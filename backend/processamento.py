"""Algoritmos de processamento: valores derivados e estatísticas.

Funções pequenas e puras (sem banco, sem Flask), fáceis de testar.
"""
from .config import Config
from .validacao import ResultadoValidacao

ADC_MAX = 4095


def temperatura_combinada(dht: float | None, bmp: float | None) -> float | None:
    """Média dos dois sensores; se só um funcionar, usa o que existe."""
    valores = [v for v in (dht, bmp) if v is not None]
    return round(sum(valores) / len(valores), 1) if valores else None


def luminosidade_percentual(ldr_bruto: int | None) -> float | None:
    """LDR em divisor de tensão: mais luz = mais tensão = valor maior."""
    if ldr_bruto is None:
        return None
    return round(ldr_bruto / ADC_MAX * 100, 1)


def indice_qualidade_ar(mq135_bruto: int | None, base_bruto: int) -> int | None:
    """Índice relativo de 0 a 100 do MQ-135.

    base_bruto é a leitura em ar limpo, depois do pré-aquecimento. O índice
    mede o quanto a leitura passou dessa base. Não é ppm nem o IQAr oficial.
    """
    if mq135_bruto is None:
        return None
    if mq135_bruto <= base_bruto:
        return 0
    return round((mq135_bruto - base_bruto) / (ADC_MAX - base_bruto) * 100)


def classificar_ar(indice: int | None) -> str | None:
    if indice is None:
        return None
    if indice <= 30:
        return "Boa"
    if indice <= 60:
        return "Moderada"
    return "Ruim"


def calcular_chuva_mm(
    distancia_cm: float | None,
    distancia_vazio_cm: float,
    diametro_funil_mm: float,
    diametro_recipiente_mm: float,
) -> float | None:
    """Converte o nível de água do recipiente em milímetros de chuva.

    O funil capta a chuva numa área grande e despeja num tubo estreito:

        volume captado = chuva_mm * area_funil = altura_agua * area_tubo
        chuva_mm = altura_agua * (area_tubo / area_funil)
                 = altura_agua * (d_tubo / d_funil) ** 2

    A altura da água é quanto a distância medida diminuiu desde o tubo vazio.
    """
    if distancia_cm is None:
        return None
    altura_mm = max(0.0, (distancia_vazio_cm - distancia_cm) * 10)
    razao_areas = (diametro_recipiente_mm / diametro_funil_mm) ** 2
    return round(altura_mm * razao_areas, 1)


def chuva_no_periodo(valores: list[float | None], tolerancia_mm: float = 0.2) -> float:
    """Soma os aumentos do acumulado; quedas são esvaziamento do recipiente.

    Aumentos menores que a tolerância são ruído do sensor ultrassônico.
    """
    total = 0.0
    anterior = None
    for atual in valores:
        if atual is None:
            continue
        if anterior is not None and atual - anterior > tolerancia_mm:
            total += atual - anterior
        anterior = atual
    return round(total, 1)


def resumo(valores: list[float | None]) -> dict | None:
    limpos = [v for v in valores if v is not None]
    if not limpos:
        return None
    return {
        "minimo": round(min(limpos), 1),
        "maximo": round(max(limpos), 1),
        "media": round(sum(limpos) / len(limpos), 1),
    }


def montar_registro(resultado: ResultadoValidacao, medido_em, config: Config) -> dict:
    """Junta valores validados e derivados no formato gravado no banco."""
    d = resultado.dados
    indice = indice_qualidade_ar(d.get("mq135_bruto"), config.mq135_base_bruto)
    return {
        "estacao_id": resultado.estacao_id,
        "medido_em": medido_em,
        "temperatura_c": temperatura_combinada(d.get("temperatura_dht"), d.get("temperatura_bmp")),
        "temperatura_dht": d.get("temperatura_dht"),
        "umidade": d.get("umidade"),
        "temperatura_bmp": d.get("temperatura_bmp"),
        "pressao_hpa": d.get("pressao_hpa"),
        "mq135_bruto": d.get("mq135_bruto"),
        "indice_ar": indice,
        "classe_ar": classificar_ar(indice),
        "luminosidade_pct": luminosidade_percentual(d.get("ldr_bruto")),
        "distancia_agua_cm": d.get("distancia_agua_cm"),
        "chuva_mm": calcular_chuva_mm(
            d.get("distancia_agua_cm"),
            config.distancia_vazio_cm,
            config.diametro_funil_mm,
            config.diametro_recipiente_mm,
        ),
        "suspeita": resultado.suspeita,
        "motivos_suspeita": resultado.motivos,
    }
