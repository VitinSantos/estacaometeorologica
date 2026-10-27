"""Geometria analítica aplicada à geolocalização das estações.

Cada estação é um ponto (latitude, longitude) sobre a esfera terrestre.
Duas formas de medir a distância entre dois pontos:

1. Haversine: distância sobre a superfície da esfera (círculo máximo).
2. Euclidiana: projeta os pontos num plano e usa d = sqrt(dx^2 + dy^2).
   Boa aproximação para distâncias curtas, como dentro de uma cidade.
"""
import math

RAIO_TERRA_KM = 6371.0088


def validar_coordenadas(lat: float, lon: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lon <= 180


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(a))


def distancia_euclidiana_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Projeção equirretangular: x encolhe com o cosseno da latitude média."""
    lat_media = math.radians((lat1 + lat2) / 2)
    x = math.radians(lon2 - lon1) * math.cos(lat_media) * RAIO_TERRA_KM
    y = math.radians(lat2 - lat1) * RAIO_TERRA_KM
    return math.hypot(x, y)


def ordenar_por_distancia(lat: float, lon: float, estacoes: list[dict]) -> list[dict]:
    """Devolve cópias das estações com distancia_km, da mais perto à mais longe."""
    com_distancia = []
    for estacao in estacoes:
        copia = dict(estacao)
        copia["distancia_km"] = round(
            haversine_km(lat, lon, estacao["latitude"], estacao["longitude"]), 2
        )
        com_distancia.append(copia)
    return sorted(com_distancia, key=lambda e: e["distancia_km"])
