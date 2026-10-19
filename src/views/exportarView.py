from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from resource_utils import resource_path

# Configurações iniciais do customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ExportarView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        icone_excel = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "excel.png")),
            size=(20, 20),
        )
        icone_engrenagem = ctk.CTkImage(
            light_image=Image.open(resource_path("imagens", "icones", "gear.png")),
            size=(18, 18),
        )

        self.label = ctk.CTkLabel(self, text="Exporte:", font=("Arial", 14, "bold"))
        self.label.pack(pady=10, fill="x", padx=20)

        linha = ctk.CTkFrame(self, fg_color="transparent")
        linha.pack(pady=10, fill="x", padx=20)

        # engrenagem: escolher quais abas vão para o Excel (fica habilitada mesmo antes de calcular)
        self.configurar_botao = ctk.CTkButton(
            linha, text="", width=32, image=icone_engrenagem, command=None,
        )
        self.configurar_botao.pack(side="right", padx=(6, 0))

        self.exportar_botao = ctk.CTkButton(
            linha,
            text="Exportar para Excel",
            state="disabled",
            command="",
            image=icone_excel,
            compound="left",
            font=("Arial", 12),
        )
        self.exportar_botao.pack(side="left", fill="x", expand=True)


class AbasExportarDialog(ctk.CTkToplevel):
    """Janela da engrenagem: marca quais abas entram no Excel."""

    # nome da aba -> (descrição curta, explicação do "?")
    DESCRICOES = {
        "Dados": (
            "Áreas medidas e normalizadas de cada amostra.",
            "Para cada amostra: elemento, Z, energia, área e erro (CPS), erro (%), "
            "área e erro normalizados e o fator de normalização (pelo Ar).\n\n"
            "Aba única: com vários padrões, os blocos de cada padrão ficam lado a lado.",
        ),
        "Concentrações": (
            "Tabela só com as concentrações.",
            "Uma linha por amostra e uma coluna por elemento, só com os valores de concentração "
            "(sem erro). Boa para copiar ou fazer gráficos.\n\n"
            "Com vários padrões, sai uma aba para cada padrão.",
        ),
        "Resultados": (
            "Concentração, erro e erro (%), com o LD de cada elemento.",
            "Para cada elemento, as colunas C, Erro e Erro (%) (o erro em % da concentração) de todas as amostras, "
            "com o LD do padrão na linha logo abaixo do nome do elemento.\n\n"
            "No fim: média, desvio padrão e DPR (%) das amostras (sem o próprio padrão).\n\n"
            "Com vários padrões, sai uma aba para cada padrão.",
        ),
        "Z-Score": (
            "Z'-Score de cada elemento contra o certificado.",
            "Por elemento: n, média e desvio padrão das amostras (sem o próprio padrão), "
            "valor e erro certificados e o Z'-Score.\n\n"
            "Só tem valores se o Z'-Score tiver sido marcado no cálculo. "
            "Com vários padrões, sai uma aba para cada padrão.",
        ),
        "SLD": (
            "Limite de detecção e sensibilidade.",
            "Por amostra, elemento e energia: o LD (precisa do PDF FullReport vinculado) "
            "e a Sensibilidade (precisa ter sido marcada no cálculo).\n\n"
            "Aba única: com vários padrões, cada padrão ganha as suas colunas.",
        ),
    }

    def __init__(self, master, abas, selecionadas, ao_salvar):
        super().__init__(master)
        self.title("Abas para exportar")
        self.resizable(False, False)
        self.ao_salvar = ao_salvar

        ctk.CTkLabel(
            self, text="Escolha as abas que vão para o Excel:", font=("Arial", 14, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(15, 10))

        lista = ctk.CTkFrame(self, fg_color="#2b2b2b")
        lista.pack(fill="x", padx=20)
        lista.grid_columnconfigure(1, weight=1)

        self.variaveis = {}
        for linha, aba in enumerate(abas):
            curta, longa = self.DESCRICOES.get(aba, ("", ""))
            var = ctk.BooleanVar(master=self, value=aba in selecionadas)
            self.variaveis[aba] = var

            ctk.CTkCheckBox(
                lista, text=aba, width=150, font=("Arial", 13, "bold"), variable=var,
            ).grid(row=linha, column=0, padx=(12, 6), pady=6, sticky="w")
            ctk.CTkLabel(lista, text=curta, font=("Arial", 12), text_color="#B0B0B0", anchor="w").grid(
                row=linha, column=1, padx=6, pady=6, sticky="w"
            )
            if longa:
                ctk.CTkButton(
                    lista, text="?", width=26, height=26, corner_radius=13, font=("Arial", 12, "bold"),
                    command=lambda a=aba, t=longa: messagebox.showinfo(a, t, parent=self),
                ).grid(row=linha, column=2, padx=(6, 12), pady=6)

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(botoes, text="Salvar", width=110, fg_color="#0D740F", command=self._salvar).pack(side="right")
        ctk.CTkButton(
            botoes, text="Cancelar", width=110, fg_color="#555555", hover_color="#666666", command=self.destroy,
        ).pack(side="right", padx=(0, 8))

        # janela modal, por cima da principal
        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _salvar(self):
        escolhidas = [aba for aba, var in self.variaveis.items() if var.get()]
        if not escolhidas:
            messagebox.showwarning("Abas para exportar", "Marque pelo menos uma aba.", parent=self)
            return
        self.ao_salvar(escolhidas)
        self.destroy()
