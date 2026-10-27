# Ligações do hardware

Placa: **ESP32 DOIT DevKit V1 (30 pinos)**. Todos os GNDs devem ser ligados juntos.

## Tabela de pinos

| Sensor | Pino do sensor | Pino do ESP32 | Tensão | Observação |
|---|---|---|---|---|
| DHT22 | VCC | 3V3 | 3,3 V | |
| | DATA | GPIO 4 | | módulo de 3 pinos já tem pull-up; sensor solto precisa de 10 kΩ entre VCC e DATA |
| | GND | GND | | |
| BMP280 | VCC | 3V3 | 3,3 V | confira no anúncio se aceita 5 V; na dúvida use 3,3 V |
| | GND | GND | | |
| | SDA | GPIO 21 | | I2C |
| | SCL | GPIO 22 | | I2C |
| | SDO | GND | | endereço 0x76 (ligado em 3V3 vira 0x77) |
| | CSB | 3V3 | | seleciona I2C |
| MQ-135 | VCC | VIN (5 V) | 5 V | o aquecedor consome cerca de 150 mA |
| | GND | GND | | |
| | AO | **divisor de tensão** | | ver abaixo, saída do divisor vai ao GPIO 34 |
| LDR | um terminal | 3V3 | | |
| | outro terminal | GPIO 35 e resistor de 10 kΩ para GND | | divisor de tensão |
| HC-SR04 | VCC | VIN (5 V) | 5 V | |
| | GND | GND | | |
| | TRIG | GPIO 25 | | o ESP32 gera pulso de 3,3 V, que o HC-SR04 aceita |
| | ECHO | **divisor de tensão** | | ver abaixo, saída do divisor vai ao GPIO 26 |

## Divisores de tensão (MQ-135 AO e HC-SR04 ECHO)

Os pinos do ESP32 trabalham com 3,3 V e **não toleram 5 V**. Estas duas saídas chegam a 5 V, então precisam de um divisor:

```
 saída 5 V ──[ R1 = 10 kΩ ]──┬──> GPIO (34 ou 26)
                             │
                      [ R2 = 20 kΩ ]
                             │
                            GND
```

Vsaída = Ventrada × R2 / (R1 + R2) = 5 × 20 / 30 = **3,33 V**.

Para obter 20 kΩ sem comprar o valor, use dois resistores de 10 kΩ em série.

## Divisor do LDR

```
 3V3 ──[ LDR ]──┬──> GPIO 35
                │
         [ 10 kΩ ]
                │
               GND
```

Com mais luz a resistência do LDR cai, a tensão no GPIO sobe e a leitura aumenta. É isso que o back end espera (`luminosidade = leitura / 4095 × 100`).

## Pluviômetro (funil, tubo e HC-SR04)

```
        HC-SR04  (acima da água, apontando para baixo)
           ↓  distância medida
   ~~~~~~~~~~~~~~~ nível da água
   |             |
   |   tubo      |  ← recebe a água do funil
   |_____________|
```

- Mantenha o sensor a **pelo menos 2 cm** acima do nível máximo da água (limite do HC-SR04).
- Proteja o sensor da chuva direta e nunca o deixe encostar na água.
- Chuva em mm = altura da água × (d_tubo / d_funil)². Com funil de 110 mm e tubo de 40 mm, 1 mm de chuva sobe cerca de 7,6 mm de água no tubo, o que compensa a precisão limitada do sensor (cerca de 3 mm).
- Esvazie o tubo de vez em quando. O sistema detecta o esvaziamento (queda no acumulado) e não perde a chuva já contabilizada.

## Circuitos lógicos digitais no projeto

**Sinais digitais (HC-SR04).** O pulso no TRIG dura 10 µs. O módulo emite ultrassom e coloca o ECHO em nível alto durante o tempo de ida e volta. O ESP32 mede essa largura de pulso com `pulseIn`:

```
distância = (tempo × velocidade do som) / 2
velocidade do som (m/s) = 331,3 + 0,606 × T(°C)
```

**Níveis lógicos.** Nível alto no ESP32 é a partir de cerca de 2,5 V (0,75 × 3,3 V). O divisor transforma os 5 V do ECHO em 3,33 V, que é lido com segurança como nível alto.

**Conversor analógico-digital.** O ADC do ESP32 tem 12 bits: 2¹² = 4096 níveis (0 a 4095). Com faixa de 3,3 V, cada passo vale cerca de 0,8 mV. Usamos o **ADC1** (GPIO 34 e 35) porque o ADC2 não funciona com o Wi-Fi ligado. A média de 16 amostras reduz o ruído.

**Barramento I2C (BMP280).** Duas linhas, SDA (dados) e SCL (clock), com resistores de pull-up (já presentes no módulo). Cada dispositivo responde ao seu endereço (0x76 ou 0x77).

**Expressões booleanas usadas no software.** Estas são as mesmas proposições de Lógica Matemática do código:

```
valido(x)  = finito(x) E (minimo <= x <= maximo)
suspeita   = descartou_algum_valor OU |T_dht - T_bmp| > 3
online     = existe_leitura E (agora - ultima_leitura <= 180 s)
```

## Lista de materiais

| Item | Qtde |
|---|---|
| ESP32 DOIT DevKit V1 (30 pinos) | 1 |
| Sensor DHT22 (módulo AM2302) | 1 |
| Sensor BMP280 (confira se não é BME280) | 1 |
| Sensor MQ-135 (módulo com AO e DO) | 1 |
| LDR 5 mm | 1 (o pacote traz 10) |
| Módulo HC-SR04 | 1 |
| Resistor 10 kΩ | 3 |
| Resistor 20 kΩ (ou 2 de 10 kΩ em série) | 2 |
| Protoboard | 1 |
| Jumpers macho-macho e macho-fêmea | 1 kit |
| Cabo micro-USB com dados e fonte 5 V | 1 |
| Funil e tubo reto transparente (pluviômetro) | 1 |

## Dúvidas comuns

- **BMP280 não é encontrado:** troque o endereço (0x76 ou 0x77) e confira SDA e SCL. Se o módulo for na verdade um **BME280**, o chip responde com outra identificação e a biblioteca BMP280 não o reconhece. Nesse caso use a biblioteca `Adafruit BME280`.
- **DHT22 devolve NaN:** confira a ligação do DATA e a alimentação. O firmware simplesmente não envia o campo e o servidor aceita a leitura sem ele.
- **Distância do HC-SR04 sempre ausente:** confira o divisor do ECHO e se o sensor está a mais de 2 cm da superfície.
