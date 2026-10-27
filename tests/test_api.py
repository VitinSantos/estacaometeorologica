import unittest
from datetime import datetime, timedelta, timezone

from backend.app import criar_app
from backend.config import Config
from backend.armazenamento import ArmazenamentoMemoria as RepositorioMemoria

CHAVE = "chave-de-teste-1234567890"


def config(api_key=CHAVE):
    return Config(api_key=api_key, distancia_vazio_cm=20.0,
                  diametro_funil_mm=110.0, diametro_recipiente_mm=40.0,
                  mq135_base_bruto=600, estacao_padrao="estacao-01", limite_online_s=180)


PAYLOAD = {"estacao_id": "estacao-01", "temperatura_dht": 24.0, "umidade": 65,
           "temperatura_bmp": 24.4, "pressao_hpa": 1013.0, "mq135_bruto": 900,
           "ldr_bruto": 2048, "distancia_agua_cm": 19.0}


class BaseApi(unittest.TestCase):
    def setUp(self):
        self.repo = RepositorioMemoria()
        self.app = criar_app(repositorio=self.repo, config=config())
        self.client = self.app.test_client()
        self.cab = {"X-API-Key": CHAVE}

    def enviar(self, payload=None, cabecalhos=None):
        return self.client.post("/api/leituras", json=PAYLOAD if payload is None else payload,
                                headers=self.cab if cabecalhos is None else cabecalhos)


class TestEnvio(BaseApi):
    def test_envio_valido_retorna_201_e_calcula_derivados(self):
        r = self.enviar()
        self.assertEqual(r.status_code, 201)
        leitura = r.get_json()["leitura"]
        self.assertEqual(leitura["temperatura_c"], 24.2)
        self.assertEqual(leitura["luminosidade_pct"], 50.0)
        self.assertEqual(leitura["classe_ar"], "Moderada" if leitura["indice_ar"] > 30 else "Boa")
        self.assertAlmostEqual(leitura["chuva_mm"], 1.3, places=1)
        self.assertFalse(leitura["suspeita"])

    def test_sem_chave_retorna_401(self):
        self.assertEqual(self.enviar(cabecalhos={}).status_code, 401)

    def test_chave_errada_retorna_401(self):
        self.assertEqual(self.enviar(cabecalhos={"X-API-Key": "errada"}).status_code, 401)

    def test_servidor_sem_chave_configurada_retorna_503(self):
        app = criar_app(repositorio=RepositorioMemoria(), config=config(api_key=None))
        r = app.test_client().post("/api/leituras", json=PAYLOAD, headers=self.cab)
        self.assertEqual(r.status_code, 503)

    def test_estacao_desconhecida_retorna_404(self):
        r = self.enviar({**PAYLOAD, "estacao_id": "estacao-99"})
        self.assertEqual(r.status_code, 404)

    def test_payload_sem_valores_validos_retorna_422(self):
        r = self.enviar({"estacao_id": "estacao-01", "umidade": 999})
        self.assertEqual(r.status_code, 422)
        self.assertTrue(r.get_json()["motivos"])

    def test_corpo_que_nao_e_json_retorna_422(self):
        r = self.client.post("/api/leituras", data="oi", headers=self.cab)
        self.assertEqual(r.status_code, 422)

    def test_corpo_grande_retorna_413(self):
        r = self.enviar({**PAYLOAD, "lixo": "x" * 5000})
        self.assertEqual(r.status_code, 413)

    def test_leitura_suspeita_e_aceita_e_marcada(self):
        r = self.enviar({**PAYLOAD, "temperatura_dht": 15.0})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.get_json()["leitura"]["suspeita"])

    def test_data_futura_retorna_422(self):
        futuro = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        self.assertEqual(self.enviar({**PAYLOAD, "medido_em": futuro}).status_code, 422)

    def test_metodo_errado_retorna_405_em_json(self):
        r = self.client.delete("/api/leituras")
        self.assertEqual(r.status_code, 405)
        self.assertIn("erro", r.get_json())


class TestConsulta(BaseApi):
    def test_ultima_sem_dados(self):
        j = self.client.get("/api/leituras/ultima").get_json()
        self.assertIsNone(j["leitura"])
        self.assertFalse(j["online"])

    def test_ultima_online_depois_de_envio(self):
        self.enviar()
        j = self.client.get("/api/leituras/ultima").get_json()
        self.assertTrue(j["online"])
        self.assertEqual(j["leitura"]["estacao_id"], "estacao-01")

    def test_estacao_offline_quando_leitura_antiga(self):
        antiga = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.enviar({**PAYLOAD, "medido_em": antiga})
        j = self.client.get("/api/leituras/ultima").get_json()
        self.assertFalse(j["online"])

    def test_historico_ordenado_e_filtrado_por_horas(self):
        agora = datetime.now(timezone.utc)
        for horas_atras in (30, 5, 2):
            self.enviar({**PAYLOAD, "medido_em": (agora - timedelta(hours=horas_atras)).isoformat()})
        j = self.client.get("/api/leituras?horas=24").get_json()
        self.assertEqual(len(j["leituras"]), 2)
        datas = [l["medido_em"] for l in j["leituras"]]
        self.assertEqual(datas, sorted(datas))

    def test_horas_invalidas(self):
        for ruim in ("0", "169", "abc"):
            self.assertEqual(self.client.get(f"/api/leituras?horas={ruim}").status_code, 422)

    def test_estatisticas(self):
        agora = datetime.now(timezone.utc)
        for i, dist in enumerate((20.0, 19.0, 18.0)):
            self.enviar({**PAYLOAD, "distancia_agua_cm": dist,
                         "medido_em": (agora - timedelta(hours=3 - i)).isoformat()})
        j = self.client.get("/api/estatisticas?horas=24").get_json()
        self.assertEqual(j["total_leituras"], 3)
        self.assertEqual(j["temperatura_c"]["media"], 24.2)
        self.assertAlmostEqual(j["chuva_periodo_mm"], 2.6, places=1)

    def test_estatisticas_sem_dados(self):
        j = self.client.get("/api/estatisticas").get_json()
        self.assertEqual(j["total_leituras"], 0)
        self.assertIsNone(j["temperatura_c"])
        self.assertEqual(j["chuva_periodo_mm"], 0.0)


class TestEstacoes(BaseApi):
    def test_listar(self):
        j = self.client.get("/api/estacoes").get_json()
        self.assertEqual(len(j["estacoes"]), 3)

    def test_mais_proxima(self):
        j = self.client.get("/api/estacoes/proxima?lat=-23.5614&lon=-46.6559").get_json()
        self.assertEqual(j["mais_proxima"]["id"], "estacao-01")
        distancias = [e["distancia_km"] for e in j["estacoes"]]
        self.assertEqual(distancias, sorted(distancias))

    def test_coordenadas_invalidas(self):
        for url in ("/api/estacoes/proxima", "/api/estacoes/proxima?lat=x&lon=1",
                    "/api/estacoes/proxima?lat=95&lon=0"):
            self.assertEqual(self.client.get(url).status_code, 422)

    def test_saude(self):
        self.assertEqual(self.client.get("/api/saude").get_json(),
                         {"status": "ok", "armazenamento": "memoria"})

    def test_cabecalhos_de_seguranca(self):
        r = self.client.get("/api/saude")
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
