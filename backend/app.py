"""API Flask da estação meteorológica.

Rotas -> validação -> processamento -> repositório (banco).
"""
import hmac
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from . import geo, processamento
from .config import Config
from .roteamento import CorrigeCaminho
from .armazenamento import ArmazenamentoMemoria
from .validacao import ErroValidacao, interpretar_data, validar_leitura

PASTA_PUBLICA = Path(__file__).resolve().parent.parent / "public"


def _para_json(registro: dict | None) -> dict | None:
    """Converte datas em texto ISO 8601 para poder serializar em JSON."""
    if registro is None:
        return None
    saida = dict(registro)
    for chave, valor in saida.items():
        if isinstance(valor, datetime):
            saida[chave] = valor.astimezone(timezone.utc).isoformat()
    return saida


def criar_app(repositorio=None, config: Config | None = None, servir_estaticos: bool = False) -> Flask:
    config = config or Config.do_ambiente()
    repo = repositorio or ArmazenamentoMemoria()

    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    app.json.ensure_ascii = False
    app.wsgi_app = CorrigeCaminho(app.wsgi_app)

    def exige_chave(funcao):
        @wraps(funcao)
        def envolvida(*args, **kwargs):
            if not config.api_key:
                return jsonify(erro="Servidor sem API_KEY_ESTACAO configurada."), 503
            enviada = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(enviada.encode(), config.api_key.encode()):
                return jsonify(erro="Chave de API inválida."), 401
            return funcao(*args, **kwargs)
        return envolvida

    def horas_do_pedido() -> int:
        try:
            horas = int(request.args.get("horas", 24))
        except ValueError:
            raise ErroValidacao("horas deve ser um inteiro.")
        if not 1 <= horas <= 168:
            raise ErroValidacao("horas deve estar entre 1 e 168.")
        return horas

    @app.get("/api/saude")
    def saude():
        return jsonify(status="ok", armazenamento="memoria")

    @app.post("/api/leituras")
    @exige_chave
    def receber_leitura():
        corpo = request.get_json(silent=True)
        resultado = validar_leitura(corpo)
        medido_em = interpretar_data(corpo.get("medido_em"))
        if not repo.estacao_existe(resultado.estacao_id):
            return jsonify(erro="Estação desconhecida."), 404
        registro = processamento.montar_registro(resultado, medido_em, config)
        salvo = repo.inserir_leitura(registro)
        return jsonify(leitura=_para_json(salvo)), 201

    @app.get("/api/leituras/ultima")
    def ultima():
        estacao_id = request.args.get("estacao_id", config.estacao_padrao)
        leitura = repo.ultima_leitura(estacao_id)
        if leitura is None:
            return jsonify(leitura=None, online=False, segundos_desde_ultima=None)
        segundos = int((datetime.now(timezone.utc) - leitura["medido_em"]).total_seconds())
        return jsonify(
            leitura=_para_json(leitura),
            online=segundos <= config.limite_online_s,
            segundos_desde_ultima=max(segundos, 0),
        )

    @app.get("/api/leituras")
    def historico():
        estacao_id = request.args.get("estacao_id", config.estacao_padrao)
        leituras = repo.leituras_periodo(estacao_id, horas_do_pedido())
        return jsonify(leituras=[_para_json(l) for l in leituras])

    @app.get("/api/estatisticas")
    def estatisticas():
        estacao_id = request.args.get("estacao_id", config.estacao_padrao)
        horas = horas_do_pedido()
        leituras = repo.leituras_periodo(estacao_id, horas)
        coluna = lambda nome: [l[nome] for l in leituras]
        return jsonify(
            periodo_horas=horas,
            total_leituras=len(leituras),
            leituras_suspeitas=sum(1 for l in leituras if l["suspeita"]),
            temperatura_c=processamento.resumo(coluna("temperatura_c")),
            umidade=processamento.resumo(coluna("umidade")),
            pressao_hpa=processamento.resumo(coluna("pressao_hpa")),
            luminosidade_pct=processamento.resumo(coluna("luminosidade_pct")),
            indice_ar=processamento.resumo(coluna("indice_ar")),
            chuva_periodo_mm=processamento.chuva_no_periodo(coluna("chuva_mm")),
        )

    @app.get("/api/estacoes")
    def estacoes():
        return jsonify(estacoes=repo.listar_estacoes())

    @app.get("/api/estacoes/proxima")
    def estacoes_por_proximidade():
        try:
            lat = float(request.args["lat"])
            lon = float(request.args["lon"])
        except (KeyError, ValueError):
            raise ErroValidacao("Informe lat e lon numéricos.")
        if not geo.validar_coordenadas(lat, lon):
            raise ErroValidacao("Coordenadas fora do intervalo válido.")
        ordenadas = geo.ordenar_por_distancia(lat, lon, repo.listar_estacoes())
        return jsonify(estacoes=ordenadas, mais_proxima=ordenadas[0] if ordenadas else None)

    @app.errorhandler(ErroValidacao)
    def erro_validacao(erro):
        return jsonify(erro=str(erro), motivos=erro.motivos), 422

    @app.errorhandler(404)
    def nao_encontrado(_):
        # "caminho" mostra o que o servidor realmente recebeu (ajuda a depurar o deploy).
        return jsonify(erro="Rota não encontrada.", caminho=request.path), 404

    @app.errorhandler(405)
    def metodo_nao_permitido(_):
        return jsonify(erro="Método não permitido."), 405

    @app.errorhandler(413)
    def corpo_grande(_):
        return jsonify(erro="Corpo da requisição grande demais."), 413

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        if isinstance(erro, HTTPException):
            return jsonify(erro=erro.description), erro.code
        app.logger.exception("Erro inesperado: %s", erro)
        return jsonify(erro="Erro interno do servidor."), 500

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        if request.path.startswith("/api/"):
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    if servir_estaticos:
        @app.get("/")
        def pagina_inicial():
            return send_from_directory(PASTA_PUBLICA, "index.html")

        @app.get("/<path:caminho>")
        def arquivos(caminho):
            return send_from_directory(PASTA_PUBLICA, caminho)

    return app
