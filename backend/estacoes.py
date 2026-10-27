"""Estações cadastradas. Para trocar nome ou coordenadas, edite esta lista.

A estação "ativa" é a que realmente recebe dados do ESP32. As outras
aparecem no mapa como planejadas.
"""

ESTACOES = [
    {"id": "estacao-01", "nome": "Estação 01, Centro", "descricao": "Estação principal",
     "latitude": -23.5505, "longitude": -46.6333, "ativa": True},
    {"id": "estacao-02", "nome": "Estação 02, Pinheiros", "descricao": "Planejada",
     "latitude": -23.5614, "longitude": -46.7020, "ativa": False},
    {"id": "estacao-03", "nome": "Estação 03, Tatuapé", "descricao": "Planejada",
     "latitude": -23.5405, "longitude": -46.5760, "ativa": False},
]
