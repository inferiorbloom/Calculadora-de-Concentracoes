"""
Regras de qualidade usadas pela tabela de resultados, pelo Excel e pela análise multivariada:
qual LD vale para cada valor, quando um valor está abaixo dele e a recuperação de um material certificado.
"""

from models.PadraoModel import FATOR_PARA_MG_KG

LIMITE_RECUPERACAO = 0.10  # recuperação fora de 100% ± 10% fica destacada na tabela
TEXTO_MENOR_LD = "< LD"


def _para_float(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def ld_de_referencia(ld_resultado, nome_amostra, elemento, nome_padrao):
    """LD da própria amostra; se não houver, o do padrão; senão, o primeiro disponível (ou None)."""
    ld_resultado = ld_resultado or {}
    for nome in (nome_amostra, nome_padrao):
        valor = _para_float((ld_resultado.get(nome) or {}).get(elemento))
        if valor is not None:
            return valor
    for dados in ld_resultado.values():
        valor = _para_float((dados or {}).get(elemento))
        if valor is not None:
            return valor
    return None


def abaixo_do_ld(valor, ld):
    """True quando há valor e LD e o valor é menor que o LD (a opção "< LD" troca só esses)."""
    valor = _para_float(valor)
    return valor is not None and ld is not None and valor < ld


def em_mg_kg(valor, unidade):
    valor = _para_float(valor)
    if valor is None:
        return None
    return valor * FATOR_PARA_MG_KG.get(str(unidade or "mg/kg").strip().lower(), 1)


def recuperacao(valor, unidade, info_certificado):
    """
    Recuperação (%) = medido / certificado × 100, com os dois em mg/kg.
    info_certificado: {"valor", "unidade", ...} do elemento no padrão certificado. None se não der para calcular.
    """
    if not info_certificado:
        return None
    medido = em_mg_kg(valor, unidade)
    certificado = em_mg_kg(info_certificado.get("valor"), info_certificado.get("unidade"))
    if medido is None or not certificado:
        return None
    return 100 * medido / certificado


def recuperacao_fora(percentual):
    return percentual is not None and abs(percentual - 100) > 100 * LIMITE_RECUPERACAO
