import pandas as pd
from models.elementosQuimicos import z_do_elemento


class AbaSLDModel:
    """Monta a aba com LD e sensibilidade por amostra e elemento."""

    COLUNAS = ["Amostra", "Elemento", "Energia (keV)", "LD", "Sensibilidade"]

    @staticmethod
    def _chave_energia(energia):
        try:
            return 0, float(energia)
        except (TypeError, ValueError):
            return 1, str(energia)

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