import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from models.graficosModel import TEMAS
from models.multivariadaModel import MODOS_ABAIXO_LD, REFERENCIAS
from views.componentesView import SeletorFormato

ABAS = {"biplot": "Biplot (PCA)", "correlacao": "Correlação (ρp)", "hca": "Agrupamento (HCA)", "dados": "Dados usados"}


class MultivariadaJanela(ctk.CTkToplevel):
    """
    PCA, correlação e HCA das amostras de um alvo/padrão. Quem calcula é o VM:
    calcular(alvo, padrão, modo) -> (resultado, título) ou lança um erro com a mensagem para o usuário;
    figura(aba, tema) -> Figure; ao_exportar_imagens(janela), ao_exportar_excel(janela).
    opcoes: {alvo: [rótulos dos padrões]}.
    """

    def __init__(self, master, opcoes, calcular, figura, ao_exportar_imagens, ao_exportar_excel):
        super().__init__(master)
        self.title("Análise multivariada")
        self.opcoes = opcoes
        self.calcular = calcular
        self.figura = figura
        self.resumo = ""
        self.canvas = None

        largura, altura = 1200, 760
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{max(y, 0)}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        topo = ctk.CTkFrame(self, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        ctk.CTkLabel(topo, text="Alvo:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
        self.combo_alvo = ctk.CTkComboBox(
            topo, values=list(opcoes), width=90, state="readonly", command=lambda _a: self._trocar_alvo(),
        )
        self.combo_alvo.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(topo, text="Padrão:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
        self.combo_padrao = ctk.CTkComboBox(
            topo, values=[], width=280, state="readonly", command=lambda _p: self._atualizar(),
        )
        self.combo_padrao.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(topo, text="Abaixo do LD:", font=("Arial", 13, "bold")).pack(side="left", padx=(0, 6))
        self.seletor_ld = ctk.CTkSegmentedButton(
            topo, values=list(MODOS_ABAIXO_LD.values()), command=lambda _m: self._atualizar(), font=("Arial", 12),
        )
        self.seletor_ld.set(MODOS_ABAIXO_LD["medido"])
        self.seletor_ld.pack(side="left")
        ctk.CTkButton(topo, text="Referências", width=110, command=self._referencias).pack(side="right")

        self.seletor_aba = ctk.CTkSegmentedButton(
            self, values=list(ABAS.values()), command=lambda _a: self._mostrar(), font=("Arial", 12),
        )
        self.seletor_aba.set(ABAS["biplot"])
        self.seletor_aba.grid(row=1, column=0, pady=(10, 6))

        self.quadro = ctk.CTkFrame(self, fg_color=TEMAS["escuro"]["fundo"])
        self.quadro.grid(row=2, column=0, sticky="nsew", padx=10)
        self.texto = ctk.CTkTextbox(self.quadro, font=("Consolas", 13), wrap="word")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.mensagem = ctk.CTkLabel(rodape, text="", font=("Arial", 12), text_color="#898781", anchor="w",
                                     justify="left", wraplength=640)
        self.mensagem.pack(side="left", fill="x", expand=True)
        self.botoes = [
            ctk.CTkButton(rodape, text="Exportar Excel", width=130, command=lambda: ao_exportar_excel(self)),
            ctk.CTkButton(rodape, text="Exportar imagens", width=150, fg_color="#0D740F",
                          command=lambda: ao_exportar_imagens(self)),
        ]
        for botao in self.botoes:
            botao.pack(side="right", padx=(8, 0))
        SeletorFormato(rodape).pack(side="right", padx=(8, 0))

        self.combo_alvo.set(next(iter(opcoes), ""))
        self._trocar_alvo()

        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def modo(self):
        return next(chave for chave, rotulo in MODOS_ABAIXO_LD.items() if rotulo == self.seletor_ld.get())

    def _trocar_alvo(self):
        padroes = self.opcoes.get(self.combo_alvo.get(), [])
        self.combo_padrao.configure(values=padroes)
        self.combo_padrao.set(padroes[0] if padroes else "")
        self._atualizar()

    def _atualizar(self):
        """Refaz a análise com o alvo, o padrão e o tratamento escolhidos."""
        try:
            resultado = self.calcular(self.combo_alvo.get(), self.combo_padrao.get(), self.modo())
        except Exception as erro:  # mensagem pronta para o usuário (dados insuficientes etc.)
            self.resumo = str(erro)
            self.mensagem.configure(text="Não foi possível fazer a análise com esta escolha.")
            for botao in self.botoes:
                botao.configure(state="disabled")
            self.seletor_aba.set(ABAS["dados"])
            self._mostrar()
            return
        self.resumo = resultado
        excluidos = "" if "Elementos excluídos" not in resultado else " Alguns elementos ficaram de fora: veja Dados usados."
        self.mensagem.configure(text=f"Valores em mg/kg, transformação clr.{excluidos}")
        for botao in self.botoes:
            botao.configure(state="normal")
        self._mostrar()

    def aba(self):
        return next(chave for chave, rotulo in ABAS.items() if rotulo == self.seletor_aba.get())

    def _mostrar(self):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        self.texto.pack_forget()
        aba = self.aba()
        if aba == "dados" or str(self.botoes[0].cget("state")) == "disabled":
            self.texto.configure(state="normal")
            self.texto.delete("1.0", "end")
            self.texto.insert("end", self.resumo)
            self.texto.configure(state="disabled")
            self.texto.pack(fill="both", expand=True, padx=6, pady=6)
            return
        self.canvas = FigureCanvasTkAgg(self.figura(aba, "escuro"), master=self.quadro)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def _referencias(self):
        janela = ctk.CTkToplevel(self)
        janela.title("Referências")
        janela.geometry("820x560")
        texto = ctk.CTkTextbox(janela, font=("Arial", 13), wrap="word")
        texto.pack(fill="both", expand=True, padx=12, pady=12)
        texto.insert("end", "O que foi decidido e com base em quê está no topo de src/models/multivariadaModel.py "
                            "e na aba Referências do Excel exportado.\n\n")
        texto.insert("end", "\n\n".join(REFERENCIAS))
        texto.configure(state="disabled")
        janela.transient(self)
        janela.after(50, lambda: (janela.lift(), janela.focus_force()))
