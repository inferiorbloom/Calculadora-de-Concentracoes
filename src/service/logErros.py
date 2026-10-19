import datetime
import traceback

from resource_utils import ensure_directory, user_data_path

# o .exe roda sem console: sem este arquivo, o detalhe de um erro inesperado se perde
ARQUIVO_LOG = user_data_path("logs", "erros.log")


def registrar_erro(erro):
    """Grava o traceback completo no log e devolve o caminho do arquivo (ou None, se não conseguir gravar)."""
    try:
        ensure_directory(user_data_path("logs"))
        with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"\n===== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
            arquivo.write("".join(traceback.format_exception(type(erro), erro, erro.__traceback__)))
        return ARQUIVO_LOG
    except OSError:
        return None


def mensagem_erro_inesperado(erro):
    """Texto para o usuário: o que deu errado e onde está o detalhe técnico."""
    caminho = registrar_erro(erro)
    texto = f"Ocorreu um erro inesperado:\n{type(erro).__name__}: {erro}"
    if caminho:
        texto += f"\n\nO detalhe técnico foi salvo em:\n{caminho}"
    return texto
