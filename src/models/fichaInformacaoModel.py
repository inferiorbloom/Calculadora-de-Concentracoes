"""
Leitura da ficha de informação (.docx) do CX Rays.

Cada linha de medida da ficha tem o formato:
    <código> – <nome / descrição>
    ex.: 041125ad – S2 (Solo coletado no mês 2)
         270426ab – Pd Folha tomate 2 - 1573a

O código (6 dígitos da data DDMMAA + letras) é o mesmo nome do arquivo da medida,
então ele é a chave que liga a ficha às amostras do programa.

O .docx é lido direto do XML (é um zip), sem depender do python-docx.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

# código: 6 dígitos + 1 a 3 letras; separador: travessão, meia-risca ou hífen
CODIGO = re.compile(r"\d{6}[a-zA-Z]{1,3}")
LINHA = re.compile(r"^\s*(\d{6}[a-zA-Z]{1,3})\s*[–—-]\s*(.+?)\s*$")
# "S2 (Solo coletado no mês 2) * obs" -> nome "S2", descrição "Solo coletado no mês 2", obs "obs"
NOME_CURTO = re.compile(r"^([^(*]+?)\s*(?:\((.*?)\))?\s*(?:\*\s*(.*))?$")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class FichaInvalidaError(Exception):
    """A ficha não pôde ser lida (não é um .docx válido)."""


def codigo_amostra(nome):
    """Código da medida dentro de um nome ("290426ab", "290426AB.txt", "C:\\...\\290426ab") em minúsculas."""
    texto = str(nome or "")
    m = CODIGO.search(texto)
    return m.group(0).lower() if m else texto.strip().lower()


def nome_da_amostra(nomes, amostra):
    """Nome dado na ficha (ou editado) para a amostra; "" se não houver."""
    return (nomes or {}).get(codigo_amostra(amostra), "")


def _texto(elemento):
    """Texto de um parágrafo/célula, com tabulações e quebras virando espaço."""
    partes = []
    for no in elemento.iter():
        if no.tag == W + "t" and no.text:
            partes.append(no.text)
        elif no.tag in (W + "tab", W + "br"):
            partes.append(" ")
    return "".join(partes)


def _textos(elemento):
    """Parágrafos e linhas de tabela na ordem em que aparecem na ficha (as células de uma linha unidas por " – ")."""
    for filho in elemento:
        if filho.tag == W + "p":
            yield _texto(filho)
        elif filho.tag == W + "tbl":
            for linha in filho.iter(W + "tr"):
                celulas = [_texto(c).strip() for c in linha.findall(W + "tc")]
                yield " – ".join(c for c in celulas if c)
        else:
            # caixas de conteúdo (w:sdt) e afins guardam parágrafos dentro
            yield from _textos(filho)


def ler_ficha(caminho):
    """Retorna {código: {nome, descricao, obs, grupo, texto}} na ordem da ficha."""
    try:
        with zipfile.ZipFile(caminho) as arquivo:
            raiz = ET.fromstring(arquivo.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as erro:
        raise FichaInvalidaError(
            f"Não foi possível ler a ficha. Ela precisa ser um arquivo do Word (.docx).\n\n({erro})"
        ) from erro

    corpo = raiz.find(W + "body")
    amostras = {}
    grupo = ""
    for texto in _textos(corpo if corpo is not None else raiz):
        texto = texto.strip()
        if not texto:
            continue
        m = LINHA.match(texto)
        if not m:
            # cabeçalhos como "Medidas dos Padrões:" ou "Amostras:" viram o grupo
            if texto.endswith(":"):
                grupo = texto.rstrip(":").strip()
            continue
        codigo, resto = m.group(1).lower(), m.group(2)
        n = NOME_CURTO.match(resto)
        nome, descricao, obs = (n.group(1), n.group(2) or "", n.group(3) or "") if n else (resto, "", "")
        amostras[codigo] = {
            "nome": nome.strip(),
            "descricao": descricao.strip(),
            "obs": obs.strip(),
            "grupo": "Calibração" if "calibra" in resto.lower() else grupo,
            "texto": resto,
        }
    return amostras
