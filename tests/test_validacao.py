import unittest
from datetime import datetime, timedelta, timezone

from backend.validacao import ErroValidacao, interpretar_data, validar_leitura


class TestValidarLeitura(unittest.TestCase):
    def base(self, **extra):
        dados = {"estacao_id": "estacao-01", "temperatura_dht": 24.0, "umidade": 60,
                 "temperatura_bmp": 24.5, "pressao_hpa": 1012.0,
                 "mq135_bruto": 900, "ldr_bruto": 2000, "distancia_agua_cm": 18.0}
        dados.update(extra)
        return dados

    def test_leitura_valida_nao_e_suspeita(self):
        r = validar_leitura(self.base())
        self.assertFalse(r.suspeita)
        self.assertEqual(r.motivos, [])
        self.assertEqual(r.dados["umidade"], 60.0)

    def test_temperatura_fora_do_intervalo_e_descartada(self):
        r = validar_leitura(self.base(temperatura_dht=120))
        self.assertNotIn("temperatura_dht", r.dados)
        self.assertTrue(r.suspeita)

    def test_umidade_acima_de_100_e_descartada(self):
        r = validar_leitura(self.base(umidade=101))
        self.assertNotIn("umidade", r.dados)

    def test_limites_sao_inclusivos(self):
        r = validar_leitura(self.base(umidade=100, temperatura_dht=-40))
        self.assertEqual(r.dados["umidade"], 100.0)
        self.assertEqual(r.dados["temperatura_dht"], -40.0)

    def test_divergencia_entre_sensores_marca_suspeita(self):
        r = validar_leitura(self.base(temperatura_dht=20.0, temperatura_bmp=25.0))
        self.assertTrue(r.suspeita)
        self.assertIn("divergem", r.motivos[0])
        self.assertIn("temperatura_dht", r.dados)

    def test_divergencia_exatamente_no_limite_nao_e_suspeita(self):
        r = validar_leitura(self.base(temperatura_dht=20.0, temperatura_bmp=23.0))
        self.assertFalse(r.suspeita)

    def test_adc_fora_de_0_a_4095_e_descartado(self):
        r = validar_leitura(self.base(mq135_bruto=5000, ldr_bruto=-1))
        self.assertNotIn("mq135_bruto", r.dados)
        self.assertNotIn("ldr_bruto", r.dados)

    def test_adc_precisa_ser_inteiro(self):
        r = validar_leitura(self.base(mq135_bruto=900.5))
        self.assertNotIn("mq135_bruto", r.dados)

    def test_nan_e_texto_sao_descartados(self):
        r = validar_leitura(self.base(umidade=float("nan"), pressao_hpa="alta"))
        self.assertNotIn("umidade", r.dados)
        self.assertNotIn("pressao_hpa", r.dados)

    def test_booleano_nao_e_numero(self):
        r = validar_leitura(self.base(umidade=True))
        self.assertNotIn("umidade", r.dados)

    def test_distancia_abaixo_do_minimo_do_hcsr04(self):
        r = validar_leitura(self.base(distancia_agua_cm=1.0))
        self.assertNotIn("distancia_agua_cm", r.dados)

    def test_sensor_ausente_nao_e_suspeito(self):
        r = validar_leitura({"estacao_id": "estacao-01", "umidade": 50})
        self.assertFalse(r.suspeita)

    def test_sem_nenhum_valor_valido_rejeita(self):
        with self.assertRaises(ErroValidacao) as ctx:
            validar_leitura({"estacao_id": "estacao-01", "umidade": 500})
        self.assertTrue(ctx.exception.motivos)

    def test_corpo_que_nao_e_objeto(self):
        with self.assertRaises(ErroValidacao):
            validar_leitura([1, 2, 3])
        with self.assertRaises(ErroValidacao):
            validar_leitura(None)

    def test_estacao_id_invalido(self):
        for ruim in (None, "", "AB", "estacao 01", "../x", 5, "a" * 41):
            with self.assertRaises(ErroValidacao):
                validar_leitura({"estacao_id": ruim, "umidade": 50})


class TestInterpretarData(unittest.TestCase):
    def setUp(self):
        self.agora = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)

    def test_sem_valor_usa_agora(self):
        self.assertEqual(interpretar_data(None, self.agora), self.agora)

    def test_iso_com_fuso(self):
        r = interpretar_data("2026-10-21T08:00:00-03:00", self.agora)
        self.assertEqual(r, datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc))

    def test_sem_fuso_assume_utc(self):
        r = interpretar_data("2026-10-21T10:00:00", self.agora)
        self.assertEqual(r.tzinfo, timezone.utc)

    def test_futuro_e_rejeitado(self):
        futuro = (self.agora + timedelta(hours=1)).isoformat()
        with self.assertRaises(ErroValidacao):
            interpretar_data(futuro, self.agora)

    def test_muito_antiga_e_rejeitada(self):
        antiga = (self.agora - timedelta(days=8)).isoformat()
        with self.assertRaises(ErroValidacao):
            interpretar_data(antiga, self.agora)

    def test_formato_invalido(self):
        for ruim in ("ontem", 123):
            with self.assertRaises(ErroValidacao):
                interpretar_data(ruim, self.agora)


if __name__ == "__main__":
    unittest.main()
