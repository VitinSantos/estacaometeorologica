"""Armazenamento das leituras na MEMÓRIA do servidor (sem banco de dados).

Guarda as últimas leituras numa fila com tamanho máximo: quando enche, a mais
antiga é descartada. Simples e rápido, mas com uma limitação importante:

    Na Vercel o servidor é "serverless". Se ele ficar parado ou for
    reiniciado, a memória é zerada e o histórico recomeça. Com o ESP32
    enviando a cada 60 s o servidor fica ativo e isso quase não acontece.

Se um dia for preciso guardar para sempre, basta criar outra classe com os
mesmos métodos (por exemplo, usando PostgreSQL) e trocá-la em app.py.
"""
import threading
from collections import deque
from datetime import datetime, timedelta, timezone

from .estacoes import ESTACOES

MAX_LEITURAS = 10080      # 7 dias com uma leitura por minuto
LIMITE_CONSULTA = 5000    # máximo devolvido de uma vez


class ArmazenamentoMemoria:
    def __init__(self, max_leituras: int = MAX_LEITURAS):
        self._leituras: deque = deque(maxlen=max_leituras)
        self._estacoes = [dict(e) for e in ESTACOES]
        self._proximo_id = 1
        # Duas requisições podem chegar ao mesmo tempo; o cadeado evita
        # que as duas mexam na fila no mesmo instante.
        self._cadeado = threading.Lock()

    def listar_estacoes(self) -> list[dict]:
        return [dict(e) for e in self._estacoes]

    def estacao_existe(self, estacao_id: str) -> bool:
        return any(e["id"] == estacao_id for e in self._estacoes)

    def inserir_leitura(self, registro: dict) -> dict:
        with self._cadeado:
            salvo = dict(registro)
            salvo["id"] = self._proximo_id
            self._proximo_id += 1
            self._leituras.append(salvo)
            return dict(salvo)

    def ultima_leitura(self, estacao_id: str) -> dict | None:
        with self._cadeado:
            do_posto = [l for l in self._leituras if l["estacao_id"] == estacao_id]
        return dict(max(do_posto, key=lambda l: l["medido_em"])) if do_posto else None

    def leituras_periodo(self, estacao_id: str, horas: int) -> list[dict]:
        inicio = datetime.now(timezone.utc) - timedelta(hours=horas)
        with self._cadeado:
            filtradas = [dict(l) for l in self._leituras
                         if l["estacao_id"] == estacao_id and l["medido_em"] >= inicio]
        filtradas.sort(key=lambda l: l["medido_em"])
        return filtradas[-LIMITE_CONSULTA:]
