import unittest

from backend.app import criar_app
from backend.config import Config

CHAVE = "chave-de-teste-1234567890"
CONFIG = Config(api_key=CHAVE, distancia_vazio_cm=20.0, diametro_funil_mm=110.0,
                diametro_recipiente_mm=40.0, mq135_base_bruto=600,
                estacao_padrao="estacao-01", limite_online_s=180)


class TestCorrigeCaminho(unittest.TestCase):
    def setUp(self):
        self.client = criar_app(config=CONFIG).test_client()

    def test_caminho_original_continua_funcionando(self):
        self.assertEqual(self.client.get("/api/saude").status_code, 200)

    def test_caminho_da_funcao_com_rota_e_reconstruido(self):
        r = self.client.get("/api/index?rota=saude")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["status"], "ok")

    def test_rota_aninhada(self):
        r = self.client.get("/api/index?rota=leituras/ultima")
        self.assertEqual(r.status_code, 200)
        self.assertIn("leitura", r.get_json())

    def test_rota_aninhada_codificada(self):
        r = self.client.get("/api/index?rota=estacoes%2Fproxima&lat=-23.5&lon=-46.6")
        self.assertEqual(r.status_code, 200)
        self.assertIn("mais_proxima", r.get_json())

    def test_outros_parametros_sao_preservados(self):
        r = self.client.get("/api/index?rota=leituras&horas=999")
        self.assertEqual(r.status_code, 422)  # horas=999 chegou à validação

    def test_post_pela_funcao(self):
        r = self.client.post("/api/index?rota=leituras", headers={"X-API-Key": CHAVE},
                             json={"estacao_id": "estacao-01", "umidade": 50})
        self.assertEqual(r.status_code, 201)

    def test_rota_maliciosa_e_ignorada(self):
        for ruim in ("../x", "saude;ls", "a//b", "SAUDE", "saude?x"):
            r = self.client.get("/api/index", query_string={"rota": ruim})
            self.assertEqual(r.status_code, 404, ruim)

    def test_sem_rota_na_funcao_retorna_404_json(self):
        r = self.client.get("/api/index")
        self.assertEqual(r.status_code, 404)
        self.assertIn("caminho", r.get_json())

    def test_parametro_rota_nao_afeta_caminho_normal(self):
        r = self.client.get("/api/leituras?rota=estacoes")
        self.assertEqual(r.status_code, 200)
        self.assertIn("leituras", r.get_json())


if __name__ == "__main__":
    unittest.main()
