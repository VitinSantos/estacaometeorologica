"""Executa o projeto no seu computador: python run_local.py

Abre o dashboard em http://localhost:5000. Os dados ficam na memória e somem
ao reiniciar. Defina API_KEY_ESTACAO no arquivo .env.
"""
from backend.config import carregar_dotenv

carregar_dotenv()

from backend.app import criar_app  # noqa: E402

if __name__ == "__main__":
    criar_app(servir_estaticos=True).run(host="127.0.0.1", port=5000, debug=True)
