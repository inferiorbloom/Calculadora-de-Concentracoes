from collections import Counter
import numpy as np
import pandas as pd
from models.elementosQuimicos import z_do_elemento
from models.arredondamentoModel import ArredondamentoModel


def montar_titulo_coluna(elemento, energia, unidade, possui_duplicata):
    if possui_duplicata:
        if unidade:
            return f"{elemento} ({energia:.3f} keV, {unidade})"
        return f"{elemento} ({energia:.3f} keV)"

    if unidade:
        return f"{elemento} ({unidade})"

    return elemento


class AbaResultadosModel:
    """Monta o DataFrame usado na aba 'Resultados' (concentração, erro e erro relativo)."""

    def __init__(self):
        self.arredondamento = ArredondamentoModel()

    def montar(self, concentracoes, erros_propagados, unidade_padrao, aplicar_arredondamento=True):
        """
        Retorna (df_analise, elementos_ordenados, contagem_elementos).

        df_analise: DataFrame com colunas MultiIndex (nome_coluna, "C"/"Erro"/"Erro (%)").
        elementos_ordenados / contagem_elementos: precisos depois, na hora de
        escrever o cabeçalho com os LDs no exportarModel.
        """
        analise = {}
        elementos_encontrados = set()

        for bloco in concentracoes.values():
            if isinstance(bloco, dict):
                for nome_amostra, valores in bloco.items():
                    analise.setdefault(nome_amostra, {})
                    for elemento, valor in valores.items():
                        elementos_encontrados.add(elemento)
                        analise[nome_amostra].setdefault(elemento, {})
                        analise[nome_amostra][elemento]["C"] = valor

        for bloco in erros_propagados.values():
            if isinstance(bloco, dict):
                for nome_amostra, amostra_valores in bloco.items():
                    analise.setdefault(nome_amostra, {})
                    for elemento, erro in amostra_valores.items():
                        elementos_encontrados.add(elemento)
                        analise[nome_amostra].setdefault(elemento, {})
                        analise[nome_amostra][elemento]["Erro"] = erro

        if not analise:
            return pd.DataFrame(), [], Counter()

        

        elementos_ordenados = sorted(
            elementos_encontrados,
            key=lambda x: (z_do_elemento(x[0]), x[1])
        )

        #print(elementos_ordenados)
        #print("__________________")
        #print("Sorted:")
        #print(sorted(elementos_encontrados))
        #print("__________________")
        #print("K encontrado:",
      #[e for e in elementos_encontrados if e[0] == "K"])

        contagem_elementos = Counter(elemento for elemento, energia in elementos_ordenados)

        colunas = []
        for elemento, energia in elementos_ordenados:
            unidade = unidade_padrao.get(elemento, "")
            possui_duplicata = contagem_elementos[elemento] > 1
            nome_coluna = montar_titulo_coluna(elemento, energia, unidade, possui_duplicata)

            colunas.append((nome_coluna, "C"))
            colunas.append((nome_coluna, "Erro"))
            colunas.append((nome_coluna, "Erro (%)"))

        linhas = []
        for nome_amostra, elementos in analise.items():
            linha = {coluna: np.nan for coluna in colunas}
            for elemento in elementos_ordenados:
                unidade = unidade_padrao.get(elemento[0], "")
                possui_duplicata = contagem_elementos[elemento[0]] > 1
                nome_coluna = montar_titulo_coluna(elemento[0], elemento[1], unidade, possui_duplicata)

                c_col = "C"
                e_col = "Erro"
                valor = elementos.get(elemento, {}).get("C", "")
                erro = elementos.get(elemento, {}).get("Erro", "")

                if valor != "":
                    if aplicar_arredondamento:
                        valor_final, erro_final, _ = self.arredondamento.formatar_resultado(valor, erro, elemento[0])
                    else:
                        valor_final, erro_final = valor, erro
                    linha[(nome_coluna, c_col)] = float(valor_final)
                    linha[(nome_coluna, e_col)] = float(erro_final)
                    # quanto o erro vale, em %, da concentração
                    if float(valor_final) != 0 and not np.isnan(float(erro_final)):
                        linha[(nome_coluna, "Erro (%)")] = abs(float(erro_final) / float(valor_final)) * 100

            linhas.append((nome_amostra, linha))

        df_analise = pd.DataFrame(
            [linha for _, linha in linhas],
            index=[nome_amostra for nome_amostra, _ in linhas],
            columns=pd.MultiIndex.from_tuples(colunas),
        )

        #print("df_analise")
        #print(df_analise)
        #print("Debug Aba resultados")
        #print(df_analise.loc[["060723ab","060723ac","060723ad"]])

        # Mantemos valores numéricos como float e deixamos a exportação decidir
        # a representação visual para células vazias com '-'.
        df_analise = df_analise.astype(object)

        #print("\n========== DF_ANALISE ==========")
        #print(df_analise.to_string())

        return df_analise, elementos_ordenados, contagem_elementos

    LINHAS_ESTATISTICA = ["Média", "Desvio padrão", "DPR (%)"]

    def montar_estatisticas(self, df_analise, nome_padrao=None):
        """
        Linhas que vão abaixo das amostras: média e desvio padrão amostral (n - 1) de cada coluna,
        e DPR (%) = desvio padrão / média × 100, só nas colunas "C".
        O próprio padrão (se também for amostra) fica fora da conta.
        """
        if df_analise is None or df_analise.empty:
            return pd.DataFrame()

        amostras = df_analise.drop(index=[nome_padrao], errors="ignore") if nome_padrao else df_analise
        numeros = amostras.apply(pd.to_numeric, errors="coerce")
        media = numeros.mean()
        desvio = numeros.std(ddof=1)  # NaN quando houver menos de 2 valores

        relativo = (desvio / media.where(media != 0)).abs() * 100
        colunas_c = [coluna[1] == "C" for coluna in df_analise.columns]
        relativo = relativo.where(colunas_c)

        df_estatisticas = pd.DataFrame(
            [media, desvio, relativo],
            index=self.LINHAS_ESTATISTICA,
            columns=df_analise.columns,
        )
        return df_estatisticas.astype(object)

