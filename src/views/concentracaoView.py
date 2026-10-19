import os
from tkinter import messagebox, ttk

import customtkinter as ctk
import numpy as np
from PIL import Image
from tksheet import Sheet

from models.abaResultadosModel import montar_titulo_coluna
from models.elementosQuimicos import z_do_elemento
from models.leitorArquivoModel import nome_amostra as _nome_arquivo
from resource_utils import resource_path


class ConcentracaoView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Carregando ícone
        icone_pasta = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "pasta.png")),
            size=(20, 20),
        )
        icone_calcular = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "calcular.png")),
            size=(20, 20),
        )

        self.label_select = ctk.CTkLabel(self, text="Selecione os arquivos:", font=("Arial", 14, "bold"))
        self.label_select.pack(pady=10, fill="x", padx=20)

        self.selecionar_arquivos = ctk.CTkButton(
            self, text="Selecionar Arquivos", image=icone_pasta, compound="left", font=("Arial", 12)
        )
        self.selecionar_arquivos.pack(pady=10, fill="x", padx=20)

        self.label_calc = ctk.CTkLabel(self, text="Calcule:", font=("Arial", 14, "bold"))
        self.label_calc.pack(pady=10, fill="x", padx=20)

        # cálculos extras, feitos junto com o Calcular quando marcados
        self.label_extras = ctk.CTkLabel(self, text="Incluir no cálculo:", font=("Arial", 12, "bold"), anchor="w")
        self.label_extras.pack(pady=(10, 0), fill="x", padx=20)

        self.lista_extras = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.lista_extras.pack(pady=(5, 10), fill="x", padx=20)

        self.var_z_score = ctk.BooleanVar(value=False)
        self.check_z_score = ctk.CTkCheckBox(
            self.lista_extras, text="Z'-Score", font=("Arial", 12), variable=self.var_z_score
        )
        self.check_z_score.pack(anchor="w", padx=10, pady=(8, 4))

        self.var_sensibilidade = ctk.BooleanVar(value=False)
        self.check_sensibilidade = ctk.CTkCheckBox(
            self.lista_extras, text="Sensibilidade", font=("Arial", 12), variable=self.var_sensibilidade
        )
        self.check_sensibilidade.pack(anchor="w", padx=10, pady=(4, 8))

        self.calcular = ctk.CTkButton(
            self,
            text="Calcular",
            font=("Arial Black", 12),
            state="disabled",
            fg_color="#0D740F",
            text_color="#FFFFFF",
            command=None,
            image=icone_calcular,
            compound="left",
        )
        self.calcular.pack(pady=10, fill="x", padx=20)

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


def _ld_referencia(ld_resultado, nome_amostra, elemento, nome_padrao):
    """LD da própria amostra; se não houver, o do padrão; senão, o primeiro disponível."""
    for nome in (nome_amostra, nome_padrao):
        valor = _para_float((ld_resultado.get(nome) or {}).get(elemento))
        if valor is not None:
            return valor
    for dados in ld_resultado.values():
        valor = _para_float((dados or {}).get(elemento))
        if valor is not None:
            return valor
    return None


class ConcentracaoResultadoView(ctk.CTkFrame):
    """Resultados em formato de planilha, com uma aba para cada tipo de cálculo."""

    ABA_CONCENTRACOES = "Concentrações"
    ABA_Z_SCORE = "Z'-Score"
    ABA_SENSIBILIDADE = "Sensibilidade"

    COR_FUNDO = "#2b2b2b"
    COR_LISTRA = "#333333"
    COR_LD = ("#22303f", "#9ECBFF")  # (fundo, texto)
    COR_ABAIXO_LD = ("#5a1e1e", "#FF8A8A")  # valores <= 3xLD
    COR_INCERTEZA_ALTA = ("#5a3a12", "#FFB86B")  # erro >= 40% do valor
    COR_AMBOS = ("#5a1e1e", "#FFE135")  # <= 3xLD e erro >= 40%: fundo vermelho, texto amarelo

    LIMITE_INCERTEZA = 0.40

    def __init__(self, master):
        super().__init__(master)

        # a legenda vai primeiro (embaixo) para não ser empurrada para fora pelas abas
        self._criar_legenda()

        # seletor de abas: só aparece quando houver mais de uma tabela
        self.seletor = ctk.CTkSegmentedButton(self, values=[], command=self._mostrar_aba)

        self.area = ctk.CTkFrame(self, fg_color=self.COR_FUNDO)
        self.area.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.area.grid_rowconfigure(0, weight=1)
        self.area.grid_columnconfigure(0, weight=1)

        self.abas = {}
        self.tabelas = {}
        self._criar_aba(self.ABA_CONCENTRACOES)

    def _criar_legenda(self):
        legenda = ctk.CTkFrame(self, fg_color="transparent")
        legenda.pack(side="bottom", fill="x", padx=15, pady=(0, 5))

        itens = [
            (self.COR_LD, "LD (limite de detecção)"),
            (self.COR_ABAIXO_LD, "Valor ≤ 3×LD"),
            (self.COR_INCERTEZA_ALTA, f"Incerteza ≥ {self.LIMITE_INCERTEZA:.0%} do valor"),
        ]
        for (fundo, texto_cor), texto in itens:
            ctk.CTkLabel(
                legenda, text="", width=14, height=14, corner_radius=3, fg_color=fundo,
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(legenda, text=texto, font=("Arial", 12), text_color=texto_cor).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(
            legenda, text=MARCADOR_AMBOS.strip(), font=("Arial", 13, "bold"), text_color=self.COR_AMBOS[1],
        ).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            legenda, text=f"≤ 3×LD e incerteza ≥ {self.LIMITE_INCERTEZA:.0%}",
            font=("Arial", 12), text_color=self.COR_AMBOS[1],
        ).pack(side="left", padx=(0, 18))

        ctk.CTkLabel(
            legenda,
            text="Ctrl+C copia as células selecionadas (ou a tabela inteira) para o Excel.",
            font=("Arial", 11),
            text_color="#8a8a8a",
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
            font=("Arial", 12, "normal"),
            header_font=("Arial", 12, "bold"),
            default_row_height=26,
            default_header_height=28,
            outline_thickness=0,
            table_bg=self.COR_FUNDO,
            table_fg="#DCE4EE",
            table_grid_fg="#3a3a3a",
            header_bg="#1f1f1f",
            header_fg="#FFFFFF",
            header_grid_fg="#3a3a3a",
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
            if not self.seletor.winfo_manager():
                self.seletor.pack(before=self.area, pady=(5, 0))
        else:
            self.seletor.pack_forget()

    def _mostrar_aba(self, nome):
        self.abas[nome].tkraise()
        self.seletor.set(nome)

    def _preencher(self, tabela, colunas, linhas, celulas_destacadas=None):
        """
        linhas: lista de (valores, tag); tag "ld" destaca a linha, None usa a cor alternada.
        celulas_destacadas: {(linha, coluna): (fundo, texto)}.
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
        tabela.align("A", align="w", redraw=False)

        listradas = 0
        for indice, (_, tag) in enumerate(linhas):
            if tag == "ld":
                tabela.highlight_rows(indice, bg=self.COR_LD[0], fg=self.COR_LD[1], redraw=False)
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

    # mostrar resultados como planilha
    def mostrar_resultados(
        self, concentracoes, ld_resultado=None, unidades=None, nome_padrao=None, erros=None, padrao_certificado=None,
    ):
        """
        erros: mesma estrutura de concentracoes, com o erro propagado de cada valor.
        padrao_certificado: {"nome": ..., "elementos": {...}}; mostrado na linha do padrão quando ele não é amostra.
        """
        ld_resultado = ld_resultado or {}
        erros = erros or {}

        # resultados anteriores de Z'-Score e Sensibilidade não valem mais
        self._remover_aba(self.ABA_Z_SCORE)
        self._remover_aba(self.ABA_SENSIBILIDADE)

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
            linhas.append(([f"LD - {nome_padrao}"] + [_formatar_ld(ld_padrao.get(s)) for s in simbolos], "ld"))

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

            linhas.append(([rotulo_padrao] + [texto_certificado(s) for s in simbolos], None))

        destacadas = {}
        for nome_amostra, elementos, erros_amostra in amostras:
            indice_linha = len(linhas)
            celulas = [rotulo_padrao if nome_amostra == nome_padrao else nome_amostra]

            for coluna, (chave, simbolo) in enumerate(zip(todos_elementos, simbolos), start=1):
                texto = texto_celula(elementos.get(chave), erros_amostra.get(chave))
                valor = _para_float(elementos.get(chave))
                erro = _para_float(erros_amostra.get(chave))
                ld = _ld_referencia(ld_resultado, nome_amostra, simbolo, nome_padrao)

                abaixo_ld = valor is not None and ld is not None and valor <= 3 * ld
                incerteza_alta = (
                    valor is not None and erro is not None and valor != 0
                    and abs(erro / valor) >= self.LIMITE_INCERTEZA
                )

                # vermelho (≤ 3×LD) tem prioridade; com incerteza alta também, ganha o marcador
                if abaixo_ld and incerteza_alta:
                    destacadas[(indice_linha, coluna)] = self.COR_AMBOS
                    texto += MARCADOR_AMBOS
                elif abaixo_ld:
                    destacadas[(indice_linha, coluna)] = self.COR_ABAIXO_LD
                elif incerteza_alta:
                    destacadas[(indice_linha, coluna)] = self.COR_INCERTEZA_ALTA

                celulas.append(texto)

            linhas.append((celulas, None))

        colunas = ["Amostra"] + [_titulo_coluna(e, unidades, contagem) for e in todos_elementos]
        self._preencher(self.tabelas[self.ABA_CONCENTRACOES], colunas, linhas, destacadas)
        self._mostrar_aba(self.ABA_CONCENTRACOES)

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

        linhas = []
        for nome_amostra, elementos in resultados.items():
            for chave, valor in sorted(elementos.items(), key=lambda item: _chave_ordem(item[0])):
                elemento, energia = chave
                linhas.append(([nome_amostra, elemento, f"{energia:.3f}", f"{valor:.6g}"], None))

        colunas = ["Amostra", "Elemento", "Energia (keV)", "Sensibilidade"]
        self._preencher(self._aba(self.ABA_SENSIBILIDADE), colunas, linhas)
        self._mostrar_aba(self.ABA_SENSIBILIDADE)


class ResultadosPadroesView(ctk.CTkFrame):
    """
    Um ConcentracaoResultadoView para cada padrão, com um seletor no topo para alternar entre eles.
    Cada padrão tem as suas próprias abas (Concentrações, Z'-Score, Sensibilidade).
    """

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.barra = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.barra, text="Padrão:", font=("Arial", 14, "bold")).pack(side="left", padx=(10, 8))
        self.seletor = ctk.CTkSegmentedButton(self.barra, values=[], command=self._mostrar_padrao)
        self.seletor.pack(side="left")

        self.views = {}  # rótulo -> ConcentracaoResultadoView
        self.rotulos = {}  # nome do padrão -> rótulo
        self.ativo = None
        self._criar_views([None])

    def _criar_views(self, rotulos):
        for view in self.views.values():
            view.destroy()
        self.views = {rotulo: ConcentracaoResultadoView(self) for rotulo in rotulos}

        # o seletor só aparece quando houver mais de um padrão
        if len(rotulos) > 1:
            self.seletor.configure(values=list(rotulos))
            self.barra.pack(side="top", fill="x", pady=(5, 0))
        else:
            self.barra.pack_forget()

        self.ativo = None
        self._mostrar_padrao(rotulos[0])

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

        for r in resultados_por_padrao:
            self._view(r).mostrar_resultados(
                r.concentracoes,
                r.resultado_limite,
                r.unidade_padrao,
                _nome_arquivo(r.arquivo_padrao),
                erros=r.erros_concentracao,
                padrao_certificado=r.c_padrao,
            )

        # recalculando, continua no padrão que estava aberto
        if anterior in self.views:
            self._mostrar_padrao(anterior)

    def mostrar_z_score(self, resultados_por_padrao):
        for r in resultados_por_padrao:
            self._view(r).mostrar_z_score(r.z_score_resultado)

    def mostrar_sensibilidade(self, resultados_por_padrao):
        for r in resultados_por_padrao:
            self._view(r).mostrar_sensibilidade(r.sensibilidade_resultado)


class ListaArquivosView(ctk.CTkScrollableFrame):
    """Lista dos arquivos selecionados, onde o usuário marca os Padrões (com o padrão certificado) e as Amostras."""

    MAX_PADROES = 2
    SEM_PADRAO = "Nenhum padrão cadastrado"

    def __init__(self, master, ao_alterar=None, ao_escolher_pdf=None, nomes_padroes=None):
        super().__init__(master, fg_color="#2b2b2b", height=200)
        self.ao_alterar = ao_alterar
        self.ao_escolher_pdf = ao_escolher_pdf
        self.nomes_padroes = list(nomes_padroes or [])
        self.linhas = []  # (caminho, var_padrao, var_amostra)
        self.pdfs = {}  # índice da linha -> caminho do FullReport (.pdf) para o LD
        self.botoes_pdf = {}  # índice da linha -> (botão escolher, botão remover)
        self.combos_padrao = {}  # índice da linha -> combobox do padrão certificado
        self.grid_columnconfigure(5, weight=1)  # coluna vazia: mantém o LD colado no nome do arquivo
        self.mostrar_vazio()

    def limpar(self):
        for w in self.winfo_children():
            w.destroy()
        self.linhas = []
        self.pdfs = {}
        self.botoes_pdf = {}
        self.combos_padrao = {}

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
            self, text="Nenhum arquivo selecionado. Use \"Selecionar Arquivos\" no Menu.", font=("Arial", 14)
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")
        self._voltar_ao_topo()

    def carregar(self, caminhos):
        self.limpar()

        # cabeçalho
        for col, texto in enumerate(["Padrão", "Amostra", "Arquivo", "Padrão Certificado", "Limite de Detecção"]):
            ctk.CTkLabel(self, text=texto, font=("Arial Black", 13)).grid(
                row=0, column=col, padx=10, pady=(5, 5), sticky="w"
            )

        for indice, caminho in enumerate(caminhos):
            var_padrao = ctk.BooleanVar(value=False)
            var_amostra = ctk.BooleanVar(value=True)

            ctk.CTkCheckBox(
                self, text="", width=24, variable=var_padrao, command=lambda i=indice: self._marcar_padrao(i)
            ).grid(row=indice + 1, column=0, padx=(22, 10), pady=3)

            ctk.CTkCheckBox(
                self, text="", width=24, variable=var_amostra, command=self._notificar
            ).grid(row=indice + 1, column=1, padx=(26, 10), pady=3)

            ctk.CTkLabel(self, text=os.path.basename(caminho), font=("Arial", 14)).grid(
                row=indice + 1, column=2, padx=10, pady=3, sticky="w"
            )

            # padrão certificado: só aparece quando a linha estiver marcada como Padrão
            combo_padrao = ctk.CTkComboBox(
                self,
                width=220,
                height=26,
                state="readonly",
                values=self.nomes_padroes or [self.SEM_PADRAO],
                font=("Arial", 12),
                button_color="#213A57",
                border_color="#213A57",
                fg_color="#375270",
                command=lambda _escolha: self._notificar(),
            )
            combo_padrao.grid(row=indice + 1, column=3, padx=10, pady=3, sticky="w")
            combo_padrao.grid_remove()
            self.combos_padrao[indice] = combo_padrao

            celula_ld = ctk.CTkFrame(self, fg_color="transparent")
            celula_ld.grid(row=indice + 1, column=4, padx=10, pady=3, sticky="w")

            botao_pdf = ctk.CTkButton(
                celula_ld, width=170, height=26, font=("Arial", 12),
                command=lambda i=indice: self._escolher_pdf(i),
            )
            botao_pdf.pack(side="left")

            botao_remover = ctk.CTkButton(
                celula_ld, text="✕", width=26, height=26, fg_color="#8B1E1E", hover_color="#B22222",
                command=lambda i=indice: self.definir_pdf(i, None),
            )

            self.botoes_pdf[indice] = (botao_pdf, botao_remover)
            self.linhas.append((caminho, var_padrao, var_amostra))
            self.definir_pdf(indice, None, notificar=False)

        self._voltar_ao_topo()

    def _escolher_pdf(self, indice):
        if self.ao_escolher_pdf:
            self.ao_escolher_pdf(indice)

    def definir_pdf(self, indice, caminho_pdf, notificar=True):
        """Vincula (ou remove, se caminho_pdf for None) o FullReport de uma linha."""
        botao_pdf, botao_remover = self.botoes_pdf[indice]
        if caminho_pdf:
            self.pdfs[indice] = caminho_pdf
            botao_pdf.configure(text=os.path.basename(caminho_pdf), fg_color="#0D740F", hover_color="#0B5E0C")
            botao_remover.pack(side="left", padx=(5, 0))
        else:
            self.pdfs.pop(indice, None)
            tema = ctk.ThemeManager.theme["CTkButton"]
            botao_pdf.configure(text="+ Adicionar PDF", fg_color=tema["fg_color"], hover_color=tema["hover_color"])
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
            # sugere um padrão certificado ainda não usado pelos outros arquivos padrão
            usados = {self.combos_padrao[j].get() for j in outros}
            livres = [n for n in self.nomes_padroes if n not in usados]
            if combo.get() not in self.nomes_padroes:
                combo.set((livres or self.nomes_padroes or [self.SEM_PADRAO])[0])
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




