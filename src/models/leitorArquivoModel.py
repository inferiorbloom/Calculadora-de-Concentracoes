import os
from dataclasses import dataclass

from models.elementosQuimicos import ELEMENTOS


class ArquivoInvalidoError(ValueError):
    """Arquivo .txt que não dá para ler; a mensagem já diz qual arquivo e qual linha."""


@dataclass
class Pico:
    z: int
    energia: float  # keV, arredondada em 3 casas (é a chave que casa amostra com padrão)
    area: float
    erro: float

    @property
    def elemento(self):
        """Símbolo do elemento, ou None se o Z não estiver na tabela."""
        return ELEMENTOS.get(self.z)

    @property
    def chave(self):
        return (self.elemento, self.energia)


def nome_amostra(caminho):
    """Nome usado em todo o programa para identificar o arquivo: o nome sem extensão."""
    return os.path.splitext(os.path.basename(str(caminho)))[0].strip()


def _ler_texto(caminho):
    try:
        with open(caminho, "r", encoding="utf-8-sig") as arquivo:
            return arquivo.read()
    except UnicodeDecodeError:
        with open(caminho, "r", encoding="latin-1") as arquivo:
            return arquivo.read()


def _numero(texto):
    return float(texto.strip().replace(",", "."))


def ler_picos(caminho):
    """
    Lê os picos (Z, energia, área, erro) de um .txt do equipamento.

    Não depende de um número fixo de linhas de cabeçalho: linhas que não começam com um número
    (cabeçalho, rodapé) e linhas em branco são ignoradas. Aceita "," como separador e também
    ";" com vírgula decimal (arquivo salvo pelo Excel em português).
    """
    nome = os.path.basename(str(caminho))
    try:
        texto = _ler_texto(caminho)
    except OSError as erro:
        raise ArquivoInvalidoError(f"Não foi possível abrir {nome}: {erro}") from erro

    picos = []
    for numero_linha, linha in enumerate(texto.splitlines(), start=1):
        linha = linha.strip()
        if not linha:
            continue

        partes = linha.split(";") if ";" in linha else linha.split(",")
        try:
            z = _numero(partes[0])
        except ValueError:
            continue  # cabeçalho ("Live Time:", "Photopeaks:", ...)

        try:
            if len(partes) < 4:
                raise ValueError("faltam colunas")
            energia, area, erro = (_numero(p) for p in partes[1:4])
            if z != int(z):
                raise ValueError("o número atômico não é inteiro")
        except ValueError as motivo:
            raise ArquivoInvalidoError(
                f"{nome}, linha {numero_linha}: não foi possível ler o pico ({motivo}).\n\n{linha}"
            ) from None

        picos.append(Pico(int(z), round(energia, 3), area, erro))

    if not picos:
        raise ArquivoInvalidoError(f"{nome}: nenhum pico encontrado. É um arquivo de aquisição do equipamento?")
    return picos
