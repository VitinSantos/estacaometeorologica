"""Validação e tratamento de dados inconsistentes (Lógica Matemática).

Cada regra abaixo é uma proposição lógica sobre o valor lido:

    valido(x)  =  x é número finito  E  minimo <= x <= maximo

Um valor que não satisfaz a proposição é descartado (vira "ausente") e a
leitura é marcada como suspeita. Se nenhum sensor produzir valor válido,
a leitura inteira é rejeitada.

Também há uma regra de consistência entre sensores:

    suspeita  =  |temperatura_dht - temperatura_bmp| > 3 °C
"""
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

LIMITES_FISICOS = {
    "temperatura_dht": (-40.0, 80.0),
    "umidade": (0.0, 100.0),
    "temperatura_bmp": (-40.0, 85.0),
    "pressao_hpa": (300.0, 1100.0),
    "distancia_agua_cm": (2.0, 400.0),
}
LIMITE_ADC = (0, 4095)
CAMPOS_ANALOGICOS = ("mq135_bruto", "ldr_bruto")
DIVERGENCIA_MAX_C = 3.0
PADRAO_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,39}$")


class ErroValidacao(ValueError):
    def __init__(self, mensagem: str, motivos: list[str] | None = None):
        super().__init__(mensagem)
        self.motivos = motivos or []


@dataclass
class ResultadoValidacao:
    estacao_id: str
    dados: dict
    suspeita: bool = False
    motivos: list[str] = field(default_factory=list)


def _numero_finito(valor) -> float | None:
    """Devolve o valor como float, ou None se não for um número finito."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not math.isfinite(valor):
        return None
    return float(valor)


def validar_leitura(payload) -> ResultadoValidacao:
    if not isinstance(payload, dict):
        raise ErroValidacao("O corpo da requisição deve ser um objeto JSON.")

    estacao_id = payload.get("estacao_id")
    if not isinstance(estacao_id, str) or not PADRAO_ID.match(estacao_id):
        raise ErroValidacao("estacao_id ausente ou inválido (use letras minúsculas, números e hífen).")

    dados: dict = {}
    motivos: list[str] = []

    for campo, (minimo, maximo) in LIMITES_FISICOS.items():
        if payload.get(campo) is None:
            continue
        valor = _numero_finito(payload[campo])
        if valor is None or not (minimo <= valor <= maximo):
            motivos.append(f"{campo} descartado: fora do intervalo físico [{minimo}, {maximo}]")
            continue
        dados[campo] = valor

    for campo in CAMPOS_ANALOGICOS:
        if payload.get(campo) is None:
            continue
        valor = _numero_finito(payload[campo])
        if valor is None or valor != int(valor) or not (LIMITE_ADC[0] <= valor <= LIMITE_ADC[1]):
            motivos.append(f"{campo} descartado: o ADC de 12 bits só produz inteiros de 0 a 4095")
            continue
        dados[campo] = int(valor)

    if not dados:
        raise ErroValidacao("Nenhum valor de sensor válido na leitura.", motivos)

    dht, bmp = dados.get("temperatura_dht"), dados.get("temperatura_bmp")
    if dht is not None and bmp is not None and abs(dht - bmp) > DIVERGENCIA_MAX_C:
        motivos.append(
            f"DHT22 e BMP280 divergem {abs(dht - bmp):.1f} °C (limite {DIVERGENCIA_MAX_C} °C)"
        )

    return ResultadoValidacao(estacao_id, dados, suspeita=bool(motivos), motivos=motivos)


def interpretar_data(texto, agora: datetime | None = None) -> datetime:
    """Interpreta medido_em (ISO 8601). Sem valor, usa o instante atual.

    Rejeita datas mais de 5 minutos no futuro ou com mais de 7 dias.
    """
    agora = agora or datetime.now(timezone.utc)
    if texto is None:
        return agora
    if not isinstance(texto, str):
        raise ErroValidacao("medido_em deve ser texto no formato ISO 8601.")
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError as erro:
        raise ErroValidacao("medido_em não está no formato ISO 8601.") from erro
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    momento = momento.astimezone(timezone.utc)
    if momento > agora + timedelta(minutes=5):
        raise ErroValidacao("medido_em está no futuro.")
    if momento < agora - timedelta(days=7):
        raise ErroValidacao("medido_em tem mais de 7 dias.")
    return momento
