import unittest

from backend.processamento import (calcular_chuva_mm, chuva_no_periodo, classificar_ar,
                                   indice_qualidade_ar, luminosidade_percentual, resumo,
                                   temperatura_combinada)


class TestDerivados(unittest.TestCase):
    def test_temperatura_combinada(self):
        self.assertEqual(temperatura_combinada(24.0, 25.0), 24.5)
        self.assertEqual(temperatura_combinada(None, 25.0), 25.0)
        self.assertEqual(temperatura_combinada(24.0, None), 24.0)
        self.assertIsNone(temperatura_combinada(None, None))

    def test_luminosidade(self):
        self.assertEqual(luminosidade_percentual(0), 0.0)
        self.assertEqual(luminosidade_percentual(4095), 100.0)
        self.assertIsNone(luminosidade_percentual(None))

    def test_indice_ar_relativo_a_base(self):
        self.assertEqual(indice_qualidade_ar(500, 600), 0)
        self.assertEqual(indice_qualidade_ar(600, 600), 0)
        self.assertEqual(indice_qualidade_ar(4095, 600), 100)
        self.assertIsNone(indice_qualidade_ar(None, 600))

    def test_classificacao_do_ar_nas_fronteiras(self):
        self.assertEqual(classificar_ar(0), "Boa")
        self.assertEqual(classificar_ar(30), "Boa")
        self.assertEqual(classificar_ar(31), "Moderada")
        self.assertEqual(classificar_ar(60), "Moderada")
        self.assertEqual(classificar_ar(61), "Ruim")
        self.assertIsNone(classificar_ar(None))


class TestChuva(unittest.TestCase):
    def test_tubo_vazio_nao_tem_chuva(self):
        self.assertEqual(calcular_chuva_mm(20.0, 20.0, 110, 40), 0.0)

    def test_distancia_maior_que_vazio_e_ruido(self):
        self.assertEqual(calcular_chuva_mm(20.3, 20.0, 110, 40), 0.0)

    def test_razao_de_areas(self):
        # 10 mm de agua no tubo de 40 mm com funil de 110 mm:
        # chuva = 10 * (40/110)^2 = 1.32 mm
        self.assertAlmostEqual(calcular_chuva_mm(19.0, 20.0, 110, 40), 1.3, places=1)

    def test_funil_igual_ao_tubo_nao_amplifica(self):
        self.assertEqual(calcular_chuva_mm(19.0, 20.0, 50, 50), 10.0)

    def test_sem_medida(self):
        self.assertIsNone(calcular_chuva_mm(None, 20.0, 110, 40))

    def test_periodo_soma_aumentos(self):
        self.assertEqual(chuva_no_periodo([0.0, 1.0, 1.0, 2.5]), 2.5)

    def test_periodo_ignora_esvaziamento(self):
        # subiu 3.0, esvaziou (queda), subiu mais 1.0
        self.assertEqual(chuva_no_periodo([0.0, 3.0, 0.0, 1.0]), 4.0)

    def test_periodo_ignora_ruido_abaixo_da_tolerancia(self):
        self.assertEqual(chuva_no_periodo([1.0, 1.1, 1.0, 1.15]), 0.0)

    def test_periodo_com_ausentes_e_vazio(self):
        self.assertEqual(chuva_no_periodo([None, 0.0, None, 2.0]), 2.0)
        self.assertEqual(chuva_no_periodo([]), 0.0)


class TestResumo(unittest.TestCase):
    def test_resumo(self):
        self.assertEqual(resumo([10, 20, None, 30]), {"minimo": 10.0, "maximo": 30.0, "media": 20.0})

    def test_resumo_vazio(self):
        self.assertIsNone(resumo([]))
        self.assertIsNone(resumo([None, None]))


if __name__ == "__main__":
    unittest.main()
