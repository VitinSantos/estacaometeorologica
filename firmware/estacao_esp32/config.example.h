// Copie este arquivo para "config.h" (na mesma pasta) e preencha os valores.
// O config.h está no .gitignore: nunca faça commit de senha de Wi-Fi nem de chave.
#pragma once

#define WIFI_SSID   "NOME_DA_SUA_REDE"
#define WIFI_SENHA  "SENHA_DA_REDE"

// URL completa da API publicada na Vercel (HTTPS)
#define API_URL     "https://SEU-PROJETO.vercel.app/api/leituras"
// Mesma chave cadastrada na variável API_KEY_ESTACAO da Vercel
#define API_KEY     "COLE_AQUI_A_CHAVE"

#define ESTACAO_ID  "estacao-01"

// Intervalo entre envios (60 s é suficiente para clima)
#define INTERVALO_ENVIO_MS        60000UL
// O MQ-135 só envia depois do pré-aquecimento (3 min no teste; na 1ª vez deixe 24 h ligado)
#define MQ135_PREAQUECIMENTO_MS   180000UL
