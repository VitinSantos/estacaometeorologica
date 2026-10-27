"""Simulador do ESP32: envia leituras falsas para a API.

Permite testar o servidor e o dashboard sem montar o hardware. Usa só a
biblioteca padrão do Python (nada para instalar).

Exemplos:
    # preenche as últimas 24 h (uma leitura a cada 30 min) e depois envia ao vivo
    python simulador/simulador.py --url http://127.0.0.1:5000 --chave SUA_CHAVE --historico 24

    # só envia 5 leituras, uma a cada 3 segundos
    python simulador/simulador.py --url https://seu-projeto.vercel.app --chave SUA_CHAVE -n 5 -i 3

A chave também pode vir da variável de ambiente API_KEY_ESTACAO.
"""
import argparse
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DISTANCIA_VAZIO_CM = 20.0


def gerar_leitura(momento: datetime, estacao_id: str, distancia_agua_cm: float) -> dict:
    """Valores no formato que o ESP32 envia (leituras brutas do ADC)."""
    hora = momento.hour + momento.minute / 60
    ciclo = math.sin((hora - 9) / 24 * 2 * math.pi)
    temperatura = 21 + 4.5 * ciclo + random.uniform(-0.2, 0.2)
    luz = max(0.0, math.sin((hora - 6) / 12 * math.pi)) if 6 <= hora <= 18 else 0.0
    return {
        "estacao_id": estacao_id,
        "medido_em": momento.isoformat(),
        "temperatura_dht": round(temperatura, 1),
        "temperatura_bmp": round(temperatura + random.uniform(-0.6, 0.6), 1),
        "umidade": round(68 - 14 * ciclo + random.uniform(-1, 1), 1),
        "pressao_hpa": round(1013 + 2.2 * math.sin(hora / 24 * 4 * math.pi), 1),
        "mq135_bruto": int(random.gauss(900, 120)),
        "ldr_bruto": int(max(0, min(4095, luz * 3800 + random.uniform(0, 150)))),
        "distancia_agua_cm": round(distancia_agua_cm, 1),
    }


def enviar(url: str, chave: str, leitura: dict) -> str:
    pedido = urllib.request.Request(
        url.rstrip("/") + "/api/leituras",
        data=json.dumps(leitura).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": chave},
        method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=10) as resposta:
            return f"{resposta.status} OK"
    except urllib.error.HTTPError as erro:
        return f"{erro.code} {erro.read().decode('utf-8', 'replace')[:120]}"
    except urllib.error.URLError as erro:
        return f"falha de rede: {erro.reason}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:5000")
    ap.add_argument("--chave", default=os.environ.get("API_KEY_ESTACAO"))
    ap.add_argument("--estacao", default="estacao-01")
    ap.add_argument("--historico", type=int, default=0, metavar="HORAS",
                    help="envia leituras passadas (uma a cada 30 min) antes de começar")
    ap.add_argument("-n", type=int, default=0, help="quantidade de leituras ao vivo (0 = infinito)")
    ap.add_argument("-i", "--intervalo", type=float, default=10.0, help="segundos entre leituras ao vivo")
    args = ap.parse_args()

    if not args.chave:
        print("Informe a chave com --chave ou API_KEY_ESTACAO.", file=sys.stderr)
        return 2

    agora = datetime.now(timezone.utc)
    nivel_chuva = 0.0  # cm de água acumulada no tubo

    if args.historico:
        passos = args.historico * 2
        print(f"Enviando {passos} leituras do passado…")
        for k in range(passos, 0, -1):
            momento = agora - timedelta(minutes=30 * k)
            if 13 <= momento.astimezone().hour <= 15:  # uma chuva de exemplo
                nivel_chuva += 0.25
            print(momento.strftime("%d/%m %H:%M"), enviar(args.url, args.chave, gerar_leitura(
                momento, args.estacao, DISTANCIA_VAZIO_CM - nivel_chuva)))

    enviadas = 0
    try:
        while args.n == 0 or enviadas < args.n:
            leitura = gerar_leitura(datetime.now(timezone.utc), args.estacao, DISTANCIA_VAZIO_CM - nivel_chuva)
            leitura.pop("medido_em")  # ao vivo, quem marca a hora é o servidor
            print(datetime.now().strftime("%H:%M:%S"), leitura["temperatura_dht"], "°C ->",
                  enviar(args.url, args.chave, leitura))
            enviadas += 1
            if args.n == 0 or enviadas < args.n:
                time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nSimulador interrompido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
