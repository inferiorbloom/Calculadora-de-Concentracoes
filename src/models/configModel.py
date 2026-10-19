import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".cx_calculator_config.json")
CHAVE_ULTIMO_DIRETORIO = "ultimo_diretorio"
CHAVE_ABAS_EXPORTAR = "abas_exportar"
CHAVE_TIPO_GRAFICO = "tipo_grafico"


def _ler_config():
    """Lê o arquivo de configuração inteiro ({} se não existir ou estiver corrompido)."""
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return {}

    return dados if isinstance(dados, dict) else {}


def _gravar_config(**valores):
    """Atualiza só as chaves informadas, mantendo as demais configurações."""
    dados = _ler_config()
    dados.update(valores)

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def carregar_ultimo_diretorio():
    """Carrega o último diretório utilizado a partir do arquivo de configuração."""
    return _ler_config().get(CHAVE_ULTIMO_DIRETORIO)


def salvar_ultimo_diretorio(caminho):
    """Salva o último diretório utilizado no arquivo de configuração."""
    if not caminho:
        return

    if os.path.isfile(caminho):
        diretorio = os.path.dirname(caminho)
    else:
        diretorio = caminho

    diretorio = os.path.abspath(os.path.expanduser(diretorio))
    _gravar_config(**{CHAVE_ULTIMO_DIRETORIO: diretorio})


def carregar_abas_exportar():
    """Abas escolhidas para exportar, ou None se o usuário nunca escolheu (exporta todas)."""
    abas = _ler_config().get(CHAVE_ABAS_EXPORTAR)
    return list(abas) if isinstance(abas, list) else None


def salvar_abas_exportar(abas):
    _gravar_config(**{CHAVE_ABAS_EXPORTAR: list(abas)})


def carregar_tipo_grafico():
    """Tipo de gráfico escolhido da última vez (anel, pizza, pizza3d, barras), ou None."""
    return _ler_config().get(CHAVE_TIPO_GRAFICO)


def salvar_tipo_grafico(tipo):
    _gravar_config(**{CHAVE_TIPO_GRAFICO: tipo})
