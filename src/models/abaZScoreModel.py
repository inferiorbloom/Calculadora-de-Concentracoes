import pandas as pd


class AbaZScoreModel:
    """Monta a aba de exportação dos resultados do Z'-Score."""

    COLUNAS = [
        "Elemento",
        "n",
        "Média",
        "Desvio padrão",
        "Certificado",
        "Erro certificado",
        "Z'-Score",
    ]

    def montar(self, resultados=None):
        linhas = []
        for elemento, dados in sorted((resultados or {}).items()):
            linhas.append(
                {
                    "Elemento": elemento,
                    "n": dados.get("n", "-"),
                    "Média": dados.get("media_amostras", "-"),
                    "Desvio padrão": dados.get("desvio_padrao_amostras", "-"),
                    "Certificado": dados.get("valor_certificado", "-"),
                    "Erro certificado": dados.get("erro_certificado", "-"),
                    "Z'-Score": dados.get("z_score", "-"),
                }
            )

        return pd.DataFrame(linhas, columns=self.COLUNAS)