import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image

from models.fichaInformacaoModel import nome_da_amostra
from models.graficosModel import BASES, LIMITE_ERRO_AREA, TEMAS, TIPOS, UNIDADE_DA_BASE, GraficosModel
from resource_utils import resource_path
from views.componentesView import SeletorFormato
from views import tema


class GraficosView(ctk.CTkFrame):
    def __init__(self, master):
        # transparente: fica dentro da mesma caixa que o Exportar (montada no ConcentracaoVM)
        super().__init__(master, fg_color="transparent")

        icone_graficos = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "graficos.png")),
            size=(20, 20),
        )

        self.botao_grafico = ctk.CTkButton(
            self, state="disabled", image=icone_graficos, text="Gráficos", command="", compound="left", anchor="w",
            height=36, **tema.BOTAO_SECUNDARIO,
        )
        self.botao_grafico.pack(pady=(0, 6), fill="x")


COR_CABECALHO = tema.BORDA
CORES_LINHA = (tema.SUPERFICIE, tema.SUPERFICIE_2)  # zebrado
COR_LINHA_ERRO, COR_TEXTO_ERRO = tema.ERRO_FUNDO, tema.ERRO_TEXTO  # erro da área >= LIMITE_ERRO_AREA
GRUPOS = {"majoritario": "Majoritário", "traco": "Traço"}
ALTURA_TABELAS = 260  # quanto a janela cresce ao abrir o modo avançado


class TabelaElementos(ctk.CTkFrame):
    """
    Tabela do modo avançado, embaixo dos gráficos: todos os elementos da amostra, com uma caixinha para
    escolher quais entram nos gráficos (o slider decide em qual). Linha vermelha = erro da área >= LIMITE_ERRO_AREA.
    """

    PESOS = (1, 1, 2, 3, 2, 3, 2)  # caixinha, Z, Elemento, valor, % do total, Grupo, Erro da área

    def __init__(self, master, titulo, ao_alternar):
        """ao_alternar() é chamado depois de marcar/desmarcar."""
        super().__init__(master, fg_color="transparent")
        self.ao_alternar = ao_alternar
        self.excluidos = {}

        ctk.CTkLabel(self, text=titulo, font=tema.fonte(13, "bold"), anchor="w").pack(fill="x", padx=4)
        # o cabeçalho fica fora da rolagem; a margem direita compensa a barra de rolagem
        self.cabecalho = ctk.CTkFrame(self, fg_color=COR_CABECALHO, corner_radius=4)
        self.cabecalho.pack(fill="x", padx=(0, 16))
        self.corpo = ctk.CTkScrollableFrame(self, fg_color=CORES_LINHA[0], height=190, corner_radius=4)
        self.corpo.pack(fill="both", expand=True)
        self.corpo.grid_columnconfigure(0, weight=1)

    def _colunas(self, frame):
        for coluna, peso in enumerate(self.PESOS):
            frame.grid_columnconfigure(coluna, weight=peso, uniform="coluna")

    def preencher(self, linhas, excluidos, unidade):
        """
        linhas: GraficosModel.linhas_tabela(); excluidos: {"majoritario": set, "traco": set} (alterado aqui mesmo).
        Desmarcar tira o elemento dos dois gráficos, então ele continua fora mesmo se o slider mudar o grupo.
        """
        self.excluidos = excluidos
        for frame in (self.cabecalho, self.corpo):
            for filho in frame.winfo_children():
                filho.destroy()

        self._colunas(self.cabecalho)
        for coluna, texto in enumerate(("", "Z", "Elemento", unidade, "% do total", "Grupo", "Erro área")):
            ctk.CTkLabel(self.cabecalho, text=texto, font=tema.fonte(12, "bold"), height=26).grid(
                row=0, column=coluna, sticky="ew"
            )

        for i, linha in enumerate(linhas):
            erro_alto = linha["erro"] is not None and linha["erro"] >= LIMITE_ERRO_AREA
            fundo = COR_LINHA_ERRO if erro_alto else CORES_LINHA[i % 2]
            cor = COR_TEXTO_ERRO if erro_alto else None

            frame = ctk.CTkFrame(self.corpo, fg_color=fundo, corner_radius=0)
            frame.grid(row=i, column=0, sticky="ew")
            self._colunas(frame)

            marcado = not any(linha["elemento"] in fora for fora in excluidos.values())
            var = ctk.BooleanVar(master=self, value=marcado)
            ctk.CTkCheckBox(
                frame, text="", variable=var, width=20, checkbox_width=18, checkbox_height=18,
                command=lambda e=linha["elemento"], v=var: self._alternar(e, v.get()),
            ).grid(row=0, column=0, pady=2)

            erro = "—" if linha["erro"] is None else f"{linha['erro']:.1f}%"
            textos = (str(linha["z"]), linha["elemento"], GraficosModel.formatar_concentracao(linha["valor"]),
                      f"{100 * linha['fracao']:.2f}%", GRUPOS.get(linha["grupo"], linha["grupo"]), erro)
            for coluna, texto in enumerate(textos, start=1):
                rotulo = ctk.CTkLabel(frame, text=texto, font=tema.fonte(12), height=24)
                if cor:
                    rotulo.configure(text_color=cor)
                rotulo.grid(row=0, column=coluna, sticky="ew")

    def _alternar(self, elemento, marcado):
        for fora in self.excluidos.values():
            if marcado:
                fora.discard(elemento)
            else:
                fora.add(elemento)
        self.ao_alternar()


class GraficosJanela(ctk.CTkToplevel):
    """
    Pizzas majoritário / traço de uma amostra. O slider diz quantos elementos (os de menor concentração)
    vão para o traço; a escolha fica guardada por amostra (ResultadoPadrao.graficos_traco) para a exportação.
    """

    def __init__(self, master, resultados_por_padrao, model, estado, ao_exportar, ao_trocar_tipo=None, nomes=None,
                 tem_concentracao=True):
        """
        estado: {"automatico": bool, "tipo": chave de TIPOS}, compartilhado com o VM para valer na exportação.
        ao_exportar(janela): chamado pelo botão Exportar imagens.
        ao_trocar_tipo(tipo): chamado ao escolher outro tipo de gráfico (para lembrar da escolha).
        nomes: {código: nome} da ficha de informação, mostrados no lugar do código.
        tem_concentracao: False antes do Calcular (só a área normalizada; a base "Concentração" fica desabilitada).
        """
        super().__init__(master)
        tema.aplicar_icone(self)
        self.title("Gráficos")
        self.model = model
        self.estado = estado
        self.ao_trocar_tipo = ao_trocar_tipo
        self.nomes = nomes or {}
        self.codigos = {}  # texto do combo de amostra -> código da amostra
        self.resultados = {r.rotulo: r for r in resultados_por_padrao}
        self.resultado = resultados_por_padrao[0]
        self.valores = {}
        self.canvases = []
        self._n_atual = 0

        largura, altura = 1320, 660
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- padrão e amostra ---
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        if len(self.resultados) > 1:
            ctk.CTkLabel(topo, text="Padrão:", font=tema.fonte(13, "bold")).pack(side="left", padx=(0, 6))
            self.combo_padrao = ctk.CTkComboBox(
                topo, values=list(self.resultados), width=260, state="readonly", command=self._trocar_padrao,
            )
            self.combo_padrao.set(self.resultado.rotulo)
            self.combo_padrao.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(topo, text="Amostra:", font=tema.fonte(13, "bold")).pack(side="left", padx=(0, 6))
        self.combo_amostra = ctk.CTkComboBox(
            topo, values=[], width=220, state="readonly", command=lambda _: self._atualizar(),
        )
        self.combo_amostra.pack(side="left")

        # tipo de gráfico (vale para a tela e para as imagens exportadas)
        self.seletor_tipo = ctk.CTkSegmentedButton(
            topo, values=list(TIPOS.values()), command=self._trocar_tipo, font=tema.fonte(12),
        )
        self.seletor_tipo.set(TIPOS[self.estado.get("tipo", "anel")])
        self.seletor_tipo.pack(side="right")
        ctk.CTkLabel(topo, text="Gráfico:", font=tema.fonte(13, "bold")).pack(side="right", padx=(0, 6))

        # --- slider: elementos no traço ---
        linha_slider = ctk.CTkFrame(self, fg_color="transparent")
        linha_slider.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(linha_slider, text="Elementos no traço:", font=tema.fonte(13)).pack(side="left", padx=(0, 8))
        self.slider = ctk.CTkSlider(linha_slider, from_=0, to=1, number_of_steps=1, width=300,
                                    command=self._mover_slider)
        self.slider.pack(side="left")
        self.label_slider = ctk.CTkLabel(linha_slider, text="", font=tema.fonte(13))
        self.label_slider.pack(side="left", padx=10)

        # concentração ou área normalizada (para quem analisa algo sem concentração calculada)
        self.seletor_base = ctk.CTkSegmentedButton(
            linha_slider, values=list(BASES.values()), command=self._trocar_base, font=tema.fonte(12),
        )
        self.seletor_base.set(BASES[self.estado.get("base", "concentracao")])
        self.seletor_base.pack(side="right")
        if not tem_concentracao:
            self.seletor_base.configure(state="disabled")
            ctk.CTkLabel(
                linha_slider, text="Concentração só depois do Calcular", font=tema.fonte(12), text_color=tema.APAGADO,
            ).pack(side="right", padx=(0, 12))
        ctk.CTkLabel(linha_slider, text="Base:", font=tema.fonte(13, "bold")).pack(side="right", padx=(0, 6))

        # --- gráficos ---
        self.frame_graficos = ctk.CTkFrame(self, fg_color=TEMAS["escuro"]["fundo"])
        self.frame_graficos.grid(row=2, column=0, sticky="nsew", padx=10)
        self.frame_graficos.grid_rowconfigure(0, weight=1)
        self.frame_graficos.grid_columnconfigure((0, 1), weight=1)

        # --- modo avançado: uma tabela embaixo dos gráficos (aparece só com "Avançado" marcado) ---
        self.frame_tabelas = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tabelas.grid_columnconfigure(0, weight=1)
        self.tabela = TabelaElementos(self.frame_tabelas, "Elementos nos gráficos", self._redesenhar_figuras)
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=5)

        # --- rodapé: automático + exportar ---
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        self.var_automatico = ctk.BooleanVar(master=self, value=estado.get("automatico", False))
        ctk.CTkCheckBox(
            rodape, text="Distribuir automaticamente (cerca de 5% no traço, em todas as amostras)",
            variable=self.var_automatico, command=self._trocar_automatico, font=tema.fonte(12),
        ).pack(side="left")
        ctk.CTkButton(
            rodape, text="Exportar imagens", width=150, command=lambda: ao_exportar(self), **tema.BOTAO_PRINCIPAL,
        ).pack(side="right")
        SeletorFormato(rodape).pack(side="right", padx=(0, 8))
        self.var_avancado = ctk.BooleanVar(master=self, value=estado.get("avancado", False))
        ctk.CTkCheckBox(
            rodape, text="Avançado (escolher os elementos dos gráficos)", variable=self.var_avancado,
            command=self._trocar_avancado, font=tema.fonte(12),
        ).pack(side="right", padx=(0, 20))
        if self.var_avancado.get():
            self.geometry(f"{largura}x{self._altura_avancado(altura, +1)}+{x}+{max(y - ALTURA_TABELAS // 2, 0)}")
            self.frame_tabelas.grid(row=3, column=0, sticky="nsew", padx=5, pady=(10, 0))

        self._carregar_amostras()

        # janela modal, por cima da principal
        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    # ---------------------------------------------------------------
    def _trocar_padrao(self, rotulo):
        self.resultado = self.resultados[rotulo]
        self._carregar_amostras()

    def _carregar_amostras(self):
        # no combo, "nome · código" (dois nomes iguais continuam distinguíveis); sem nome, só o código
        self.codigos = {}
        for amostra in self.model.amostras(self.resultado):
            nome = nome_da_amostra(self.nomes, amostra)
            self.codigos[f"{nome} · {amostra}" if nome else amostra] = amostra
        textos = list(self.codigos)
        atual = self.combo_amostra.get()
        self.combo_amostra.configure(values=textos)
        self.combo_amostra.set(atual if atual in textos else (textos[0] if textos else ""))
        self._atualizar()

    def _amostra(self):
        """Código da amostra escolhida no combo."""
        return self.codigos.get(self.combo_amostra.get(), "")

    def _trocar_tipo(self, nome):
        self.estado["tipo"] = next(chave for chave, rotulo in TIPOS.items() if rotulo == nome)
        if self.ao_trocar_tipo:
            self.ao_trocar_tipo(self.estado["tipo"])
        self._atualizar()

    def _trocar_automatico(self):
        self.estado["automatico"] = self.var_automatico.get()
        self._atualizar()

    def _trocar_base(self, nome):
        self.estado["base"] = next(chave for chave, rotulo in BASES.items() if rotulo == nome)
        self._atualizar()

    def _altura_avancado(self, altura, sentido):
        """Altura da janela ao abrir (+1) ou fechar (-1) as tabelas, sem passar da tela."""
        if sentido > 0:
            return min(altura + ALTURA_TABELAS, self.winfo_screenheight() - 80)
        return max(altura - ALTURA_TABELAS, 500)

    def _trocar_avancado(self):
        self.estado["avancado"] = self.var_avancado.get()
        self.update_idletasks()
        sentido = 1 if self.estado["avancado"] else -1
        self.geometry(f"{self.winfo_width()}x{self._altura_avancado(self.winfo_height(), sentido)}")
        if self.estado["avancado"]:
            self.frame_tabelas.grid(row=3, column=0, sticky="nsew", padx=5, pady=(10, 0))
            self._preencher_tabelas(self._n_atual)
        else:
            self.frame_tabelas.grid_remove()

    def _mover_slider(self, valor):
        amostra = self._amostra()
        chave = self.model.chave_traco(amostra, self.estado.get("base", "concentracao"))
        n = int(round(valor))
        if self.resultado.graficos_traco.get(chave) == n:
            return
        self.resultado.graficos_traco[chave] = n
        self._desenhar(amostra, n)

    def _atualizar(self):
        """Ajusta o slider à amostra escolhida (cada uma tem o seu número de elementos) e redesenha."""
        amostra = self._amostra()
        base = self.estado.get("base", "concentracao")
        self.valores = self.model.valores_da_amostra(self.resultado, amostra, base) if amostra else {}
        maximo = self.model.max_traco(self.valores)
        n = self.model.n_traco_da_amostra(self.resultado, amostra, self.valores, self.estado["automatico"], base)

        self.slider.configure(to=max(maximo, 1), number_of_steps=max(maximo, 1))
        self.slider.set(n)
        bloqueado = self.estado["automatico"] or maximo == 0
        self.slider.configure(state="disabled" if bloqueado else "normal")
        self._desenhar(amostra, n)

    def _excluidos(self):
        return self.model.excluidos_da_amostra(self.resultado, self._amostra(), self.estado.get("base", "concentracao"))

    def _preencher_tabelas(self, n):
        if not self.estado.get("avancado"):
            return
        base = self.estado.get("base", "concentracao")
        erros = self.model.erros_area_percentuais(self.resultado, self._amostra()) if self.valores else {}
        linhas = self.model.linhas_tabela(self.valores, n, erros)
        self.tabela.preencher(linhas, self._excluidos(), UNIDADE_DA_BASE.get(base, "mg/kg"))

    def _desenhar(self, amostra, n):
        self._n_atual = n
        self._preencher_tabelas(n)
        if not self.valores:
            self._limpar_figuras()
            medida = "áreas" if self.estado.get("base") == "area" else "concentrações"
            self.label_slider.configure(text=f"sem {medida} para esta amostra")
            return

        _, traco = self.model.dividir(self.valores, n)
        self.label_slider.configure(
            text=f"{len(traco)} de {len(self.valores)} "
                 f"({self.model.formatar_percentual(self.model.fracao_traco(self.valores, traco))} do total)"
        )
        self._redesenhar_figuras()

    def _limpar_figuras(self):
        for canvas in self.canvases:
            canvas.get_tk_widget().destroy()
        self.canvases = []

    def _redesenhar_figuras(self):
        """Só os gráficos (as tabelas ficam): usado também ao marcar/desmarcar um elemento."""
        self._limpar_figuras()
        if not self.valores:
            return
        figuras = self.model.criar_figuras(
            self._amostra(), self.valores, self._n_atual, "escuro", self.resultado.nome,
            self.estado.get("tipo", "anel"), self.estado.get("base", "concentracao"), self.nomes, self._excluidos(),
        )
        for coluna, figura in enumerate(figuras):
            canvas = FigureCanvasTkAgg(figura, master=self.frame_graficos)
            canvas.draw()
            canvas.get_tk_widget().grid(row=0, column=coluna, sticky="nsew", padx=5, pady=5)
            self.canvases.append(canvas)
