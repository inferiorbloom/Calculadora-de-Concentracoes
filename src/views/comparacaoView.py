import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image

from models.comparacaoModel import ESTILOS
from models.graficosModel import TEMAS
from resource_utils import resource_path


def _icone_graficos():
    return ctk.CTkImage(light_image=Image.open(resource_path("imagens", "icones", "graficos.png")), size=(20, 20))


class CompararPadroesView(ctk.CTkFrame):
    """Botão "Comparar padrões", na mesma caixa do Exportar e dos Gráficos (montada no ConcentracaoVM)."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.botao = ctk.CTkButton(
            self, state="disabled", image=_icone_graficos(), text="Comparar padrões", font=("Arial", 12),
        )
        self.botao.pack(pady=(0, 15), fill="x", padx=20)


class AnaliseEstatisticaView(ctk.CTkFrame):
    """Aba lateral "Análise estatística": por enquanto, os gráficos comparando os alvos já calculados."""

    def __init__(self, master, alvos):
        super().__init__(master, corner_radius=10)

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(centro, text="Comparar alvos", font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(
            centro,
            text="Um gráfico por elemento com os resultados de cada alvo lado a lado, com barra de erro.\n"
                 "As amostras são ligadas entre os alvos pelo nome da ficha de informação;\n"
                 "com mais de um padrão, cada padrão certificado ganha o seu painel.",
            font=("Segoe UI", 13), text_color="#898781", justify="center",
        ).pack(pady=(10, 15))

        lista = ctk.CTkFrame(centro, fg_color="#2b2b2b")
        lista.pack(fill="x", pady=(0, 15))
        lista.grid_columnconfigure(1, weight=1)

        self.status = {}
        for linha, alvo in enumerate(alvos):
            ctk.CTkLabel(lista, text=alvo, font=("Segoe UI", 16, "bold"), width=40, anchor="w").grid(
                row=linha, column=0, padx=(14, 6), pady=6, sticky="w"
            )
            self.status[alvo] = ctk.CTkLabel(lista, text="", font=("Segoe UI", 12), anchor="w")
            self.status[alvo].grid(row=linha, column=1, padx=(6, 14), pady=6, sticky="w")

        self.botao = ctk.CTkButton(
            centro, text="Comparar alvos", state="disabled", image=_icone_graficos(), compound="left",
            font=("Arial", 13), height=36,
        )
        self.botao.pack(fill="x")

    def mostrar_status(self, alvo, texto, calculado):
        self.status[alvo].configure(text=texto, text_color="#f0efec" if calculado else "#898781")


class ComparacaoJanela(ctk.CTkToplevel):
    """Um gráfico por elemento (escolhido no combo), em barras ou linhas, comparando padrões ou alvos."""

    def __init__(self, master, titulo, comparacao, model, estado, ao_exportar, ao_trocar_estilo=None):
        """
        estado: {"estilo": chave de ESTILOS}, compartilhado com o VM para valer na exportação.
        ao_exportar(janela): chamado pelo botão Exportar imagens.
        ao_trocar_estilo(estilo): chamado ao escolher Barras/Linhas (para lembrar da escolha).
        """
        super().__init__(master)
        self.title(titulo)
        self.comparacao = comparacao
        self.model = model
        self.estado = estado
        self.ao_trocar_estilo = ao_trocar_estilo
        self.elementos = model.elementos(comparacao)
        self.canvas = None

        largura, altura = 1320, 700
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- elemento e estilo ---
        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(topo, text="Elemento:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
        ctk.CTkButton(topo, text="◀", width=32, command=lambda: self._andar(-1)).pack(side="left")
        self.combo_elemento = ctk.CTkComboBox(
            topo, values=self.elementos, width=110, state="readonly", command=lambda _: self._desenhar(),
        )
        self.combo_elemento.set(self.elementos[0] if self.elementos else "")
        self.combo_elemento.pack(side="left", padx=4)
        ctk.CTkButton(topo, text="▶", width=32, command=lambda: self._andar(1)).pack(side="left")

        self.seletor_estilo = ctk.CTkSegmentedButton(
            topo, values=list(ESTILOS.values()), command=self._trocar_estilo, font=("Arial", 12),
        )
        self.seletor_estilo.set(ESTILOS[self.estado.get("estilo", "barras")])
        self.seletor_estilo.pack(side="right")
        ctk.CTkLabel(topo, text="Gráfico:", font=("Arial", 13, "bold")).pack(side="right", padx=(0, 6))

        # --- gráfico ---
        self.frame_grafico = ctk.CTkFrame(self, fg_color=TEMAS["escuro"]["fundo"])
        self.frame_grafico.grid(row=1, column=0, sticky="nsew", padx=10)
        self.frame_grafico.grid_rowconfigure(0, weight=1)
        self.frame_grafico.grid_columnconfigure(0, weight=1)

        # --- rodapé: avisos + exportar ---
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(
            rodape, text="\n".join(comparacao.avisos), font=("Arial", 12), text_color="#898781", justify="left",
            anchor="w", wraplength=1000,
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            rodape, text="Exportar imagens", width=150, fg_color="#0D740F", command=lambda: ao_exportar(self),
            state="normal" if self.elementos else "disabled",
        ).pack(side="right")

        self._desenhar()

        # janela modal, por cima da principal
        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _andar(self, passo):
        if not self.elementos:
            return
        atual = self.combo_elemento.get()
        i = self.elementos.index(atual) if atual in self.elementos else 0
        self.combo_elemento.set(self.elementos[(i + passo) % len(self.elementos)])
        self._desenhar()

    def _trocar_estilo(self, nome):
        self.estado["estilo"] = next(chave for chave, rotulo in ESTILOS.items() if rotulo == nome)
        if self.ao_trocar_estilo:
            self.ao_trocar_estilo(self.estado["estilo"])
        self._desenhar()

    def _desenhar(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        elemento = self.combo_elemento.get()
        if not elemento:
            ctk.CTkLabel(self.frame_grafico, text="Nenhum elemento com concentração para comparar.",
                         font=("Arial", 13), text_color="#898781").grid(row=0, column=0)
            return
        figura = self.model.criar_figura(
            self.comparacao, elemento, self.estado.get("estilo", "barras"), "escuro", figsize=(13, 5.6),
        )
        self.canvas = FigureCanvasTkAgg(figura, master=self.frame_grafico)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
