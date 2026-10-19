import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image

from resource_utils import resource_path

# Configurações iniciais do customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class GraficosView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        icone_graficos = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "graficos.png")),
            size=(20, 20),
        )

        self.label = ctk.CTkLabel(self, text="Crie Gráficos:", font=("Arial", 14, "bold"))
        self.label.pack(pady=10, fill="x", padx=20)

        self.botao_grafico = ctk.CTkButton(
            self, state="disabled", image=icone_graficos, text="Gráficos", font=("Arial", 12), command=""
        )
        self.botao_grafico.pack(pady=10, fill="x", padx=20)


class GraficosJanela(ctk.CTkToplevel):
    """
    Pizzas majoritário / traço de uma amostra. O slider diz quantos elementos (os de menor concentração)
    vão para o traço; a escolha fica guardada por amostra (ResultadoPadrao.graficos_traco) para a exportação.
    """

    def __init__(self, master, resultados_por_padrao, model, estado, ao_exportar):
        """
        estado: {"automatico": bool}, compartilhado com o VM para valer também na exportação.
        ao_exportar(janela): chamado pelo botão Exportar imagens.
        """
        super().__init__(master)
        self.title("Gráficos")
        self.model = model
        self.estado = estado
        self.resultados = {r.rotulo: r for r in resultados_por_padrao}
        self.resultado = resultados_por_padrao[0]
        self.valores = {}
        self.canvases = []

        largura, altura = 1120, 640
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- padrão e amostra ---
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        if len(self.resultados) > 1:
            ctk.CTkLabel(topo, text="Padrão:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
            self.combo_padrao = ctk.CTkComboBox(
                topo, values=list(self.resultados), width=260, state="readonly", command=self._trocar_padrao,
            )
            self.combo_padrao.set(self.resultado.rotulo)
            self.combo_padrao.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(topo, text="Amostra:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
        self.combo_amostra = ctk.CTkComboBox(
            topo, values=[], width=220, state="readonly", command=lambda _: self._atualizar(),
        )
        self.combo_amostra.pack(side="left")

        # --- slider: elementos no traço ---
        linha_slider = ctk.CTkFrame(self, fg_color="transparent")
        linha_slider.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(linha_slider, text="Elementos no traço:", font=("Arial", 13)).pack(side="left", padx=(0, 8))
        self.slider = ctk.CTkSlider(linha_slider, from_=0, to=1, number_of_steps=1, width=300,
                                    command=self._mover_slider)
        self.slider.pack(side="left")
        self.label_slider = ctk.CTkLabel(linha_slider, text="", font=("Arial", 13))
        self.label_slider.pack(side="left", padx=10)

        # --- gráficos ---
        self.frame_graficos = ctk.CTkFrame(self)
        self.frame_graficos.grid(row=2, column=0, sticky="nsew", padx=10)
        self.frame_graficos.grid_rowconfigure(0, weight=1)
        self.frame_graficos.grid_columnconfigure((0, 1), weight=1)

        # --- rodapé: automático + exportar ---
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.var_automatico = ctk.BooleanVar(master=self, value=estado.get("automatico", False))
        ctk.CTkCheckBox(
            rodape, text="Distribuir automaticamente (cerca de 5% no traço, em todas as amostras)",
            variable=self.var_automatico, command=self._trocar_automatico, font=("Arial", 12),
        ).pack(side="left")
        ctk.CTkButton(
            rodape, text="Exportar imagens", width=150, fg_color="#0D740F", command=lambda: ao_exportar(self),
        ).pack(side="right")

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
        amostras = self.model.amostras(self.resultado)
        atual = self.combo_amostra.get()
        self.combo_amostra.configure(values=amostras)
        self.combo_amostra.set(atual if atual in amostras else (amostras[0] if amostras else ""))
        self._atualizar()

    def _trocar_automatico(self):
        self.estado["automatico"] = self.var_automatico.get()
        self._atualizar()

    def _mover_slider(self, valor):
        amostra = self.combo_amostra.get()
        n = int(round(valor))
        if self.resultado.graficos_traco.get(amostra) == n:
            return
        self.resultado.graficos_traco[amostra] = n
        self._desenhar(amostra, n)

    def _atualizar(self):
        """Ajusta o slider à amostra escolhida (cada uma tem o seu número de elementos) e redesenha."""
        amostra = self.combo_amostra.get()
        self.valores = self.model.valores_da_amostra(self.resultado, amostra) if amostra else {}
        maximo = self.model.max_traco(self.valores)
        n = self.model.n_traco_da_amostra(self.resultado, amostra, self.valores, self.estado["automatico"])

        self.slider.configure(to=max(maximo, 1), number_of_steps=max(maximo, 1))
        self.slider.set(n)
        bloqueado = self.estado["automatico"] or maximo == 0
        self.slider.configure(state="disabled" if bloqueado else "normal")
        self._desenhar(amostra, n)

    def _desenhar(self, amostra, n):
        for canvas in self.canvases:
            canvas.get_tk_widget().destroy()
        self.canvases = []
        if not self.valores:
            self.label_slider.configure(text="sem concentrações para esta amostra")
            return

        _, traco = self.model.dividir(self.valores, n)
        self.label_slider.configure(
            text=f"{len(traco)} de {len(self.valores)} "
                 f"({self.model.formatar_percentual(self.model.fracao_traco(self.valores, traco))} do total)"
        )
        for coluna, figura in enumerate(self.model.criar_figuras(amostra, self.valores, n)):
            canvas = FigureCanvasTkAgg(figura, master=self.frame_graficos)
            canvas.draw()
            canvas.get_tk_widget().grid(row=0, column=coluna, sticky="nsew", padx=5, pady=5)
            self.canvases.append(canvas)
