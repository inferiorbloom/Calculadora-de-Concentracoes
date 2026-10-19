import pandas as pd
from models.elementosQuimicos import z_do_elemento


class AbaSLDModel:
    """Monta a aba com LD e sensibilidade por amostra e elemento."""

    COLUNAS = ["Amostra", "Elemento", "Energia (keV)", "LD", "Sensibilidade"]
    CHAVES = COLUNAS[:3]
    VALORES = COLUNAS[3:]

    @staticmethod
    def _chave_energia(energia):
        try:
            return 0, float(energia)
        except (TypeError, ValueError):
            return 1, str(energia)

    @staticmethod
    def _tem_valor(valor):
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return False
        return str(valor).strip() not in ["", "-", "--", "—", "nan", "NaN", "None"]

    def montar(self, ld_resultado=None, sensibilidade_resultado=None, concentracoes=None):
        ld_resultado = ld_resultado or {}
        sensibilidade_resultado = sensibilidade_resultado or {}
        concentracoes = concentracoes or {}
        dados = {}

        def adicionar_chave(nome_amostra, elemento, energia=""):
            dados.setdefault(nome_amostra, {}).setdefault((elemento, energia), {})

        for bloco in concentracoes.values():
            if not isinstance(bloco, dict):
                continue
            for nome_amostra, elementos in bloco.items():
                for chave in (elementos or {}):
                    if isinstance(chave, tuple):
                        adicionar_chave(nome_amostra, chave[0], chave[1])
                    else:
                        adicionar_chave(nome_amostra, chave)

        for nome_amostra, elementos in ld_resultado.items():
            for elemento in (elementos or {}):
                chaves = [chave for chave in dados.get(nome_amostra, {}) if chave[0] == elemento]
                if not chaves:
                    adicionar_chave(nome_amostra, elemento)
                    chaves = [(elemento, "")]
                for chave in chaves:
                    dados[nome_amostra][chave]["LD"] = elementos[elemento]

        for nome_amostra, elementos in sensibilidade_resultado.items():
            for chave, valor in (elementos or {}).items():
                if isinstance(chave, tuple):
                    elemento, energia = chave
                else:
                    elemento, energia = chave, ""
                adicionar_chave(nome_amostra, elemento, energia)
                dados[nome_amostra][(elemento, energia)]["Sensibilidade"] = valor

        linhas = []
        for nome_amostra in sorted(dados):
            itens_ordenados = sorted(
                dados[nome_amostra].items(),
                key=lambda item: (
                    z_do_elemento(item[0][0]),
                    AbaSLDModel._chave_energia(item[0][1]),
                ),
            )
            for (elemento, energia), valores in itens_ordenados:
                if not any(AbaSLDModel._tem_valor(valores.get(v)) for v in self.VALORES):
                    continue  # sem LD nem sensibilidade: não aparece na aba
                linhas.append(
                    {
                        "Amostra": nome_amostra,
                        "Elemento": elemento,
                        "Energia (keV)": energia,
                        "LD": valores.get("LD", "-"),
                        "Sensibilidade": valores.get("Sensibilidade", "-"),
                    }
                )

        return pd.DataFrame(linhas, columns=self.COLUNAS)

    @staticmethod
    def coluna_do_padrao(valor, nome_padrao):
        return f"{valor} - {nome_padrao}"

    def montar_varios(self, resultados):
        """
        resultados: lista de (nome_padrao, ld_resultado, sensibilidade_resultado, concentracoes).
        Devolve uma tabela só: Amostra/Elemento/Energia uma vez por linha e, para cada padrão,
        as colunas coluna_do_padrao("LD", nome) e coluna_do_padrao("Sensibilidade", nome).
        """
        linhas = {}
        colunas = list(self.CHAVES)
        for nome_padrao, ld_resultado, sensibilidade_resultado, concentracoes in resultados:
            df = self.montar(ld_resultado, sensibilidade_resultado, concentracoes)
            nomes_colunas = [self.coluna_do_padrao(valor, nome_padrao) for valor in self.VALORES]
            colunas += nomes_colunas
            for registro in df.to_dict("records"):
                chave = tuple(registro[c] for c in self.CHAVES)
                linha = linhas.setdefault(chave, dict(zip(self.CHAVES, chave)))
                for valor, coluna in zip(self.VALORES, nomes_colunas):
                    linha[coluna] = registro[valor]

        ordenadas = sorted(
            linhas,
            key=lambda chave: (chave[0], z_do_elemento(chave[1]), AbaSLDModel._chave_energia(chave[2])),
        )
        return pd.DataFrame([linhas[chave] for chave in ordenadas], columns=colunas)
