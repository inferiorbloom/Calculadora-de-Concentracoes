import math

from models.leitorArquivoModel import nome_amostra as _nome_arquivo


class ZScoreModel:
    """Calcula o Z'-Score das concentrações das amostras contra o padrão."""

    def calcular(
        self,
        concentracoes,
        c_padrao,
        erros_concentracao=None,
        nome_padrao=None,
    ):
        """Retorna estatísticas agregadas por elemento das amostras válidas."""
        elementos_padrao = (c_padrao or {}).get("elementos", {})
        nome_padrao = _nome_arquivo(nome_padrao or "")
        valores_por_elemento = {}

        for nome_bloco, bloco in (concentracoes or {}).items():
            erros_bloco = (erros_concentracao or {}).get(nome_bloco, {})
            for nome_amostra, valores in (bloco or {}).items():
                if nome_padrao and nome_amostra == nome_padrao:
                    continue

                erros_amostra = erros_bloco.get(nome_amostra, {})
                valores_amostra = {}

                for chave, valor in (valores or {}).items():
                    elemento = chave[0] if isinstance(chave, tuple) else chave
                    try:
                        valor = float(valor)
                    except (TypeError, ValueError):
                        continue
                    valores_amostra.setdefault(elemento, []).append((valor, chave))

                for elemento, observacoes in valores_amostra.items():
                    if len(observacoes) == 1:
                        valores_por_elemento.setdefault(elemento, []).append(observacoes[0][0])
                        continue

                    ponderadas = []
                    for valor, chave in observacoes:
                        try:
                            erro = float(erros_amostra.get(chave))
                        except (TypeError, ValueError):
                            continue
                        if math.isfinite(erro) and erro > 0:
                            ponderadas.append((valor, 1 / erro ** 2))

                    if ponderadas:
                        soma_pesos = sum(peso for _, peso in ponderadas)
                        valor_consolidado = sum(valor * peso for valor, peso in ponderadas) / soma_pesos
                    else:
                        valor_consolidado = sum(valor for valor, _ in observacoes) / len(observacoes)

                    valores_por_elemento.setdefault(elemento, []).append(valor_consolidado)

        resultado = {}
        for elemento, valores in valores_por_elemento.items():
            info_padrao = elementos_padrao.get(elemento)
            if not isinstance(info_padrao, dict) or len(valores) < 2:
                continue

            try:
                valor_certificado = float(info_padrao["valor"])
                erro_certificado = float(info_padrao["erro"])
            except (KeyError, TypeError, ValueError):
                continue

            media = sum(valores) / len(valores)
            variancia = sum((valor - media) ** 2 for valor in valores) / (len(valores) - 1)
            desvio_padrao = math.sqrt(variancia)
            denominador = math.sqrt(desvio_padrao ** 2 + erro_certificado ** 2)
            z_score = (media - valor_certificado) / denominador if denominador else None

            resultado[elemento] = {
                "media_amostras": media,
                "desvio_padrao_amostras": desvio_padrao,
                "valor_certificado": valor_certificado,
                "erro_certificado": erro_certificado,
                "z_score": z_score,
                "n": len(valores),
            }
        return resultado