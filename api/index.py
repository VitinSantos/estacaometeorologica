"""Ponto de entrada da Vercel: expõe o objeto WSGI chamado `app`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import criar_app  # noqa: E402

app = criar_app()
