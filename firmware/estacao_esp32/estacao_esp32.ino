/*
 * Estação meteorológica ClimaSP Aberta - firmware do ESP32 (DOIT DevKit V1, 30 pinos)
 *
 * Sensores:
 *   DHT22   -> GPIO 4            temperatura e umidade
 *   BMP280  -> I2C 21 (SDA), 22 (SCL)   pressão e temperatura
 *   MQ-135  -> GPIO 34 (ADC1)    qualidade do ar (saída AO, com divisor de tensão)
 *   LDR     -> GPIO 35 (ADC1)    luminosidade (divisor com resistor de 10 kΩ)
 *   HC-SR04 -> TRIG 25, ECHO 26  nível da água do pluviômetro (ECHO com divisor de tensão)
 *
 * Bibliotecas (Gerenciador de Bibliotecas da Arduino IDE):
 *   DHT sensor library (Adafruit), Adafruit Unified Sensor, Adafruit BMP280 Library,
 *   ArduinoJson (versão 7)
 *
 * Placa: "DOIT ESP32 DEVKIT V1" (pacote esp32 da Espressif).
 */
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP280.h>
#include <ArduinoJson.h>
#include "config.h"

// ---------- pinos ----------
const int PIN_DHT   = 4;
const int PIN_SDA   = 21;
const int PIN_SCL   = 22;
const int PIN_MQ135 = 34;  // ADC1: funciona com o Wi-Fi ligado (ADC2 não funciona)
const int PIN_LDR   = 35;  // ADC1
const int PIN_TRIG  = 25;
const int PIN_ECHO  = 26;

DHT dht(PIN_DHT, DHT22);
Adafruit_BMP280 bmp;
bool bmpOk = false;

// ---------- Wi-Fi ----------
void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("Conectando ao Wi-Fi %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 20000UL) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nConectado. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nFalha ao conectar. Nova tentativa no próximo ciclo.");
  }
}

// ---------- leituras ----------

// Média de 16 amostras do ADC (reduz o ruído). Retorna 0 a 4095.
int lerAnalogicoMedio(int pino) {
  long soma = 0;
  for (int i = 0; i < 16; i++) {
    soma += analogRead(pino);
    delay(5);
  }
  return (int)(soma / 16);
}

// Mede a distância com o HC-SR04. O TRIG recebe um pulso de 10 µs e o ECHO
// fica em nível alto durante o tempo de ida e volta do som.
// A velocidade do som varia com a temperatura: v = 331,3 + 0,606 * T (m/s).
// Retorna a mediana de 7 medidas em cm, ou NAN se todas falharem.
float medirDistanciaCm(float temperaturaC) {
  float velocidadeCmPorUs = (331.3f + 0.606f * temperaturaC) / 10000.0f;
  float medidas[7];
  int validas = 0;

  for (int i = 0; i < 7; i++) {
    digitalWrite(PIN_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);
    unsigned long duracao = pulseIn(PIN_ECHO, HIGH, 30000UL);  // 30 ms = cerca de 5 m
    if (duracao > 0) {
      medidas[validas++] = duracao * velocidadeCmPorUs / 2.0f;
    }
    delay(60);  // o HC-SR04 precisa de pausa entre medidas
  }
  if (validas == 0) return NAN;

  for (int i = 1; i < validas; i++) {  // ordenação por inserção
    float chave = medidas[i];
    int j = i - 1;
    while (j >= 0 && medidas[j] > chave) {
      medidas[j + 1] = medidas[j];
      j--;
    }
    medidas[j + 1] = chave;
  }
  return medidas[validas / 2];
}

// ---------- envio ----------
void enviarLeitura() {
  float tempDht = dht.readTemperature();
  float umidade = dht.readHumidity();
  float tempBmp = bmpOk ? bmp.readTemperature() : NAN;
  float pressao = bmpOk ? bmp.readPressure() / 100.0f : NAN;  // Pa -> hPa
  float tempRef = !isnan(tempDht) ? tempDht : (!isnan(tempBmp) ? tempBmp : 25.0f);
  float distancia = medirDistanciaCm(tempRef);

  JsonDocument doc;
  doc["estacao_id"] = ESTACAO_ID;
  if (!isnan(tempDht)) doc["temperatura_dht"] = tempDht;
  if (!isnan(umidade)) doc["umidade"] = umidade;
  if (!isnan(tempBmp)) doc["temperatura_bmp"] = tempBmp;
  if (!isnan(pressao)) doc["pressao_hpa"] = pressao;
  if (millis() >= MQ135_PREAQUECIMENTO_MS) doc["mq135_bruto"] = lerAnalogicoMedio(PIN_MQ135);
  doc["ldr_bruto"] = lerAnalogicoMedio(PIN_LDR);
  if (!isnan(distancia)) doc["distancia_agua_cm"] = distancia;

  String corpo;
  serializeJson(doc, corpo);
  Serial.println(corpo);

  // ATENÇÃO: setInsecure() cifra a conexão mas não confere o certificado do servidor.
  // Para um projeto de faculdade é aceitável; em produção use setCACert().
  WiFiClientSecure cliente;
  cliente.setInsecure();
  HTTPClient http;
  http.setTimeout(10000);
  if (!http.begin(cliente, API_URL)) {
    Serial.println("Não foi possível iniciar a conexão HTTPS.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  int codigo = http.POST(corpo);
  Serial.printf("Resposta do servidor: %d\n", codigo);
  if (codigo > 0 && codigo != 201) Serial.println(http.getString());
  http.end();
}

// ---------- setup / loop ----------
void setup() {
  Serial.begin(115200);
  delay(500);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_MQ135, ADC_11db);  // faixa de 0 a ~3,3 V
  analogSetPinAttenuation(PIN_LDR, ADC_11db);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);

  dht.begin();
  Wire.begin(PIN_SDA, PIN_SCL);
  bmpOk = bmp.begin(0x76) || bmp.begin(0x77);  // endereço depende do pino SDO do módulo
  if (!bmpOk) Serial.println("BMP280 não encontrado. Confira as ligações e o endereço I2C.");

  conectarWifi();
}

void loop() {
  unsigned long inicio = millis();
  conectarWifi();
  if (WiFi.status() == WL_CONNECTED) enviarLeitura();

  unsigned long gasto = millis() - inicio;
  if (gasto < INTERVALO_ENVIO_MS) delay(INTERVALO_ENVIO_MS - gasto);
}
