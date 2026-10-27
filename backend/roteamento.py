"""Corrige o caminho da requisição quando a Vercel o entrega trocado.

Na Vercel, todas as rotas /api/... passam por UMA função (api/index.py).
O vercel.json reescreve  /api/saude  ->  /api/index?rota=saude.

Se o Flask receber o caminho original (/api/saude), nada muda. Se receber o
caminho da função (/api/index), este middleware reconstrói a rota original a
partir do parâmetro "rota". Assim o sistema funciona nos dois casos.
"""
import re
from urllib.parse import parse_qsl, urlencode

CAMINHOS_DA_FUNCAO = {"", "/", "/api", "/api/", "/api/index", "/api/index.py"}
ROTA_VALIDA = re.compile(r"^[a-z0-9_-]+(/[a-z0-9_-]+)*$")


class CorrigeCaminho:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO", "") in CAMINHOS_DA_FUNCAO:
            parametros = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
            rota = next((v for k, v in parametros if k == "rota"), None)
            if rota is not None:
                rota = rota.strip("/")
                if ROTA_VALIDA.match(rota):
                    environ["PATH_INFO"] = "/api/" + rota
                    resto = [(k, v) for k, v in parametros if k != "rota"]
                    environ["QUERY_STRING"] = urlencode(resto)
        return self.wsgi_app(environ, start_response)
