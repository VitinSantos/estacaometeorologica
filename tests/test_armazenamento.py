import threading
import unittest
from datetime import datetime, timedelta, timezone

from backend.armazenamento import ArmazenamentoMemoria


def leitura(minutos_atras=0, estacao="estacao-01", temp=20.0):
    return {"estacao_id": estacao, "temperatura_c": temp,
            "medido_em": datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)}


class TestArmazenamento(unittest.TestCase):
    def test_fila_descarta_a_mais_antiga_quando_enche(self):
        a = ArmazenamentoMemoria(max_leituras=3)
        for i in range(5):
            a.inserir_leitura(leitura(minutos_atras=10 - i, temp=float(i)))
        temps = [l["temperatura_c"] for l in a.leituras_periodo("estacao-01", 24)]
        self.assertEqual(temps, [2.0, 3.0, 4.0])

    def test_ultima_leitura_e_a_mais_recente_e_nao_a_ultima_inserida(self):
        a = ArmazenamentoMemoria()
        a.inserir_leitura(leitura(minutos_atras=1, temp=1.0))
        a.inserir_leitura(leitura(minutos_atras=30, temp=2.0))
        self.assertEqual(a.ultima_leitura("estacao-01")["temperatura_c"], 1.0)

    def test_estacoes_sao_separadas(self):
        a = ArmazenamentoMemoria()
        a.inserir_leitura(leitura(estacao="estacao-02"))
        self.assertIsNone(a.ultima_leitura("estacao-01"))
        self.assertIsNotNone(a.ultima_leitura("estacao-02"))

    def test_alteracao_do_resultado_nao_corrompe_o_armazenamento(self):
        a = ArmazenamentoMemoria()
        a.inserir_leitura(leitura(temp=5.0))
        a.ultima_leitura("estacao-01")["temperatura_c"] = 999
        self.assertEqual(a.ultima_leitura("estacao-01")["temperatura_c"], 5.0)

    def test_envios_simultaneos_nao_perdem_leituras(self):
        a = ArmazenamentoMemoria()
        def enviar():
            for _ in range(200):
                a.inserir_leitura(leitura())
        fios = [threading.Thread(target=enviar) for _ in range(5)]
        for f in fios: f.start()
        for f in fios: f.join()
        self.assertEqual(len(a.leituras_periodo("estacao-01", 24)), 1000)
        ids = {l["id"] for l in a.leituras_periodo("estacao-01", 24)}
        self.assertEqual(len(ids), 1000)


if __name__ == "__main__":
    unittest.main()
