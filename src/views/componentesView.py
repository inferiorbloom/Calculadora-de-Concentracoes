import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from models.configModel import (
    FORMATOS_IMAGEM,
    carregar_formato_imagem,
    carregar_ultimo_diretorio,
    salvar_formato_imagem,
    salvar_ultimo_diretorio,
)
from models.graficosModel import TEMAS, salvar_figura
from views import tema


class SeletorFormato(ctk.CTkSegmentedButton):
    """PNG / SVG / PDF ao lado do "Exportar imagens"; a escolha vale para todas as janelas e fica salva."""

    def __init__(self, master):
        super().__init__(
            master, values=[f.upper() for f in FORMATOS_IMAGEM], font=tema.fonte(12), command=self._trocar,
        )
        self.set(carregar_formato_imagem().upper())

    @staticmethod
    def _trocar(rotulo):
        salvar_formato_imagem(rotulo.lower())


class JanelaFigura(ctk.CTkToplevel):
    """
    Uma figura só, com "Exportar imagem" (no formato escolhido, tema claro).
    criar_figura(tema): devolve a Figure do matplotlib no tema "escuro" (tela) ou "claro" (arquivo).
    """

    def __init__(self, master, titulo, criar_figura, nome_arquivo):
        super().__init__(master)
        tema.aplicar_icone(self)
        self.title(titulo)
        self.criar_figura = criar_figura
        self.nome_arquivo = nome_arquivo
        largura, altura = 1000, 680
        x = (self.winfo_screenwidth() - largura) // 2
        y = (self.winfo_screenheight() - altura) // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        quadro = ctk.CTkFrame(self, fg_color=TEMAS["escuro"]["fundo"])
        quadro.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))
        canvas = FigureCanvasTkAgg(criar_figura("escuro"), master=quadro)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkButton(rodape, text="Exportar imagem", width=150, command=self._exportar, **tema.BOTAO_PRINCIPAL).pack(
            side="right"
        )
        SeletorFormato(rodape).pack(side="right", padx=(0, 8))

        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _exportar(self):
        formato = carregar_formato_imagem()
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Exportar imagem", defaultextension=f".{formato}",
            filetypes=[(formato.upper(), f"*.{formato}")], initialfile=f"{self.nome_arquivo}.{formato}",
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho:
            return
        salvar_ultimo_diretorio(caminho)
        gravado = salvar_figura(self.criar_figura("claro"), os.path.splitext(caminho)[0], formato)
        messagebox.showinfo("Imagem exportada", f"Salva em:\n{gravado}", parent=self)
