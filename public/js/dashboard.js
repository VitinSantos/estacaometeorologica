/*
 * Dashboard da estação meteorológica.
 *
 * O HTML e o CSS cuidam da aparência. Este arquivo só faz três coisas:
 *   1. buscar os dados na API (fetch) a cada 10 segundos;
 *   2. escrever os valores nos cards (sempre com textContent, nunca innerHTML,
 *      para que nenhum dado vindo da rede vire código na página);
 *   3. desenhar o gráfico (Chart.js) e o mapa (Leaflet).
 */
"use strict";

const ESTACAO_PADRAO = "estacao-01";
const INTERVALO_MS = 10000;
const LIMITE_ONLINE_FALHAS = 3;
const FUSO = "America/Sao_Paulo";
const POSICAO_PADRAO = { lat: -23.5614, lon: -46.6559 }; // Av. Paulista

const SERIES = {
  temperatura_c: { rotulo: "Temperatura (°C)", cor: "#eb6834" },
  umidade: { rotulo: "Umidade (%)", cor: "#2a78d6" },
  pressao_hpa: { rotulo: "Pressão (hPa)", cor: "#6250d6" },
  chuva_mm: { rotulo: "Chuva acumulada no recipiente (mm)", cor: "#1baf7a" },
};

const $ = (id) => document.getElementById(id);
let falhasSeguidas = 0;
let serieAtual = "temperatura_c";
let historico = [];
let grafico = null;
let mapa = null;
let camadaUsuario = null;

/* ---------- utilidades ---------- */

function numero(valor, casas, unidade) {
  if (valor === null || valor === undefined) return "--";
  return valor.toFixed(casas).replace(".", ",") + unidade;
}

function hora(iso) {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: FUSO });
}

class ErroApi extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.status = status;
  }
}

async function api(caminho) {
  const controle = new AbortController();
  const limite = setTimeout(() => controle.abort(), 8000);
  try {
    const resposta = await fetch(caminho, { signal: controle.signal });
    if (!resposta.ok) {
      let detalhe = "";
      try { detalhe = (await resposta.json()).erro || ""; } catch (e) { /* corpo sem JSON */ }
      throw new ErroApi(detalhe || "Erro HTTP " + resposta.status, resposta.status);
    }
    return await resposta.json();
  } finally {
    clearTimeout(limite);
  }
}

function mostrarAviso(texto) {
  const aviso = $("aviso");
  aviso.textContent = texto || "";
  aviso.hidden = !texto;
}

/* ---------- leitura atual ---------- */

function mostrarStatus(online, segundos) {
  const ponto = $("status-ponto");
  ponto.className = "ponto " + (online ? "online" : "offline");
  $("status-texto").textContent = online ? "Estação online" : "Estação offline";
  if (segundos === null || segundos === undefined) {
    $("atualizado").textContent = "Sem leituras ainda";
  } else if (segundos < 60) {
    $("atualizado").textContent = "Última leitura há " + segundos + " s";
  } else {
    $("atualizado").textContent = "Última leitura há " + Math.round(segundos / 60) + " min";
  }
}

function mostrarLeitura(leitura) {
  $("v-temperatura").textContent = numero(leitura && leitura.temperatura_c, 1, " °C");
  $("v-umidade").textContent = numero(leitura && leitura.umidade, 0, " %");
  $("v-pressao").textContent = numero(leitura && leitura.pressao_hpa, 0, " hPa");
  $("v-luz").textContent = numero(leitura && leitura.luminosidade_pct, 0, " %");

  const ar = $("v-ar");
  ar.textContent = (leitura && leitura.classe_ar) || "--";
  ar.dataset.classe = (leitura && leitura.classe_ar) || "";
  $("v-ar-detalhe").textContent =
    leitura && leitura.indice_ar !== null ? "MQ-135, índice " + leitura.indice_ar : "MQ-135 (índice relativo)";

  $("suspeita").hidden = !(leitura && leitura.suspeita);
}

async function atualizarAgora() {
  const dados = await api("/api/leituras/ultima?estacao_id=" + ESTACAO_PADRAO);
  mostrarStatus(dados.online, dados.segundos_desde_ultima);
  mostrarLeitura(dados.leitura);

  const estat = await api("/api/estatisticas?horas=24&estacao_id=" + ESTACAO_PADRAO);
  $("v-chuva").textContent = dados.leitura ? numero(estat.chuva_periodo_mm, 1, " mm") : "--";
}

/* ---------- gráfico ---------- */

function desenharGrafico() {
  const serie = SERIES[serieAtual];
  const pontos = historico.filter((l) => l[serieAtual] !== null && l[serieAtual] !== undefined);
  $("grafico-vazio").hidden = pontos.length > 0;

  const rotulos = pontos.map((l) => hora(l.medido_em));
  const valores = pontos.map((l) => l[serieAtual]);

  if (!grafico) {
    grafico = new Chart($("grafico"), {
      type: "line",
      data: { labels: rotulos, datasets: [{ label: serie.rotulo, data: valores, borderColor: serie.cor,
        backgroundColor: serie.cor + "1a", fill: true, borderWidth: 2, pointRadius: 0,
        pointHoverRadius: 5, tension: 0.3 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { maxTicksLimit: 8 }, grid: { display: false } },
                  y: { grid: { color: "rgba(128,128,128,0.2)" } } },
      },
    });
    return;
  }
  const conjunto = grafico.data.datasets[0];
  grafico.data.labels = rotulos;
  conjunto.label = serie.rotulo;
  conjunto.data = valores;
  conjunto.borderColor = serie.cor;
  conjunto.backgroundColor = serie.cor + "1a";
  grafico.update();
}

async function atualizarGrafico() {
  const dados = await api("/api/leituras?horas=24&estacao_id=" + ESTACAO_PADRAO);
  historico = dados.leituras;
  desenharGrafico();
}

function configurarAbas() {
  document.querySelectorAll(".aba").forEach((botao) => {
    botao.addEventListener("click", () => {
      document.querySelectorAll(".aba").forEach((b) => {
        b.classList.remove("ativa");
        b.setAttribute("aria-pressed", "false");
      });
      botao.classList.add("ativa");
      botao.setAttribute("aria-pressed", "true");
      serieAtual = botao.dataset.serie;
      desenharGrafico();
    });
  });
}

/* ---------- mapa ---------- */

function conteudoPopup(estacao) {
  const caixa = document.createElement("div");
  const nome = document.createElement("strong");
  nome.textContent = estacao.nome;
  const estado = document.createElement("div");
  estado.textContent = estacao.ativa ? "Estação ativa" : "Estação planejada";
  caixa.append(nome, estado);
  return caixa;
}

async function iniciarMapa() {
  if (typeof L === "undefined") {
    $("mapa").textContent = "Não foi possível carregar o mapa.";
    return;
  }
  mapa = L.map("mapa").setView([-23.5505, -46.6333], 11);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; colaboradores do OpenStreetMap",
  }).addTo(mapa);

  const dados = await api("/api/estacoes");
  $("estacao-nome").textContent = "Estação 01, São Paulo";
  dados.estacoes.forEach((e) => {
    if (e.id === ESTACAO_PADRAO) $("estacao-nome").textContent = e.nome + ", São Paulo";
    L.circleMarker([e.latitude, e.longitude], {
      radius: 9, color: e.ativa ? "#2a78d6" : "#85847e", fillOpacity: 0.8,
    }).addTo(mapa).bindPopup(conteudoPopup(e));
  });
}

function posicaoDoUsuario() {
  return new Promise((resolver) => {
    if (!navigator.geolocation) return resolver({ ...POSICAO_PADRAO, simulada: true });
    navigator.geolocation.getCurrentPosition(
      (p) => resolver({ lat: p.coords.latitude, lon: p.coords.longitude, simulada: false }),
      () => resolver({ ...POSICAO_PADRAO, simulada: true }),
      { timeout: 8000 }
    );
  });
}

async function buscarMaisProxima() {
  const botao = $("btn-proxima");
  botao.disabled = true;
  try {
    const pos = await posicaoDoUsuario();
    const dados = await api("/api/estacoes/proxima?lat=" + pos.lat + "&lon=" + pos.lon);
    const perto = dados.mais_proxima;
    const todas = dados.estacoes.map((e) => e.nome + ": " + numero(e.distancia_km, 1, " km")).join(" | ");
    $("mapa-resultado").textContent =
      (pos.simulada ? "Localização indisponível, usando a Av. Paulista como exemplo. " : "") +
      "Mais próxima: " + perto.nome + " (" + numero(perto.distancia_km, 1, " km") + "). " + todas;

    if (mapa) {
      if (camadaUsuario) camadaUsuario.remove();
      camadaUsuario = L.layerGroup([
        L.circleMarker([pos.lat, pos.lon], { radius: 7, color: "#eb6834", fillOpacity: 0.9 }),
        L.polyline([[pos.lat, pos.lon], [perto.latitude, perto.longitude]], { color: "#0a8a0a", dashArray: "6 6" }),
      ]).addTo(mapa);
      mapa.fitBounds([[pos.lat, pos.lon], [perto.latitude, perto.longitude]], { padding: [40, 40] });
    }
  } catch (erro) {
    $("mapa-resultado").textContent = "Não foi possível calcular a estação mais próxima. Tente de novo.";
  } finally {
    botao.disabled = false;
  }
}

/* ---------- ciclo principal ---------- */

async function atualizarTudo() {
  try {
    await Promise.all([atualizarAgora(), atualizarGrafico()]);
    falhasSeguidas = 0;
    mostrarAviso("");
  } catch (erro) {
    falhasSeguidas += 1;
    if (erro instanceof ErroApi && erro.status === 503) {
      mostrarAviso("O servidor está com um problema de configuração: " + erro.message);
    } else if (falhasSeguidas >= LIMITE_ONLINE_FALHAS) {
      mostrarAviso("Não foi possível falar com o servidor. Tentando novamente automaticamente.");
    }
  }
}

configurarAbas();
$("btn-proxima").addEventListener("click", buscarMaisProxima);
iniciarMapa().catch(() => { $("mapa-resultado").textContent = "Não foi possível carregar as estações."; });
atualizarTudo();
setInterval(atualizarTudo, INTERVALO_MS);
