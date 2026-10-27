/*
 * Teste dos sensores SEM Wi-Fi: use isto ANTES do firmware principal.
 * Mostra no Monitor Serial (115200) o que cada sensor está lendo, a cada 2 s.
 * Assim você descobre se um problema é de ligação ou de internet.
 *
 * Mesmos pinos do firmware principal:
 *   DHT22 -> 4 | BMP280 -> SDA 21, SCL 22 | MQ-135 -> 34 | LDR -> 35
 *   HC-SR04 -> TRIG 25, ECHO 26 (com divisor de tensão)
 *
 * Bibliotecas: DHT sensor library, Adafruit Unified Sensor, Adafruit BMP280 Library.
 */
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP280.h>

const int PIN_DHT = 4, PIN_SDA = 21, PIN_SCL = 22;
const int PIN_MQ135 = 34, PIN_LDR = 35, PIN_TRIG = 25, PIN_ECHO = 26;

DHT dht(PIN_DHT, DHT22);
Adafruit_BMP280 bmp;
bool bmpOk = false;

// Procura dispositivos I2C. O BMP280 deve aparecer em 0x76 ou 0x77.
void escanearI2C() {
  Serial.println("--- Scanner I2C ---");
  int achados = 0;
  for (uint8_t endereco = 1; endereco < 127; endereco++) {
    Wire.beginTransmission(endereco);
    if (Wire.endTransmission() == 0) {
      Serial.printf("Dispositivo em 0x%02X", endereco);
      if (endereco == 0x76 || endereco == 0x77) {
        // O registrador 0xD0 guarda a identificação do chip.
        Wire.beginTransmission(endereco);
        Wire.write(0xD0);
        Wire.endTransmission(false);
        Wire.requestFrom((int)endereco, 1);
        if (Wire.available()) {
          uint8_t id = Wire.read();
          Serial.printf(" (ID do chip 0x%02X: ", id);
          if (id == 0x58) Serial.print("BMP280, correto)");
          else if (id == 0x60) Serial.print("BME280, use a biblioteca Adafruit BME280)");
          else Serial.print("desconhecido)");
        }
      }
      Serial.println();
      achados++;
    }
  }
  if (achados == 0) Serial.println("Nenhum dispositivo I2C. Confira SDA, SCL, VCC e GND do BMP280.");
}

// Uma medida do HC-SR04 em cm (0 = sem eco).
float distanciaCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  unsigned long duracao = pulseIn(PIN_ECHO, HIGH, 30000UL);
  return duracao * 0.0343f / 2.0f;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_MQ135, ADC_11db);
  analogSetPinAttenuation(PIN_LDR, ADC_11db);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  dht.begin();
  Wire.begin(PIN_SDA, PIN_SCL);
  escanearI2C();
  bmpOk = bmp.begin(0x76) || bmp.begin(0x77);
  Serial.println(bmpOk ? "BMP280 iniciado." : "BMP280 NAO iniciou.");
  Serial.println("Valores a cada 2 s. O MQ-135 so estabiliza depois de minutos ligado.\n");
}

void loop() {
  float t = dht.readTemperature();
  float u = dht.readHumidity();
  Serial.println("--------------------");
  if (isnan(t) || isnan(u)) Serial.println("DHT22  : FALHA (confira DATA no GPIO 4 e a alimentacao)");
  else Serial.printf("DHT22  : %.1f C | %.0f %%\n", t, u);

  if (bmpOk) Serial.printf("BMP280 : %.1f C | %.1f hPa\n", bmp.readTemperature(), bmp.readPressure() / 100.0f);
  else Serial.println("BMP280 : indisponivel");

  int mq = analogRead(PIN_MQ135);
  Serial.printf("MQ-135 : bruto %d de 4095  (anote o valor em ar limpo: sera o MQ135_BASE_BRUTO)\n", mq);

  int ldr = analogRead(PIN_LDR);
  Serial.printf("LDR    : bruto %d de 4095  (%d %%)  -> cubra com a mao: deve cair\n", ldr, ldr * 100 / 4095);

  float d = distanciaCm();
  if (d < 2.0f) Serial.println("HC-SR04: sem eco (confira TRIG, ECHO, divisor de tensao e distancia minima de 2 cm)");
  else Serial.printf("HC-SR04: %.1f cm\n", d);

  delay(2000);
}
