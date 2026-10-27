"""Configuração lida de variáveis de ambiente.

Nenhum segredo fica no código: a chave da API vem do
ambiente (arquivo .env no computador, painel de variáveis na Vercel).
"""
import os
from dataclasses import dataclass
from pathlib import Path


def carregar_dotenv(caminho: str = ".env") -> None:
    """Lê um arquivo .env simples (CHAVE=valor) e preenche os.environ.

    Só serve para desenvolvimento local. Variáveis que já existem no
    ambiente não são sobrescritas.
    """
    arquivo = Path(caminho)
    if not arquivo.is_file():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Config:
    api_key: str | None
    distancia_vazio_cm: float
    diametro_funil_mm: float
    diametro_recipiente_mm: float
    mq135_base_bruto: int
    estacao_padrao: str
    limite_online_s: int

    @classmethod
    def do_ambiente(cls) -> "Config":
        return cls(
            api_key=os.environ.get("API_KEY_ESTACAO") or None,
            distancia_vazio_cm=float(os.environ.get("DISTANCIA_VAZIO_CM", "20")),
            diametro_funil_mm=float(os.environ.get("DIAMETRO_FUNIL_MM", "110")),
            diametro_recipiente_mm=float(os.environ.get("DIAMETRO_RECIPIENTE_MM", "40")),
            mq135_base_bruto=int(os.environ.get("MQ135_BASE_BRUTO", "600")),
            estacao_padrao=os.environ.get("ESTACAO_PADRAO", "estacao-01"),
            limite_online_s=int(os.environ.get("LIMITE_ONLINE_S", "180")),
        )
