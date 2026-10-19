import re
import unicodedata
from difflib import SequenceMatcher

FATOR_PARA_MG_KG = {"mg/kg": 1, "g/kg": 1000}


class PadraoModel:
    def __init__(self):
        self.c_padrao = {}


def _normalizar_nome(nome):
    """'b) Montana Soil - 2710' -> 'montanasoil2710': sem prefixo a)/b), acentos, maiúsculas e pontuação."""
    texto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode().lower()
    texto = re.sub(r"^\s*[a-z]\)\s*", "", texto)
    return re.sub(r"[^a-z0-9]", "", texto)


def _em_mg_kg(info):
    try:
        return float(info.get("valor")) * FATOR_PARA_MG_KG.get(str(info.get("unidade", "mg/kg")).strip().lower(), 1)
    except (TypeError, ValueError, AttributeError):
        return None


def padroes_semelhantes(novo, existentes, limite_nome=0.88, min_iguais=3, tolerancia=0.01):
    """
    Padrões já cadastrados que parecem ser o mesmo que `novo`. Devolve [(nome, [motivos])].
    - nome: igual ou quase igual, ignorando prefixo a)/b), acentos, maiúsculas, hífens e espaços;
    - valores: pelo menos `min_iguais` elementos (e 80% dos que os dois têm) com o mesmo valor
      depois de converter para mg/kg, o que pega o mesmo material cadastrado em g/kg e em mg/kg.
    Só avisa: pode ser um padrão parecido mas diferente.
    """
    nome_novo = _normalizar_nome(novo.get("nome"))
    valores_novo = {el: _em_mg_kg(info) for el, info in (novo.get("elementos") or {}).items()}
    semelhantes = []
    for padrao in existentes:
        motivos = []
        nome = _normalizar_nome(padrao.get("nome"))
        if nome_novo and nome and (nome == nome_novo or SequenceMatcher(None, nome, nome_novo).ratio() >= limite_nome):
            motivos.append("nome parecido")

        comuns = []
        for elemento, info in (padrao.get("elementos") or {}).items():
            a, b = valores_novo.get(elemento), _em_mg_kg(info)
            if a is not None and b is not None:
                comuns.append(abs(a - b) <= tolerancia * max(abs(a), abs(b), 1e-12))
        iguais = sum(comuns)
        if len(comuns) >= min_iguais and iguais >= max(min_iguais, 0.8 * len(comuns)):
            motivos.append(f"{iguais} de {len(comuns)} elementos com os mesmos valores (já convertidos para mg/kg)")

        if motivos:
            semelhantes.append((padrao["nome"], motivos))
    return semelhantes
