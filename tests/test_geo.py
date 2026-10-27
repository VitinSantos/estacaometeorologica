import unittest

from backend.geo import (distancia_euclidiana_km, haversine_km, ordenar_por_distancia,
                         validar_coordenadas)

SE = (-23.5505, -46.6333)
PINHEIROS = (-23.5614, -46.7020)
RIO = (-22.9068, -43.1729)


class TestGeo(unittest.TestCase):
    def test_distancia_zero(self):
        self.assertAlmostEqual(haversine_km(*SE, *SE), 0.0)

    def test_um_grau_de_latitude(self):
        self.assertAlmostEqual(haversine_km(0, 0, 1, 0), 111.195, delta=0.01)

    def test_sao_paulo_rio(self):
        self.assertAlmostEqual(haversine_km(*SE, *RIO), 360, delta=5)

    def test_simetria(self):
        self.assertAlmostEqual(haversine_km(*SE, *RIO), haversine_km(*RIO, *SE))

    def test_euclidiana_concorda_com_haversine_em_distancia_curta(self):
        h = haversine_km(*SE, *PINHEIROS)
        e = distancia_euclidiana_km(*SE, *PINHEIROS)
        self.assertAlmostEqual(h, e, delta=0.05)
        self.assertAlmostEqual(h, 7.1, delta=0.2)

    def test_ordenacao(self):
        estacoes = [
            {"id": "longe", "latitude": RIO[0], "longitude": RIO[1]},
            {"id": "perto", "latitude": PINHEIROS[0], "longitude": PINHEIROS[1]},
        ]
        r = ordenar_por_distancia(*SE, estacoes)
        self.assertEqual([e["id"] for e in r], ["perto", "longe"])
        self.assertIn("distancia_km", r[0])
        self.assertNotIn("distancia_km", estacoes[0])

    def test_validar_coordenadas(self):
        self.assertTrue(validar_coordenadas(-23.5, -46.6))
        self.assertTrue(validar_coordenadas(90, 180))
        self.assertFalse(validar_coordenadas(91, 0))
        self.assertFalse(validar_coordenadas(0, -181))


if __name__ == "__main__":
    unittest.main()
