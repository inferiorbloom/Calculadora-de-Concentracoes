import math

import numpy as np
import pandas as pd

REGUA_GROSSA = 2  # topo e fim da tabela
REGUA_FINA = 1  # abaixo do cabeçalho, sob os títulos mesclados e na coluna de rótulos


class EstiloTabela:
    """
    Escreve tabelas no estilo de artigo científico (booktabs): tudo centralizado e sem grade.
    Só há régua no topo da tabela, abaixo do cabeçalho e no fim, uma régua fina sob os títulos
    que agrupam colunas (ex.: o nome do elemento sobre C e Erro) e uma linha vertical separando
    as colunas de rótulo (Amostra, Nome...) dos valores.
    Um EstiloTabela por arquivo: os formatos ficam guardados no workbook.
    """

    LARGURA_MIN = 8
    LARGURA_MAX = 45

    def __init__(self, workbook):
        self.workbook = workbook
        self._formatos = {}
        self._larguras = {}  # (aba, coluna) -> maior largura pedida até agora

    def formato(self, cima=0, baixo=0, direita=0, negrito=False, num_format=None):
        chave = (cima, baixo, direita, negrito, num_format)
        if chave not in self._formatos:
            propriedades = {"align": "center", "valign": "vcenter"}
            if cima:
                propriedades["top"] = cima
            if baixo:
                propriedades["bottom"] = baixo
            if direita:
                propriedades["right"] = direita
            if negrito:
                propriedades["bold"] = True
            if num_format:
                propriedades["num_format"] = num_format
            self._formatos[chave] = self.workbook.add_format(propriedades)
        return self._formatos[chave]

    @staticmethod
    def _valor(valor, na_rep):
        """Valor pronto para a célula: vazio/NaN viram na_rep, tipos do numpy viram tipos do Python."""
        if isinstance(valor, np.generic):
            valor = valor.item()
        if valor is None or (isinstance(valor, float) and math.isnan(valor)):
            return na_rep
        if isinstance(valor, float) and math.isinf(valor):
            return str(valor)
        if isinstance(valor, (tuple, list)):
            return " ".join(str(v) for v in valor)
        try:
            if pd.isna(valor):
                return na_rep
        except (TypeError, ValueError):
            pass
        return valor

    @staticmethod
    def _celula(worksheet, linha, coluna, valor, formato):
        if valor is None or valor == "":
            worksheet.write_blank(linha, coluna, None, formato)
        elif isinstance(valor, bool):
            worksheet.write_boolean(linha, coluna, valor, formato)
        elif isinstance(valor, (int, float)):
            worksheet.write_number(linha, coluna, valor, formato)
        else:
            worksheet.write_string(linha, coluna, str(valor), formato)

    @staticmethod
    def _largura_texto(valor):
        if isinstance(valor, float):
            return min(len(f"{valor:.10g}"), 12)  # o Excel mostra ~11 algarismos no formato Geral
        return len(str(valor)) if valor is not None else 0

    def escrever(self, worksheet, linha, coluna, cabecalho, corpo, colunas_rotulo=0, mesclas=(),
                 linhas_valor=(), separar_antes=(), formatos_coluna=None, na_rep="-"):
        """
        cabecalho / corpo: listas de linhas (listas de valores), a partir de (linha, coluna).
        colunas_rotulo: quantas colunas do início são rótulos (ganham a linha vertical à direita).
        mesclas: [(linha do cabeçalho, coluna inicial, coluna final)], com o valor na coluna inicial.
        linhas_valor: linhas do cabeçalho que trazem valores (ex.: LD), sem negrito.
        separar_antes: linhas do corpo com uma régua fina em cima (ex.: Média, depois das amostras).
        formatos_coluna: {coluna: formato numérico} para o corpo, ex.: {5: "0.0"}.
        Devolve o número de linhas escritas.
        """
        linhas = [(valores, True) for valores in cabecalho] + [(valores, False) for valores in corpo]
        if not linhas:
            return 0
        formatos_coluna = formatos_coluna or {}
        n_colunas = max(len(valores) for valores, _ in linhas)
        fim_mescla = {(l, c): fim for l, c, fim in mesclas}
        cobertas = {(l, c) for l, inicio, fim in mesclas for c in range(inicio + 1, fim + 1)}
        ultima_cabecalho = len(cabecalho) - 1
        ultima = len(linhas) - 1

        for i, (valores, eh_cabecalho) in enumerate(linhas):
            i_corpo = i - len(cabecalho)
            for c in range(n_colunas):
                if (i, c) in cobertas:
                    continue
                fim = fim_mescla.get((i, c), c)

                cima = REGUA_GROSSA if i == 0 else 0
                if not eh_cabecalho and i_corpo in separar_antes:
                    cima = REGUA_FINA
                baixo = 0
                if i == ultima:
                    baixo = REGUA_GROSSA
                elif i == ultima_cabecalho:
                    baixo = REGUA_FINA
                elif i == 0 and fim > c:
                    baixo = REGUA_FINA  # título que agrupa colunas, como o \cmidrule
                direita = REGUA_FINA if colunas_rotulo and fim == colunas_rotulo - 1 else 0

                formato = self.formato(
                    cima, baixo, direita,
                    negrito=eh_cabecalho and i not in linhas_valor,
                    num_format=None if eh_cabecalho else formatos_coluna.get(c),
                )
                valor = valores[c] if c < len(valores) else None
                valor = self._valor(valor, None if eh_cabecalho else na_rep)

                if fim > c:
                    worksheet.merge_range(linha + i, coluna + c, linha + i, coluna + fim, "", formato)
                    if valor not in (None, ""):
                        self._celula(worksheet, linha + i, coluna + c, valor, formato)
                else:
                    self._celula(worksheet, linha + i, coluna + c, valor, formato)
                    self._ajustar_largura(worksheet, coluna + c, self._largura_texto(valor))

        return len(linhas)

    def escrever_celula(self, worksheet, linha, coluna, valor, negrito=False):
        """Célula solta (fora de tabela), centralizada e sem borda."""
        self._celula(worksheet, linha, coluna, self._valor(valor, None), self.formato(negrito=negrito))

    def _ajustar_largura(self, worksheet, coluna, texto):
        chave = (worksheet.name, coluna)
        largura = max(self.LARGURA_MIN, min(texto + 3, self.LARGURA_MAX))
        if largura > self._larguras.get(chave, 0):
            self._larguras[chave] = largura
            worksheet.set_column(coluna, coluna, largura)
