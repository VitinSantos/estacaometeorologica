# ClimaSP Aberta: estação meteorológica inteligente

Projeto integrador de **Projeto e Desenvolvimento II**. Uma estação com ESP32 e sensores ambientais envia dados pela internet para um servidor em Python, que os valida e os exibe num dashboard público.

```
Sensores -> ESP32 -> Wi-Fi (HTTPS + JSON) -> Flask (Vercel) -> memória do servidor -> Dashboard (HTML/CSS/JS)
```

**Sem banco de dados:** as leituras ficam numa fila na memória do servidor (até 7 dias de leituras). É a opção mais simples. A consequência está em "Segurança e limitações".

## O que o projeto mede

| Variável | Sensor | Como chega ao dashboard |
|---|---|---|
| Temperatura | DHT22 e BMP280 | média dos dois; divergência maior que 3 °C marca a leitura como suspeita |
| Umidade | DHT22 | direto |
| Pressão atmosférica | BMP280 | direto (hPa) |
| Qualidade do ar | MQ-135 | índice relativo de 0 a 100 (Boa, Moderada, Ruim) |
| Luminosidade | LDR | percentual de 0 a 100 |
| Chuva | HC-SR04 + funil + tubo | nível da água convertido em milímetros de chuva |

## Estrutura

```
api/index.py            entrada da Vercel (expõe o app Flask)
backend/
  app.py                rotas da API
  validacao.py          validação e tratamento de dados inconsistentes
  processamento.py      cálculos: derivados, chuva, estatísticas
  geo.py                geometria analítica (Haversine e distância euclidiana)
  roteamento.py         ajusta o caminho das requisições na Vercel
  armazenamento.py      guarda as leituras na memória
  estacoes.py           lista de estações (edite nomes e coordenadas aqui)
  config.py             variáveis de ambiente
public/                 dashboard (index.html, css/style.css, js/dashboard.js)
firmware/
  teste_sensores/       testa os sensores sem Wi-Fi (use primeiro)
  estacao_esp32/        firmware principal, envia para a API
simulador/              envia dados falsos para testar sem hardware
tests/                  80 testes automatizados
docs/                   ligações, montagem passo a passo e backlog
```

## Rodar no seu computador

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

Edite o `.env` e defina `API_KEY_ESTACAO` (gere uma com `python -c "import secrets; print(secrets.token_urlsafe(32))"`).

```bash
python run_local.py              # abre em http://localhost:5000
```

Para ver o painel com dados sem o hardware, rode em outro terminal:

```bash
python simulador/simulador.py --url http://127.0.0.1:5000 --chave SUA_CHAVE --historico 24
```

## Testes

```bash
python -m unittest discover -s tests -t . -v
```

Cobrem validação (limites, NaN, tipos, divergência entre sensores), cálculo de chuva, índice do ar, geometria, o armazenamento em memória (inclusive envios simultâneos) e a API completa (autenticação, erros 401, 404, 413, 422, estatísticas, estação online ou offline).

## Publicar: GitHub e Vercel

**GitHub**

```bash
git init
git add .
git commit -m "feat: estação meteorológica ClimaSP Aberta"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/estacaometeorologica.git
git push -u origin main
```

Antes do primeiro commit, confirme com `git status` que o `.env` e o `config.h` **não** aparecem na lista (o `.gitignore` já os exclui). Se o repositório já existe, basta substituir os arquivos e fazer `git add .`, `git commit` e `git push`: a Vercel publica sozinha.

**Vercel**

1. Em vercel.com, **Add New > Project** e importe o repositório. *Framework Preset*: **Other**.
2. Em **Environment Variables**, cadastre `API_KEY_ESTACAO` e, quando for calibrar, `DISTANCIA_VAZIO_CM`, `DIAMETRO_FUNIL_MM`, `DIAMETRO_RECIPIENTE_MM` e `MQ135_BASE_BRUTO`.
3. Variáveis só valem em deploys novos: depois de alterá-las, faça **Redeploy**.
4. Teste: abra `https://SEU-PROJETO.vercel.app/api/saude` (deve responder `{"armazenamento":"memoria","status":"ok"}`) e depois o site.

## Se algo não funcionar depois do deploy

Abra `https://SEU-PROJETO.vercel.app/api/saude`:

| Resultado | Significado |
|---|---|
| `{"armazenamento":"memoria","status":"ok"}` | API funcionando |
| `{"erro":"Rota não encontrada.","caminho":"..."}` | A função está no ar, mas recebeu um caminho inesperado: anote o valor de `caminho` |
| Página da Vercel com 404 | A pasta `api/` ou o `vercel.json` não estão na raiz do repositório |
| `FUNCTION_INVOCATION_FAILED` | A função quebrou ao iniciar: veja **Logs** na Vercel |

O painel mostra "Não foi possível falar com o servidor" sempre que `/api/...` não responde com sucesso. Isso **não** tem relação com os sensores: sem dados, o painel mostra "Estação offline" e traços.

## API

| Método e rota | Autenticação | Descrição |
|---|---|---|
| `POST /api/leituras` | cabeçalho `X-API-Key` | recebe uma leitura do ESP32 |
| `GET /api/leituras/ultima?estacao_id=` | pública | leitura mais recente, com `online` |
| `GET /api/leituras?horas=24&estacao_id=` | pública | histórico (1 a 168 horas) |
| `GET /api/estatisticas?horas=24` | pública | mínimo, máximo, média e chuva do período |
| `GET /api/estacoes` | pública | estações e coordenadas |
| `GET /api/estacoes/proxima?lat=&lon=` | pública | estações ordenadas por distância (Haversine) |
| `GET /api/saude` | pública | verificação de funcionamento |

Exemplo de corpo do `POST /api/leituras` (todos os sensores são opcionais, mas ao menos um precisa ser válido):

```json
{
  "estacao_id": "estacao-01",
  "temperatura_dht": 24.1, "umidade": 68,
  "temperatura_bmp": 24.5, "pressao_hpa": 1013.2,
  "mq135_bruto": 900, "ldr_bruto": 2900,
  "distancia_agua_cm": 19.0
}
```

Respostas: `201` salvo, `401` chave inválida, `404` estação desconhecida, `413` corpo grande, `422` dados inválidos, `503` servidor sem chave configurada.

## Calibração

- **Pluviômetro:** com o tubo vazio e o HC-SR04 fixo, meça a distância até o fundo e informe em `DISTANCIA_VAZIO_CM`. Informe também o diâmetro do funil e do tubo. A chuva em mm é `altura da água × (d_tubo / d_funil)²`.
- **MQ-135:** deixe ligado por 24 h na primeira vez. Depois, em ar limpo, anote o valor bruto do Monitor Serial e use como `MQ135_BASE_BRUTO`. O índice é relativo, **não é ppm** nem o índice oficial de qualidade do ar.

Detalhes e testes em `docs/montagem_passo_a_passo.md`.

## Conexão com as disciplinas

| Disciplina | Onde aparece |
|---|---|
| Lógica de Programação e Algoritmos | mediana de medidas no firmware, `chuva_no_periodo`, `resumo`, fila circular do armazenamento |
| Programação Estruturada em Python | funções pequenas e puras em `backend/` |
| Circuitos Lógicos Digitais | sinais TRIG e ECHO, ADC de 12 bits, divisores de tensão (veja `docs/ligacoes_hardware.md`) |
| Lógica Matemática | proposições de validade em `validacao.py` e a regra de divergência entre sensores |
| Geometria Analítica | distância entre pontos em `geo.py` e razão de áreas do pluviômetro |

## Segurança e limitações

- **Os dados ficam só na memória.** Se o servidor da Vercel ficar parado ou reiniciar, o histórico zera e volta a ser preenchido pelas novas leituras. Com o ESP32 enviando a cada 60 s isso quase não ocorre, mas pode ocorrer. Para guardar para sempre seria preciso adicionar um banco de dados (basta criar outra classe com os mesmos métodos de `armazenamento.py`).
- A Vercel pode manter mais de uma cópia do servidor ativa; nesse caso cada uma tem sua própria memória. Com apenas uma estação enviando a cada minuto isso é raro.
- A escrita na API exige chave; a comparação é feita em tempo constante. A leitura é pública por decisão do projeto.
- O dashboard escreve dados com `textContent`, nunca `innerHTML`.
- Não há limitação de taxa de requisições. Uma chave vazada permite enviar dados falsos: se isso acontecer, troque `API_KEY_ESTACAO` na Vercel e no `config.h`.
- O firmware usa `setInsecure()`: a conexão é cifrada, mas o certificado do servidor não é conferido.
- O dashboard consulta a API a cada 10 s, mas o ESP32 envia a cada 60 s. A estação é considerada offline após 180 s sem leitura.
- Os dados são experimentais e não substituem fontes oficiais (INMET, CETESB).
