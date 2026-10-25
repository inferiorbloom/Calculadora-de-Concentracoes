import json
import os

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".cx_calculator_config.json")
CHAVE_ULTIMO_DIRETORIO = "ultimo_diretorio"
CHAVE_ABAS_EXPORTAR = "abas_exportar"
CHAVE_TIPO_GRAFICO = "tipo_grafico"
CHAVE_ESTILO_COMPARACAO = "estilo_comparacao"
CHAVE_TEMPO_CONTAGEM = "tempo_contagem"
CHAVE_CERTIFICADOS = "certificados_por_arquivo"
CHAVE_MENOR_LD = "mostrar_menor_ld"
CHAVE_FORMATO_IMAGEM = "formato_imagem"
FORMATOS_IMAGEM = ("png", "svg", "pdf")


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
    """
    Último diretório utilizado, ou None se ele não existir mais (pasta apagada, pendrive removido).
    Uma pasta inexistente como initialdir faz o Windows mostrar "Não é possível abrir o local".
    """
    diretorio = _ler_config().get(CHAVE_ULTIMO_DIRETORIO)
    return diretorio if diretorio and os.path.isdir(diretorio) else None


def salvar_ultimo_diretorio(caminho):
    """Salva a pasta do caminho informado (um arquivo, que pode ainda não existir, ou a própria pasta)."""
    if not caminho:
        return

    caminho = os.path.abspath(os.path.expanduser(caminho))
    # o "Salvar como" devolve um arquivo que ainda não existe: guardar a pasta dele, não o arquivo
    diretorio = caminho if os.path.isdir(caminho) else os.path.dirname(caminho)
    if not os.path.isdir(diretorio):
        return
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


def carregar_estilo_comparacao():
    """Estilo dos gráficos comparativos escolhido da última vez (barras, linhas), ou None."""
    return _ler_config().get(CHAVE_ESTILO_COMPARACAO)


def salvar_estilo_comparacao(estilo):
    _gravar_config(**{CHAVE_ESTILO_COMPARACAO: estilo})


def carregar_tempo_contagem():
    """Último tempo de contagem (texto, como foi digitado) da Sensibilidade, ou ""."""
    tempo = _ler_config().get(CHAVE_TEMPO_CONTAGEM)
    return str(tempo) if tempo not in (None, "") else ""


def salvar_tempo_contagem(tempo):
    _gravar_config(**{CHAVE_TEMPO_CONTAGEM: str(tempo)})


def carregar_certificados(alvo=None):
    """
    Padrão certificado usado da última vez com cada arquivo padrão, de um alvo:
    {"arquivos": {nome do arquivo: certificado}, "ultimo": certificado ou None}.
    """
    dados = _ler_config().get(CHAVE_CERTIFICADOS)
    dados = dados.get(alvo or "") if isinstance(dados, dict) else None
    if not isinstance(dados, dict):
        return {"arquivos": {}, "ultimo": None}
    arquivos = dados.get("arquivos")
    return {"arquivos": dict(arquivos) if isinstance(arquivos, dict) else {}, "ultimo": dados.get("ultimo")}


def salvar_certificado(alvo, arquivo, certificado):
    """Lembra o certificado escolhido para o arquivo padrão (pelo nome, sem a pasta) neste alvo."""
    if not arquivo or not certificado:
        return
    todos = _ler_config().get(CHAVE_CERTIFICADOS)
    todos = todos if isinstance(todos, dict) else {}
    dados = carregar_certificados(alvo)
    dados["arquivos"][arquivo] = certificado
    dados["ultimo"] = certificado
    todos[alvo or ""] = dados
    _gravar_config(**{CHAVE_CERTIFICADOS: todos})


def carregar_mostrar_menor_ld():
    """True: valores abaixo do LD aparecem como "< LD" na tabela e no Excel (o padrão é mostrar o valor)."""
    return _ler_config().get(CHAVE_MENOR_LD) is True


def salvar_mostrar_menor_ld(mostrar):
    _gravar_config(**{CHAVE_MENOR_LD: bool(mostrar)})


def carregar_formato_imagem():
    """Formato das imagens exportadas: "png" (o padrão), "svg" ou "pdf"."""
    formato = _ler_config().get(CHAVE_FORMATO_IMAGEM)
    return formato if formato in FORMATOS_IMAGEM else "png"


def salvar_formato_imagem(formato):
    if formato in FORMATOS_IMAGEM:
        _gravar_config(**{CHAVE_FORMATO_IMAGEM: formato})
