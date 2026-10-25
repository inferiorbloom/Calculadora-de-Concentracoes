import os
import re
import tkinter
from tkinter import messagebox, ttk

import customtkinter as ctk
import numpy as np
from PIL import Image
from tksheet import Sheet

from models.abaResultadosModel import montar_titulo_coluna
from models.elementosQuimicos import z_do_elemento
from models.fichaInformacaoModel import nome_da_amostra
from models.configModel import carregar_mostrar_menor_ld, salvar_mostrar_menor_ld
from models.leitorArquivoModel import nome_amostra as _nome_arquivo
from models.qualidadeModel import (
    LIMITE_RECUPERACAO,
    TEXTO_MENOR_LD,
    LIMITE_INCERTEZA,
    abaixo_do_ld,
    classificar,
    ld_de_referencia,
    recuperacao,
    recuperacao_fora,
)
from resource_utils import resource_path
from views import tema


def _icone(nome, tamanho=18):
    return ctk.CTkImage(light_image=Image.open(resource_path("imagens", "icones", nome)), size=(tamanho, tamanho))


class ConcentracaoView(ctk.CTkFrame):
    """
    Seções ENTRADA e CÁLCULO do menu do alvo. slot_padroes recebe o botão "Padrões certificados"
    (montado pelo PadraoVM); as SAÍDAS ficam na caixa montada pelo ConcentracaoVM.
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        tema.rotulo_secao(self, "Entrada", fill="x", pady=(4, 6))
        self.selecionar_arquivos = ctk.CTkButton(
            self, text="Selecionar arquivos", image=_icone("pasta.png"), compound="left", anchor="w", height=36,
            **tema.BOTAO_SECUNDARIO,
        )
        self.selecionar_arquivos.pack(pady=(0, 6), fill="x")

        # ficha de informação (.docx) com os nomes das amostras; o lápis edita os nomes sem ficha
        linha_ficha = ctk.CTkFrame(self, fg_color="transparent")
        linha_ficha.pack(pady=(0, 6), fill="x")
        self.editar_nomes = ctk.CTkButton(linha_ficha, text="✎", width=36, height=36, **tema.BOTAO_SECUNDARIO)
        self.editar_nomes.pack(side="right", padx=(6, 0))
        self.ler_ficha = ctk.CTkButton(
            linha_ficha, text="Ficha de informação", image=_icone("file.png"), compound="left", anchor="w",
            height=36, **tema.BOTAO_SECUNDARIO,
        )
        self.ler_ficha.pack(side="left", fill="x", expand=True)
        self.slot_padroes = ctk.CTkFrame(self, fg_color="transparent", height=1)
        self.slot_padroes.pack(fill="x")

        # cálculos extras, feitos junto com o Calcular quando marcados
        tema.rotulo_secao(self, "Cálculo", fill="x", pady=(18, 6))
        self.lista_extras = ctk.CTkFrame(self, fg_color="transparent")
        self.lista_extras.pack(fill="x")

        self.var_z_score = ctk.BooleanVar(value=False)
        self.check_z_score = ctk.CTkCheckBox(
            self.lista_extras, text="Z'-Score", variable=self.var_z_score, checkbox_width=18, checkbox_height=18,
        )
        self.check_z_score.pack(anchor="w", pady=(0, 8))

        # a Sensibilidade precisa do tempo de contagem: fica ao lado, lembrado entre as sessões
        linha_sensibilidade = ctk.CTkFrame(self.lista_extras, fg_color="transparent")
        linha_sensibilidade.pack(fill="x")
        self.var_sensibilidade = ctk.BooleanVar(value=False)
        self.check_sensibilidade = ctk.CTkCheckBox(
            linha_sensibilidade, text="Sensibilidade", variable=self.var_sensibilidade, checkbox_width=18,
            checkbox_height=18,
        )
        self.check_sensibilidade.pack(side="left")
        ctk.CTkLabel(linha_sensibilidade, text="s", text_color=tema.TEXTO_2).pack(side="right", padx=(4, 0))
        self.tempo_contagem = ctk.CTkEntry(linha_sensibilidade, width=56, height=26, placeholder_text="tempo")
        self.tempo_contagem.pack(side="right")

        self.calcular = ctk.CTkButton(
            self,
            text="Calcular   F5",
            state="disabled",
            command=None,
            height=42,
            **tema.BOTAO_PRINCIPAL,
            image=_icone("calcular.png", 18),
            compound="left",
        )
        self.calcular.pack(pady=(14, 6), fill="x")

        # o próximo passo (o que falta para calcular) ou o estado do cálculo
        linha_status = ctk.CTkFrame(self, fg_color="transparent")
        linha_status.pack(fill="x")
        self.bolinha_status = ctk.CTkLabel(linha_status, text="●", font=tema.fonte(11), width=14, anchor="nw")
        self.bolinha_status.pack(side="left", anchor="n", pady=(1, 0))
        self.status = ctk.CTkLabel(
            linha_status, text="", font=tema.fonte(12), text_color=COR_STATUS["info"], wraplength=186,
            justify="left", anchor="w",
        )
        self.status.pack(side="left", fill="x", expand=True, padx=(4, 0))

    def mostrar_status(self, texto, tipo="info"):
        """tipo: "info", "pronto", "feito" ou "atencao" (a cor do texto e da bolinha)."""
        cor = COR_STATUS.get(tipo, COR_STATUS["info"])
        self.status.configure(text=texto, text_color=cor)
        self.bolinha_status.configure(text_color=cor)


COR_STATUS = {"info": tema.APAGADO, "pronto": tema.DESTAQUE, "feito": tema.OK, "atencao": tema.ATENCAO}


def _chave_ordem(chave):
    """Ordena por número atômico e, no mesmo elemento, pela energia."""
    elemento, energia = chave if isinstance(chave, tuple) else (chave, 0)
    try:
        energia = float(energia)
    except (TypeError, ValueError):
        energia = 0.0
    return z_do_elemento(elemento), energia


def _titulo_coluna(chave, unidades, contagem):
    """Elemento + unidade; a energia só aparece quando o elemento se repete (ex.: Ag K e Ag L)."""
    elemento, energia = chave if isinstance(chave, tuple) else (chave, None)
    unidade = (unidades or {}).get(elemento, "")
    possui_duplicata = energia is not None and contagem.get(elemento, 0) > 1
    return montar_titulo_coluna(elemento, energia, unidade, possui_duplicata)


SEPARADOR_ERRO = " ± "
MARCADOR_AMBOS = " ⚠"  # valor ≤ 3×LD e incerteza ≥ 40%; removido no Ctrl+C


def _para_float(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _formatar_numero(valor):
    """
    Sem arredondamento por regra (o Excel também sai sem): só limita a 6 algarismos significativos,
    o que já é mais do que a medida tem. Nunca vira "0.000" por falta de casas.
    """
    numero = _para_float(valor)
    if numero is None:
        return str(valor)
    return np.format_float_positional(numero, precision=6, unique=False, fractional=False, trim="-")


def _formatar_ld(valor):
    if valor in (None, ""):
        return "---"
    return _formatar_numero(valor)


class ConcentracaoResultadoView(ctk.CTkFrame):
    """Resultados em formato de planilha, com uma aba para cada tipo de cálculo."""

    ABA_CONCENTRACOES = "Concentrações"
    ABA_Z_SCORE = "Z'-Score"
    ABA_SENSIBILIDADE = "Sensibilidade"

    COR_FUNDO = tema.SUPERFICIE
    COR_LISTRA = tema.SUPERFICIE_2
    COR_LD = (tema.LD_FUNDO, tema.LD_TEXTO)  # (fundo, texto)
    COR_ABAIXO_LD = (tema.ERRO_FUNDO, tema.ERRO_TEXTO)  # valores <= 3xLD
    COR_INCERTEZA_ALTA = (tema.ATENCAO_FUNDO, tema.ATENCAO)  # erro >= 40% do valor
    COR_AMBOS = (tema.ERRO_FUNDO, tema.AMBOS_TEXTO)  # <= 3xLD e erro >= 40%: fundo vermelho, texto amarelo
    COR_RECUPERACAO = (tema.OK_FUNDO, tema.OK_TEXTO)  # linha de recuperação de um material certificado medido como amostra
    COR_RECUPERACAO_FORA = (tema.ATENCAO_FUNDO, tema.ATENCAO)  # recuperação fora de 100% ± LIMITE_RECUPERACAO

    LIMITE_INCERTEZA = LIMITE_INCERTEZA

    _abertas = []  # todas as tabelas: a opção "< LD" vale para todas ao mesmo tempo

    def __init__(self, master, ao_grafico_sensibilidade=None):
        """ao_grafico_sensibilidade(): botão "Sensibilidade × Z", que aparece com a aba Sensibilidade."""
        super().__init__(master)
        self.ao_grafico_sensibilidade = ao_grafico_sensibilidade
        ConcentracaoResultadoView._abertas.append(self)
        self.bind("<Destroy>", self._ao_destruir, add="+")

        # a legenda vai primeiro (embaixo) para não ser empurrada para fora pelas abas
        self._criar_legenda()

        # seletor de abas: só aparece quando houver mais de uma tabela
        self.barra_abas = ctk.CTkFrame(self, fg_color="transparent")
        self.seletor = ctk.CTkSegmentedButton(self.barra_abas, values=[], command=self._mostrar_aba)
        self.seletor.pack(side="left", expand=True)
        self.botao_grafico_sensibilidade = ctk.CTkButton(
            self.barra_abas, text="Gráfico: sensibilidade × Z", width=180, height=26, font=tema.fonte(12),
            command=lambda: self.ao_grafico_sensibilidade and self.ao_grafico_sensibilidade(),
        )

        self.area = ctk.CTkFrame(self, fg_color=self.COR_FUNDO)
        self.area.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.area.grid_rowconfigure(0, weight=1)
        self.area.grid_columnconfigure(0, weight=1)

        self.abas = {}
        self.tabelas = {}
        self._criar_aba(self.ABA_CONCENTRACOES)

        # nomes das amostras ({código: nome}) e os últimos dados mostrados, para redesenhar quando os nomes mudam
        self.nomes = {}
        self.certificados = {}  # {arquivo padrão: padrão certificado}, para a recuperação
        self._dados_concentracoes = None
        self._dados_sensibilidade = None

    def _ao_destruir(self, evento):
        if evento.widget is self and self in ConcentracaoResultadoView._abertas:
            ConcentracaoResultadoView._abertas.remove(self)

    def _criar_legenda(self):
        # 2ª linha (embaixo): recuperação, a opção "< LD" e a dica do Ctrl+C
        linha2 = ctk.CTkFrame(self, fg_color="transparent")
        linha2.pack(side="bottom", fill="x", padx=15, pady=(0, 5))
        ctk.CTkLabel(
            linha2, text="", width=14, height=14, corner_radius=3, fg_color=self.COR_RECUPERACAO[0],
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            linha2, text="Recuperação (%)", font=tema.fonte(12), text_color=self.COR_RECUPERACAO[1],
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            linha2, text=f"fora de 100 ± {LIMITE_RECUPERACAO * 100:.0f}%", font=tema.fonte(12),
            text_color=self.COR_RECUPERACAO_FORA[1],
        ).pack(side="left", padx=(0, 18))
        self.var_menor_ld = ctk.BooleanVar(master=self, value=carregar_mostrar_menor_ld())
        ctk.CTkCheckBox(
            linha2, text="Mostrar \"< LD\" abaixo do LD (vale também no Excel)",
            variable=self.var_menor_ld, command=self._trocar_menor_ld, font=tema.fonte(12),
            checkbox_width=18, checkbox_height=18,
        ).pack(side="left", padx=(0, 18))

        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(side="bottom", fill="x", padx=15, pady=(0, 2))

        itens = [
            (self.COR_LD, "LD (limite de detecção)"),
            (self.COR_ABAIXO_LD, "Valor ≤ 3×LD"),
            (self.COR_INCERTEZA_ALTA, f"Incerteza ≥ {self.LIMITE_INCERTEZA:.0%} do valor"),
        ]
        for (fundo, texto_cor), texto in itens:
            ctk.CTkLabel(
                legenda, text="", width=14, height=14, corner_radius=3, fg_color=fundo,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(legenda, text=texto, font=tema.fonte(12), text_color=texto_cor).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(
            legenda, text=MARCADOR_AMBOS.strip(), font=tema.fonte(13, "bold"), text_color=self.COR_AMBOS[1],
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            legenda, text=f"≤ 3×LD e incerteza ≥ {self.LIMITE_INCERTEZA:.0%}",
            font=tema.fonte(12), text_color=self.COR_AMBOS[1],
        ).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(
            linha2,
            text="Ctrl+C copia para o Excel",
            font=tema.fonte(11),
            text_color=tema.APAGADO,
        ).pack(side="right")

    def _criar_aba(self, nome):
        aba = ctk.CTkFrame(self.area, fg_color="transparent")
        aba.grid(row=0, column=0, sticky="nsew")

        # as barras de rolagem do tksheet são ttk; no Windows só aceitam cores no tema "clam"
        ttk.Style(self).theme_use("clam")

        tabela = Sheet(
            aba,
            theme="dark blue",
            show_row_index=False,
            show_top_left=False,
            font=tema.fonte(12),
            header_font=tema.fonte(12, "bold"),
            default_row_height=26,
            default_header_height=28,
            outline_thickness=0,
            table_bg=self.COR_FUNDO,
            table_fg=tema.TEXTO,
            table_grid_fg=tema.BORDA_SUAVE,
            header_bg=tema.MARINHO,
            header_fg=tema.TEXTO,
            header_grid_fg=tema.BORDA_SUAVE,
            frame_bg=self.COR_FUNDO,
            vertical_scroll_troughcolor=self.COR_FUNDO,
            horizontal_scroll_troughcolor=self.COR_FUNDO,
            vertical_scroll_bordercolor=self.COR_FUNDO,
            horizontal_scroll_bordercolor=self.COR_FUNDO,
        )
        tabela.enable_bindings(
            "single_select", "drag_select", "ctrl_select", "select_all",
            "row_select", "column_select", "column_width_resize", "double_click_column_resize",
            "arrowkeys", "right_click_popup_menu", "rc_select",
        )
        tabela.popup_menu_add_command("Copiar (Ctrl+C)", lambda: self._copiar(tabela))
        tabela.bind("<Control-c>", lambda _e: self._copiar(tabela))
        tabela.bind("<Control-C>", lambda _e: self._copiar(tabela))
        tabela.pack(fill="both", expand=True)

        self.abas[nome] = aba
        self.tabelas[nome] = tabela
        self._atualizar_seletor()
        return tabela

    def _aba(self, nome):
        """Retorna a tabela da aba, criando a aba se ainda não existir."""
        return self.tabelas.get(nome) or self._criar_aba(nome)

    def _remover_aba(self, nome):
        if nome in self.abas:
            self.abas.pop(nome).destroy()
            del self.tabelas[nome]
            self._atualizar_seletor()

    def _atualizar_seletor(self):
        if len(self.abas) > 1:
            self.seletor.configure(values=list(self.abas))
            if not self.barra_abas.winfo_manager():
                self.barra_abas.pack(before=self.area, fill="x", padx=10, pady=(5, 0))
        else:
            self.barra_abas.pack_forget()
        if self.ABA_SENSIBILIDADE in self.abas and self.ao_grafico_sensibilidade:
            self.botao_grafico_sensibilidade.pack(side="right")
        else:
            self.botao_grafico_sensibilidade.pack_forget()

    def _mostrar_aba(self, nome):
        self.abas[nome].tkraise()
        self.seletor.set(nome)

    def _trocar_menor_ld(self):
        """A opção vale para todas as tabelas abertas (e para o Excel): redesenha cada uma com ela."""
        mostrar = self.var_menor_ld.get()
        salvar_mostrar_menor_ld(mostrar)
        for view in list(ConcentracaoResultadoView._abertas):
            if view is not self:
                view.var_menor_ld.set(mostrar)
            if view._dados_concentracoes is not None:
                view._preencher_concentracoes(*view._dados_concentracoes)

    def _preencher(self, tabela, colunas, linhas, celulas_destacadas=None, colunas_texto=1):
        """
        linhas: lista de (valores, tag); tag "ld" destaca a linha, None usa a cor alternada.
        celulas_destacadas: {(linha, coluna): (fundo, texto)}.
        colunas_texto: quantas colunas do início ficam alinhadas à esquerda (Amostra, Nome).
        """
        dados = [[str(v) for v in valores] for valores, _ in linhas]
        larguras = [170]
        for c in range(1, len(colunas)):
            maior = max([len(str(colunas[c])) + 1] + [len(linha[c]) for linha in dados if c < len(linha)])
            larguras.append(max(90, 10 * maior + 24))

        tabela.dehighlight_all(redraw=False)
        tabela.headers([str(c) for c in colunas], redraw=False)
        tabela.set_sheet_data(dados, redraw=False)
        tabela.set_column_widths(larguras)
        tabela.table_align("center", redraw=False)
        tabela.header_align("center", redraw=False)
        for letra in "AB"[:colunas_texto]:
            tabela.align(letra, align="w", redraw=False)

        listradas = 0
        for indice, (_, tag) in enumerate(linhas):
            if tag == "ld":
                tabela.highlight_rows(indice, bg=self.COR_LD[0], fg=self.COR_LD[1], redraw=False)
                continue
            if tag == "recuperacao":
                tabela.highlight_rows(indice, bg=self.COR_RECUPERACAO[0], fg=self.COR_RECUPERACAO[1], redraw=False)
                continue
            if listradas % 2 == 1:
                tabela.highlight_rows(indice, bg=self.COR_LISTRA, redraw=False)
            listradas += 1

        for (linha, coluna), (fundo, texto) in (celulas_destacadas or {}).items():
            tabela.highlight_cells(linha, coluna, bg=fundo, fg=texto, redraw=False)

        tabela.redraw()

    def _copiar(self, tabela):
        """
        Copia as células selecionadas como texto separado por tabulação, com vírgula decimal (Excel pt-BR).
        Colunas "C ± Erro" viram duas colunas (C e Erro), para colarem como números.
        """

        def celula(texto):
            return texto.replace(".", ",") if _para_float(texto) is not None else texto

        dados = tabela.get_sheet_data()
        cabecalho = tabela.headers()
        selecionadas = tabela.get_selected_cells(get_rows=True, get_columns=True)
        if selecionadas:
            linhas = sorted({r for r, _ in selecionadas})
            colunas = sorted({c for _, c in selecionadas})
        else:
            linhas = range(len(dados))
            colunas = range(len(cabecalho))

        com_erro = {c for c in colunas if any(SEPARADOR_ERRO in str(dados[r][c]) for r in linhas)}

        titulos = []
        for c in colunas:
            titulos += [str(cabecalho[c]), "Erro"] if c in com_erro else [str(cabecalho[c])]
        texto = ["\t".join(titulos)]

        for r in linhas:
            partes = []
            for c in colunas:
                valor = str(dados[r][c]).replace(MARCADOR_AMBOS, "")
                if c in com_erro:
                    c_valor, _, erro = valor.partition(SEPARADOR_ERRO)
                    partes += [celula(c_valor.strip()), celula(erro.strip())]
                else:
                    partes.append(celula(valor))
            texto.append("\t".join(partes))
        self.clipboard_clear()
        self.clipboard_append("\n".join(texto))
        return "break"

    def _com_nome(self, amostras):
        """A coluna Nome só aparece quando alguma das amostras tem nome."""
        return any(nome_da_amostra(self.nomes, a) for a in amostras if a)

    def mostrar_nomes(self, nomes):
        """Nomes das amostras mudaram: redesenha as tabelas que têm amostras, sem trocar a aba aberta."""
        self.nomes = dict(nomes or {})
        if self._dados_concentracoes is not None:
            self._preencher_concentracoes(*self._dados_concentracoes)
        if self._dados_sensibilidade is not None and self.ABA_SENSIBILIDADE in self.tabelas:
            self._preencher_sensibilidade(self._dados_sensibilidade)

    # mostrar resultados como planilha
    def mostrar_resultados(
        self, concentracoes, ld_resultado=None, unidades=None, nome_padrao=None, erros=None, padrao_certificado=None,
        certificados=None,
    ):
        """
        erros: mesma estrutura de concentracoes, com o erro propagado de cada valor.
        padrao_certificado: {"nome": ..., "elementos": {...}}; mostrado na linha do padrão quando ele não é amostra.
        certificados: {arquivo: padrão certificado} dos arquivos marcados como Padrão. Um deles medido como
        amostra (que não seja o padrão desta tabela) ganha, logo abaixo, a linha de recuperação.
        """
        self.certificados = dict(certificados or {})
        # resultados anteriores de Z'-Score e Sensibilidade não valem mais
        self._remover_aba(self.ABA_Z_SCORE)
        self._remover_aba(self.ABA_SENSIBILIDADE)
        self._dados_sensibilidade = None

        self._dados_concentracoes = (concentracoes, ld_resultado, unidades, nome_padrao, erros, padrao_certificado)
        self._preencher_concentracoes(*self._dados_concentracoes)
        self._mostrar_aba(self.ABA_CONCENTRACOES)

    def _preencher_concentracoes(self, concentracoes, ld_resultado, unidades, nome_padrao, erros, padrao_certificado):
        """Os argumentos de mostrar_resultados (guardados em _dados_concentracoes para redesenhar)."""
        ld_resultado = ld_resultado or {}
        erros = erros or {}

        # Junta todos os elementos presentes em qualquer amostra, em ordem de número atômico
        todos_elementos = set()
        for conc_amostra in concentracoes.values():
            for elementos in conc_amostra.values():
                todos_elementos.update(elementos.keys())
        todos_elementos = sorted(todos_elementos, key=_chave_ordem)
        simbolos = [chave[0] if isinstance(chave, tuple) else chave for chave in todos_elementos]
        contagem = {s: simbolos.count(s) for s in simbolos}

        amostras = []  # (nome, concentrações, erros)
        for bloco, conc_amostra in concentracoes.items():
            erros_bloco = erros.get(bloco, {})
            for nome, elementos in conc_amostra.items():
                amostras.append((nome, elementos, erros_bloco.get(nome, {})))
        nomes_amostras = [nome for nome, _, _ in amostras]
        com_nome = self._com_nome(nomes_amostras + [nome_padrao])
        primeira = 2 if com_nome else 1  # coluna do primeiro elemento
        menor_ld = self.var_menor_ld.get()

        def inicio(rotulo, amostra=None):
            """Primeiras células da linha: o rótulo e, se houver a coluna, o nome da amostra."""
            return [rotulo, nome_da_amostra(self.nomes, amostra) if amostra else ""] if com_nome else [rotulo]

        def texto_celula(valor, erro):
            """'C ± Erro'; sem erro, só o valor."""
            if valor in (None, ""):
                return "---"
            if _para_float(erro) is None:
                return _formatar_numero(valor)
            return f"{_formatar_numero(valor)}{SEPARADOR_ERRO}{_formatar_numero(erro)}"

        # 1ª linha: só o LD do padrão usado nesta aba
        linhas = []
        ld_padrao = ld_resultado.get(nome_padrao)
        if ld_padrao:
            linhas.append((inicio(f"LD - {nome_padrao}") + [_formatar_ld(ld_padrao.get(s)) for s in simbolos], "ld"))

        # 2ª linha: o próprio padrão. Se ele também for amostra, sobe para cá; senão, mostra os valores certificados
        rotulo_padrao = f"{nome_padrao} (Pd)"
        if nome_padrao in nomes_amostras:
            amostras.sort(key=lambda amostra: amostra[0] != nome_padrao)
        elif nome_padrao:
            certificados = (padrao_certificado or {}).get("elementos", {})

            def texto_certificado(simbolo):
                info = certificados.get(simbolo)
                if not info:
                    return "---"
                valor, erro = info.get("valor_str", info.get("valor")), info.get("erro_str", info.get("erro"))
                return f"{valor}{SEPARADOR_ERRO}{erro}" if erro not in (None, "") else str(valor)

            linhas.append((inicio(rotulo_padrao, nome_padrao) + [texto_certificado(s) for s in simbolos], None))

        destacadas = {}
        for nome_amostra, elementos, erros_amostra in amostras:
            indice_linha = len(linhas)
            celulas = inicio(rotulo_padrao if nome_amostra == nome_padrao else nome_amostra, nome_amostra)

            for coluna, (chave, simbolo) in enumerate(zip(todos_elementos, simbolos), start=primeira):
                texto = texto_celula(elementos.get(chave), erros_amostra.get(chave))
                valor = _para_float(elementos.get(chave))
                erro = _para_float(erros_amostra.get(chave))
                ld = ld_de_referencia(ld_resultado, nome_amostra, simbolo, nome_padrao)
                if menor_ld and abaixo_do_ld(valor, ld):
                    texto = TEXTO_MENOR_LD

                destaque = classificar(valor, erro, ld)

                # vermelho (≤ 3×LD) tem prioridade; com incerteza alta também, ganha o marcador
                if destaque == "ambos":
                    destacadas[(indice_linha, coluna)] = self.COR_AMBOS
                    if texto != TEXTO_MENOR_LD:
                        texto += MARCADOR_AMBOS
                elif destaque == "abaixo_ld":
                    destacadas[(indice_linha, coluna)] = self.COR_ABAIXO_LD
                elif destaque == "incerteza":
                    destacadas[(indice_linha, coluna)] = self.COR_INCERTEZA_ALTA

                celulas.append(texto)

            linhas.append((celulas, None))

            # material certificado medido como amostra: medido / certificado, elemento a elemento
            certificado = self.certificados.get(nome_amostra) if nome_amostra != nome_padrao else None
            if certificado:
                indice_linha = len(linhas)
                celulas = inicio(f"  ↳ Recuperação (%) · {certificado.get('nome', '')}")
                for coluna, (chave, simbolo) in enumerate(zip(todos_elementos, simbolos), start=primeira):
                    percentual = recuperacao(
                        elementos.get(chave), (unidades or {}).get(simbolo), certificado.get("elementos", {}).get(simbolo)
                    )
                    celulas.append("---" if percentual is None else f"{percentual:.1f}%")
                    if recuperacao_fora(percentual):
                        destacadas[(indice_linha, coluna)] = self.COR_RECUPERACAO_FORA
                linhas.append((celulas, "recuperacao"))

        colunas = (["Amostra", "Nome"] if com_nome else ["Amostra"]) + [
            _titulo_coluna(e, unidades, contagem) for e in todos_elementos
        ]
        self._preencher(self.tabelas[self.ABA_CONCENTRACOES], colunas, linhas, destacadas, colunas_texto=primeira)

    def mostrar_z_score(self, resultados):
        if not resultados:
            return

        linhas = []
        for chave, dados in sorted(resultados.items(), key=lambda item: _chave_ordem(item[0])):
            elemento = chave[0] if isinstance(chave, tuple) else chave
            valores = [
                elemento,
                dados["n"],
                f"{dados['media_amostras']:.6g}",
                f"{dados['desvio_padrao_amostras']:.6g}",
                f"{dados['valor_certificado']:.6g} +/- {dados['erro_certificado']:.6g}",
                "--" if dados["z_score"] is None else f"{dados['z_score']:.6g}",
            ]
            linhas.append((valores, None))

        colunas = ["Elemento", "n", "Média", "Desvio padrão", "Certificado", "Z'-Score"]
        self._preencher(self._aba(self.ABA_Z_SCORE), colunas, linhas)
        self._mostrar_aba(self.ABA_Z_SCORE)

    def mostrar_sensibilidade(self, resultados):
        if not resultados:
            return
        self._dados_sensibilidade = resultados
        self._preencher_sensibilidade(resultados)
        self._mostrar_aba(self.ABA_SENSIBILIDADE)

    def _preencher_sensibilidade(self, resultados):
        com_nome = self._com_nome(resultados)
        linhas = []
        for nome_amostra, elementos in resultados.items():
            inicio = [nome_amostra, nome_da_amostra(self.nomes, nome_amostra)] if com_nome else [nome_amostra]
            for chave, valor in sorted(elementos.items(), key=lambda item: _chave_ordem(item[0])):
                elemento, energia = chave
                linhas.append((inicio + [elemento, f"{energia:.3f}", f"{valor:.6g}"], None))

        colunas = (["Amostra", "Nome"] if com_nome else ["Amostra"]) + ["Elemento", "Energia (keV)", "Sensibilidade"]
        self._preencher(self._aba(self.ABA_SENSIBILIDADE), colunas, linhas, colunas_texto=2 if com_nome else 1)


class BarraAvisosView(ctk.CTkFrame):
    """
    Acima dos resultados: a faixa de "resultados desatualizados" (a seleção mudou depois do Calcular)
    e o botão com os avisos do último cálculo, para consultar depois que o pop-up fechou.
    """

    COR_FAIXA = (tema.ATENCAO_FUNDO, tema.ATENCAO)  # (fundo, texto)

    def __init__(self, master, antes=None):
        """antes: o widget que fica logo abaixo da barra (os resultados)."""
        super().__init__(master, fg_color="transparent", height=10)
        self.antes = antes
        self.avisos = []  # [(origem, texto)]

        self.faixa = ctk.CTkLabel(
            self, text="", font=tema.fonte(12, "bold"), fg_color=self.COR_FAIXA[0], text_color=self.COR_FAIXA[1],
            corner_radius=6, anchor="w", height=28,
        )
        self.botao_avisos = ctk.CTkButton(
            self, text="", width=110, height=28, font=tema.fonte(12), fg_color=tema.BORDA_SUAVE, hover_color=tema.CONTROLE_HOVER,
            command=self._abrir_avisos,
        )
        self._atualizar()

    def mostrar_desatualizado(self, texto):
        """texto vazio esconde a faixa."""
        self.faixa.configure(text=f"  ⚠  {texto}" if texto else "")
        self._atualizar()

    def definir_avisos(self, avisos):
        """avisos: [(origem, texto)], substituindo os anteriores (cada cálculo tem os seus)."""
        self.avisos = list(avisos)
        self._atualizar()

    def _atualizar(self):
        for widget in (self.faixa, self.botao_avisos):
            widget.pack_forget()
        if self.avisos:
            n = len(self.avisos)
            self.botao_avisos.configure(text=f"⚠ {n} aviso" if n == 1 else f"⚠ {n} avisos")
            self.botao_avisos.pack(side="right", padx=(8, 0))
        if self.faixa.cget("text"):
            self.faixa.pack(side="left", fill="x", expand=True)
        if self.avisos or self.faixa.cget("text"):
            opcoes = {"before": self.antes} if self.antes is not None and self.antes.winfo_manager() else {}
            self.pack(side="top", fill="x", padx=10, pady=(8, 0), **opcoes)
        else:
            self.pack_forget()

    def _abrir_avisos(self):
        JanelaAvisos(self, self.avisos)


class JanelaAvisos(ctk.CTkToplevel):
    """Lista dos avisos do último cálculo (os mesmos do pop-up), agrupados pela origem."""

    def __init__(self, master, avisos):
        super().__init__(master)
        tema.aplicar_icone(self)
        self.title("Avisos")
        self.geometry("620x420")
        texto = ctk.CTkTextbox(self, font=tema.fonte(13), wrap="word")
        texto.pack(fill="both", expand=True, padx=12, pady=12)
        origens = []
        for origem, _ in avisos:
            if origem not in origens:
                origens.append(origem)
        for origem in origens:
            texto.insert("end", f"{origem}\n")
            for o, aviso in avisos:
                if o == origem:
                    texto.insert("end", f"  • {aviso}\n\n")
        texto.configure(state="disabled")
        ctk.CTkButton(self, text="Fechar", width=100, command=self.destroy).pack(pady=(0, 12))
        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()


class ResultadosPadroesView(ctk.CTkFrame):
    """
    Um ConcentracaoResultadoView para cada padrão, com um seletor no topo para alternar entre eles.
    Cada padrão tem as suas próprias abas (Concentrações, Z'-Score, Sensibilidade).
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.barra = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.barra, text="Padrão:", font=tema.fonte(14, "bold")).pack(side="left", padx=(10, 8))
        self.seletor = ctk.CTkSegmentedButton(self.barra, values=[], command=self._mostrar_padrao)
        self.seletor.pack(side="left")

        self.views = {}  # rótulo -> ConcentracaoResultadoView
        self.rotulos = {}  # nome do padrão -> rótulo
        self.nomes = {}  # nomes das amostras ({código: nome}), repassados a cada padrão
        self.ativo = None
        self.ao_grafico_sensibilidade = None  # ao_grafico_sensibilidade(nome do padrão), definido pelo VM
        self._criar_views([None])

    def _criar_views(self, rotulos):
        for view in self.views.values():
            view.destroy()
        nomes_por_rotulo = {rotulo: nome for nome, rotulo in self.rotulos.items()}
        self.views = {
            rotulo: ConcentracaoResultadoView(
                self, ao_grafico_sensibilidade=lambda n=nomes_por_rotulo.get(rotulo): self._grafico_sensibilidade(n)
            )
            for rotulo in rotulos
        }

        # o seletor só aparece quando houver mais de um padrão
        if len(rotulos) > 1:
            self.seletor.configure(values=list(rotulos))
            self.barra.pack(side="top", fill="x", pady=(5, 0))
        else:
            self.barra.pack_forget()

        self.ativo = None
        self._mostrar_padrao(rotulos[0])

    def _grafico_sensibilidade(self, nome_padrao):
        if self.ao_grafico_sensibilidade and nome_padrao:
            self.ao_grafico_sensibilidade(nome_padrao)

    def limpar(self):
        """Volta ao estado inicial: uma tabela vazia, sem seletor de padrão."""
        self.rotulos = {}
        self._criar_views([None])

    def _mostrar_padrao(self, rotulo):
        if self.ativo is not None and self.ativo in self.views:
            self.views[self.ativo].pack_forget()
        self.views[rotulo].pack(fill="both", expand=True)
        self.ativo = rotulo
        if len(self.views) > 1:
            self.seletor.set(rotulo)

    def _view(self, resultado_padrao):
        return self.views[self.rotulos[resultado_padrao.nome]]

    def mostrar_resultados(self, resultados_por_padrao):
        self.rotulos = {r.nome: r.rotulo for r in resultados_por_padrao}
        anterior = self.ativo
        self._criar_views([r.rotulo for r in resultados_por_padrao])
        certificados = {_nome_arquivo(r.arquivo_padrao): r.c_padrao for r in resultados_por_padrao if r.c_padrao}

        for r in resultados_por_padrao:
            self._view(r).nomes = self.nomes
            self._view(r).mostrar_resultados(
                r.concentracoes,
                r.resultado_limite,
                r.unidade_padrao,
                _nome_arquivo(r.arquivo_padrao),
                erros=r.erros_concentracao,
                padrao_certificado=r.c_padrao,
                certificados=certificados,
            )

        # recalculando, continua no padrão que estava aberto
        if anterior in self.views:
            self._mostrar_padrao(anterior)

    def mostrar_nomes(self, nomes):
        self.nomes = dict(nomes or {})
        for view in self.views.values():
            view.mostrar_nomes(self.nomes)

    def mostrar_z_score(self, resultados_por_padrao):
        for r in resultados_por_padrao:
            self._view(r).mostrar_z_score(r.z_score_resultado)

    def mostrar_sensibilidade(self, resultados_por_padrao):
        for r in resultados_por_padrao:
            self._view(r).mostrar_sensibilidade(r.sensibilidade_resultado)


def chave_natural(texto):
    """Ordem "de gente": F2 antes de F10 e 290426ab antes de 290426ac, sem diferenciar maiúsculas."""
    return [int(parte) if parte.isdigit() else parte.lower() for parte in re.split(r"(\d+)", str(texto))]


class ListaArquivosView(ctk.CTkScrollableFrame):
    """Lista dos arquivos selecionados, onde o usuário marca os Padrões (com o padrão certificado) e as Amostras."""

    MAX_PADROES = 2
    SEM_PADRAO = "Nenhum padrão cadastrado"

    def __init__(self, master, ao_alterar=None, ao_escolher_pdf=None, nomes_padroes=None, sugerir_certificado=None,
                 ao_vincular_pdfs=None, ao_soltar=None):
        """
        sugerir_certificado(caminho, usados): certificado para um arquivo recém-marcado como Padrão, ou None.
        ao_vincular_pdfs(): botão "Vincular PDFs" do cabeçalho. ao_soltar(caminhos): arquivos arrastados para a lista.
        """
        super().__init__(master, fg_color=tema.SUPERFICIE, height=200)
        self.ao_alterar = ao_alterar
        self.ao_escolher_pdf = ao_escolher_pdf
        self.sugerir_certificado = sugerir_certificado
        self.ao_vincular_pdfs = ao_vincular_pdfs
        self.ao_soltar = ao_soltar
        self.nomes_padroes = list(nomes_padroes or [])
        self.linhas = []  # (caminho, var_padrao, var_amostra)
        self.pdfs = {}  # índice da linha -> caminho do FullReport (.pdf) para o LD
        self.botoes_pdf = {}  # índice da linha -> (botão escolher, botão remover)
        self.combos_padrao = {}  # índice da linha -> combobox do padrão certificado
        self.labels_nome = {}  # índice da linha -> label com o nome da amostra (ficha de informação)
        self.nomes = {}  # {código: nome} mostrados na coluna Nome
        self.ordem = None  # ("arquivo" ou "nome", decrescente) da última ordenação pelo cabeçalho
        self.grid_columnconfigure(6, weight=1)  # coluna vazia: mantém o LD colado no nome do arquivo
        self.mostrar_vazio()

    def limpar(self):
        for w in self.winfo_children():
            w.destroy()
        self.linhas = []
        self.pdfs = {}
        self.botoes_pdf = {}
        self.combos_padrao = {}
        self.labels_nome = {}

    def _voltar_ao_topo(self):
        """
        Com uma lista menor que a anterior, a rolagem ficava parada lá embaixo; como a lista nova
        cabe na tela, o CTkScrollableFrame desliga a rolagem e não dava mais para subir.
        """
        self.update_idletasks()
        self._parent_canvas.yview_moveto(0)

    def mostrar_vazio(self):
        self.limpar()
        ctk.CTkLabel(
            self, text="Nenhum arquivo selecionado. Use \"Selecionar Arquivos\" no Menu (Ctrl+O) "
                       "ou arraste os arquivos .txt para cá.", font=tema.fonte(14)
        ).grid(row=0, column=0, columnspan=6, padx=10, pady=10, sticky="w")
        self._voltar_ao_topo()
        self._registrar_soltar()

    def carregar(self, caminhos, nomes=None, ordem=None):
        """
        nomes: {código: nome} da ficha de informação, mostrados ao lado do arquivo.
        ordem: a ordenação que os caminhos já seguem (para a setinha do cabeçalho), ou None.
        """
        self.limpar()
        self.ordem = ordem

        # cabeçalho; "Arquivo" e "Nome" ordenam a lista ao clicar (de novo, inverte)
        colunas = ["Padrão", "Amostra", "Arquivo", "Nome", "Padrão Certificado"]
        ordenaveis = {"Arquivo": "arquivo", "Nome": "nome"}
        for col, texto in enumerate(colunas):
            chave = ordenaveis.get(texto)
            if chave and ordem and ordem[0] == chave:
                texto += " ▼" if ordem[1] else " ▲"
            rotulo = ctk.CTkLabel(self, text=texto, font=tema.fonte(13, "bold"))
            rotulo.grid(row=0, column=col, padx=10, pady=(5, 5), sticky="w")
            if chave:
                rotulo.configure(cursor="hand2")
                rotulo.bind("<Button-1>", lambda _e, c=chave: self.ordenar(c))
        # LD: o vínculo continua por linha; o botão só procura de uma vez os PDFs com o mesmo nome do .txt
        cabecalho_ld = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho_ld.grid(row=0, column=5, padx=10, pady=(5, 5), sticky="w")
        ctk.CTkLabel(cabecalho_ld, text="Limite de Detecção", font=tema.fonte(13, "bold")).pack(side="left")
        ctk.CTkButton(
            cabecalho_ld, text="Vincular PDFs", width=96, height=22, font=tema.fonte(11),
            fg_color=tema.CONTROLE, hover_color=tema.BORDA, command=self._vincular_pdfs,
        ).pack(side="left", padx=(10, 0))

        for indice, caminho in enumerate(caminhos):
            var_padrao = ctk.BooleanVar(value=False)
            var_amostra = ctk.BooleanVar(value=True)

            ctk.CTkCheckBox(
                self, text="", width=24, variable=var_padrao, command=lambda i=indice: self._marcar_padrao(i)
            ).grid(row=indice + 1, column=0, padx=(22, 10), pady=3)

            ctk.CTkCheckBox(
                self, text="", width=24, variable=var_amostra, command=self._notificar
            ).grid(row=indice + 1, column=1, padx=(26, 10), pady=3)

            ctk.CTkLabel(self, text=os.path.basename(caminho), font=tema.fonte(14)).grid(
                row=indice + 1, column=2, padx=10, pady=3, sticky="w"
            )

            label_nome = ctk.CTkLabel(self, text="", font=tema.fonte(13), text_color=tema.TEXTO_2)
            label_nome.grid(row=indice + 1, column=3, padx=10, pady=3, sticky="w")
            self.labels_nome[indice] = label_nome

            # padrão certificado: só aparece quando a linha estiver marcada como Padrão
            combo_padrao = ctk.CTkComboBox(
                self,
                width=220,
                height=26,
                state="readonly",
                values=self.nomes_padroes or [self.SEM_PADRAO],
                font=tema.fonte(12),
                button_color=tema.BORDA,
                border_color=tema.BORDA,
                fg_color=tema.CONTROLE,
                command=lambda _escolha: self._notificar(),
            )
            combo_padrao.grid(row=indice + 1, column=4, padx=10, pady=3, sticky="w")
            combo_padrao.grid_remove()
            self.combos_padrao[indice] = combo_padrao

            celula_ld = ctk.CTkFrame(self, fg_color="transparent")
            celula_ld.grid(row=indice + 1, column=5, padx=10, pady=3, sticky="w")

            botao_pdf = ctk.CTkButton(
                celula_ld, width=170, height=26, font=tema.fonte(12),
                command=lambda i=indice: self._escolher_pdf(i),
            )
            botao_pdf.pack(side="left")

            botao_remover = ctk.CTkButton(
                celula_ld, text="✕", width=26, height=26, fg_color=tema.ERRO_FUNDO, hover_color=tema.ERRO_HOVER,
                command=lambda i=indice: self.definir_pdf(i, None),
            )

            self.botoes_pdf[indice] = (botao_pdf, botao_remover)
            self.linhas.append((caminho, var_padrao, var_amostra))
            self.definir_pdf(indice, None, notificar=False)

        self.mostrar_nomes(nomes)
        self._voltar_ao_topo()
        self._registrar_soltar()

    def _vincular_pdfs(self):
        if self.ao_vincular_pdfs:
            self.ao_vincular_pdfs()

    def _registrar_soltar(self):
        """
        Arrastar e soltar (tkinterdnd2): a lista inteira, com tudo o que está dentro, aceita arquivos.
        Sem a biblioteca carregada na janela principal, não faz nada.
        """
        if not self.ao_soltar:
            return

        def registrar(widget):
            try:
                widget.drop_target_register("DND_Files")
                widget.dnd_bind("<<Drop>>", self._soltou)
            except (AttributeError, tkinter.TclError):
                return False
            for filho in widget.winfo_children():
                registrar(filho)
            return True

        registrar(self._parent_frame)

    def _soltou(self, evento):
        caminhos = [str(c) for c in self.tk.splitlist(evento.data)]
        if caminhos:
            self.after(10, lambda: self.ao_soltar(caminhos))  # fora do callback do tkdnd
        return evento.action

    def estado(self):
        """[{arquivo, padrao, amostra, certificado, pdf}] de cada linha, na ordem (para salvar a análise)."""
        return [
            {
                "arquivo": caminho,
                "padrao": var_padrao.get(),
                "amostra": var_amostra.get(),
                "certificado": self.combos_padrao[indice].get() if var_padrao.get() else "",
                "pdf": self.pdfs.get(indice),
            }
            for indice, (caminho, var_padrao, var_amostra) in enumerate(self.linhas)
        ]

    def restaurar(self, linhas, nomes=None, ordem=None):
        """Recria a lista a partir de estado() (sem perguntar nada e avisando o VM uma vez só, no fim)."""
        if not linhas:
            self.mostrar_vazio()
            self._notificar()
            return
        self.carregar([linha["arquivo"] for linha in linhas], nomes, ordem)
        for indice, linha in enumerate(linhas):
            _, var_padrao, var_amostra = self.linhas[indice]
            var_padrao.set(bool(linha.get("padrao")))
            var_amostra.set(bool(linha.get("amostra", True)))
            if var_padrao.get():
                combo = self.combos_padrao[indice]
                certificado = linha.get("certificado") or ""
                combo.set(certificado if certificado in self.nomes_padroes else "")
                combo.grid()
            if linha.get("pdf"):
                self.definir_pdf(indice, linha["pdf"], notificar=False)
        self._notificar()

    def ordenar(self, coluna):
        """
        Reorganiza a lista pelo nome do arquivo ou pelo nome da ficha (sem nome vai para o fim), mantendo
        as marcações, os certificados e os PDFs de cada linha. Clicar de novo na mesma coluna inverte.
        """
        if not self.linhas:
            return
        estado = self.estado()

        def ordenado(decrescente):
            if coluna == "arquivo":
                return sorted(estado, key=lambda linha: chave_natural(os.path.basename(linha["arquivo"])),
                              reverse=decrescente)

            def chave(linha):
                nome = nome_da_amostra(self.nomes, _nome_arquivo(linha["arquivo"]))
                return chave_natural(nome or os.path.basename(linha["arquivo"]))
            com_nome = [linha for linha in estado if nome_da_amostra(self.nomes, _nome_arquivo(linha["arquivo"]))]
            sem_nome = [linha for linha in estado if linha not in com_nome]
            return sorted(com_nome, key=chave, reverse=decrescente) + sorted(sem_nome, key=chave)

        # crescente; se a lista já estava assim (ou o último clique foi esse), decrescente
        decrescente = self.ordem == (coluna, False) or ordenado(False) == estado
        self.restaurar(ordenado(decrescente), self.nomes, ordem=(coluna, decrescente))

    def mostrar_nomes(self, nomes):
        """Atualiza a coluna Nome ({código: nome}); arquivo sem nome fica com "—"."""
        self.nomes = dict(nomes or {})
        for indice, label in self.labels_nome.items():
            label.configure(text=nome_da_amostra(nomes, _nome_arquivo(self.linhas[indice][0])) or "—")

    def _escolher_pdf(self, indice):
        if self.ao_escolher_pdf:
            self.ao_escolher_pdf(indice)

    def definir_pdf(self, indice, caminho_pdf, notificar=True):
        """Vincula (ou remove, se caminho_pdf for None) o FullReport de uma linha."""
        botao_pdf, botao_remover = self.botoes_pdf[indice]
        if caminho_pdf:
            self.pdfs[indice] = caminho_pdf
            botao_pdf.configure(
                text=os.path.basename(caminho_pdf), fg_color=tema.OK_FUNDO, hover_color=tema.OK_HOVER,
                text_color=tema.OK_TEXTO,
            )
            botao_remover.pack(side="left", padx=(5, 0))
        else:
            self.pdfs.pop(indice, None)
            botao_pdf.configure(
                text="+ Adicionar PDF", fg_color=tema.CONTROLE, hover_color=tema.CONTROLE_HOVER, text_color=tema.TEXTO_2,
            )
            botao_remover.pack_forget()
        if notificar:
            self._notificar()

    def fullreports_por_arquivo(self):
        """Retorna {caminho_txt: caminho_pdf} das linhas que têm FullReport vinculado."""
        return {self.linhas[indice][0]: caminho_pdf for indice, caminho_pdf in self.pdfs.items()}

    def _marcar_padrao(self, indice):
        _, var_padrao, var_amostra = self.linhas[indice]
        combo = self.combos_padrao[indice]
        if var_padrao.get():
            outros = [j for j, (_, outro_padrao, _) in enumerate(self.linhas) if j != indice and outro_padrao.get()]
            if len(outros) >= self.MAX_PADROES:
                var_padrao.set(False)
                messagebox.showwarning(
                    "Limite de padrões",
                    f"É possível usar no máximo {self.MAX_PADROES} padrões. Desmarque um deles primeiro.",
                )
                return
            # sugere o certificado usado da última vez com esse arquivo; senão, um ainda não usado pelos outros padrões
            usados = {self.combos_padrao[j].get() for j in outros}
            livres = [n for n in self.nomes_padroes if n not in usados]
            if combo.get() not in self.nomes_padroes:
                lembrado = self.sugerir_certificado(self.linhas[indice][0], usados) if self.sugerir_certificado else None
                combo.set(lembrado or (livres or self.nomes_padroes or [self.SEM_PADRAO])[0])
            combo.grid()
            # por padrão, o arquivo padrão deixa de ser amostra (pode ser remarcado)
            var_amostra.set(False)
        else:
            combo.grid_remove()
            var_amostra.set(True)
        self._notificar()

    def atualizar_padroes(self, nomes):
        """Atualiza os padrões certificados disponíveis (depois de editados no Gerenciar Padrões)."""
        self.nomes_padroes = list(nomes)
        for indice, combo in self.combos_padrao.items():
            combo.configure(values=self.nomes_padroes or [self.SEM_PADRAO])
            if combo.get() not in self.nomes_padroes:
                # o padrão escolhido foi apagado/renomeado: escolhe outro só se a linha for um padrão
                marcado = self.linhas[indice][1].get()
                combo.set(self.nomes_padroes[0] if marcado and self.nomes_padroes else "")
        self._notificar()

    def _notificar(self):
        if self.ao_alterar:
            self.ao_alterar()

    def padroes_selecionados(self):
        """[(caminho do arquivo padrão, nome do padrão certificado)], na ordem da lista."""
        return [
            (caminho, self.combos_padrao[indice].get())
            for indice, (caminho, var_padrao, _) in enumerate(self.linhas)
            if var_padrao.get()
        ]

    def arquivos_amostras(self):
        return [caminho for caminho, _, var_amostra in self.linhas if var_amostra.get()]


