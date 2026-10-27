# Montagem e testes, passo a passo

Faça nesta ordem. Cada etapa só vale a pena se a anterior funcionou. Os pinos e os divisores de tensão estão em `ligacoes_hardware.md`.

## Antes de começar

1. Instale a **Arduino IDE** e, em *Gerenciador de Placas*, o pacote **esp32 (Espressif)**.
2. Em *Gerenciador de Bibliotecas*, instale: `DHT sensor library`, `Adafruit Unified Sensor`, `Adafruit BMP280 Library` e `ArduinoJson` (versão 7).
3. Selecione a placa **DOIT ESP32 DEVKIT V1** e a porta COM do ESP32.
4. Use sempre um **cabo micro-USB que transmite dados** (cabos só de carga não aparecem como porta).

## Etapa 1: ESP32 sozinho

Grave `firmware/teste_sensores/teste_sensores.ino` e abra o Monitor Serial em **115200**. Mesmo sem sensores, o scanner I2C deve rodar e mostrar "Nenhum dispositivo I2C". Se aparecer, o ESP32 está bom.

Se o upload falhar com "Connecting......", segure o botão **BOOT** da placa quando a mensagem aparecer.

## Etapa 2: um sensor por vez

Desligue o USB antes de mexer na fiação. Ligue **um sensor, grave, confira**, e só então o próximo.

| Ordem | Sensor | O que deve aparecer | Se não aparecer |
|---|---|---|---|
| 1 | LDR | valor muda ao cobrir com a mão | confira o resistor de 10 kΩ para GND |
| 2 | DHT22 | temperatura e umidade realistas | confira DATA no GPIO 4; troque o jumper |
| 3 | BMP280 | endereço `0x76` ou `0x77` no scanner e pressão de 900 a 1050 hPa | confira SDA e SCL; veja o ID do chip (BMP280 ou BME280) |
| 4 | HC-SR04 | distância em cm que muda ao aproximar a mão | confira o divisor de tensão no ECHO e se está a mais de 2 cm do objeto |
| 5 | MQ-135 | valor bruto que sobe perto de álcool ou fumaça | deixe aquecer alguns minutos; confira o divisor de tensão |

**Atenção ao divisor de tensão** no ECHO do HC-SR04 e no AO do MQ-135. Sem ele, os 5 V podem danificar o pino do ESP32.

Guarde dois números para a calibração:
- **MQ-135 em ar limpo** (depois de pelo menos 24 h ligado na primeira vez): será o `MQ135_BASE_BRUTO`.
- **Distância do HC-SR04 com o tubo vazio**: será o `DISTANCIA_VAZIO_CM`.

## Etapa 3: enviar para a internet

1. Em `firmware/estacao_esp32/`, copie `config.example.h` para `config.h`.
2. Preencha `WIFI_SSID`, `WIFI_SENHA`, `API_URL` (`https://estacaometeorologica-alpha.vercel.app/api/leituras`) e `API_KEY` (a mesma chave cadastrada na Vercel).
3. Use uma rede **2,4 GHz**: o ESP32 não conecta em 5 GHz. Rede de faculdade com login por página (portal cativo) normalmente não funciona; use o roteador do celular se precisar.
4. Grave `firmware/estacao_esp32/estacao_esp32.ino` e abra o Monitor Serial.

O que esperar no monitor:

```
Conectado. IP: 192.168.x.x
{"estacao_id":"estacao-01","temperatura_dht":24.1, ...}
Resposta do servidor: 201
```

| Resposta | Significado | O que fazer |
|---|---|---|
| `201` | gravado com sucesso | nada, está certo |
| `401` | chave errada | confira `API_KEY` no `config.h` e na Vercel |
| `404` | estação desconhecida | confira `ESTACAO_ID` |
| `422` | todos os valores inválidos | o servidor explica o motivo no texto da resposta |
| `-1` ou negativo | sem conexão com o servidor | confira Wi-Fi e a URL |

## Etapa 4: conferir no dashboard

Abra o site. Em até 1 minuto os cards devem mostrar valores e o status deve ficar **"Estação online"**. O gráfico começa a se formar com as leituras que chegam a cada 60 s.

## Etapa 5: calibrar

1. Informe `MQ135_BASE_BRUTO` e `DISTANCIA_VAZIO_CM` nas variáveis de ambiente da Vercel e faça o redeploy.
2. **Teste da chuva:** despeje uma quantidade conhecida de água no funil (por exemplo, 50 mL). Chuva em mm = volume (mL) / área do funil (cm²) × 10. Compare com o valor do painel e ajuste os diâmetros se precisar.
3. Cubra o LDR e aponte uma lanterna para ele para ver os extremos da luminosidade.

## Atenção: o servidor guarda os dados na memória

Se o servidor da Vercel reiniciar, o histórico zera e o painel mostra "Sem leituras ainda" até o ESP32 enviar de novo (no máximo 1 minuto). Isso é esperado nesta versão sem banco de dados.
