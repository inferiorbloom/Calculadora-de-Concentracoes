import customtkinter as ctk

COR_APAGADA = "#898781"
COR_AVISO = "#FFB86B"


class NomesAmostrasDialog(ctk.CTkToplevel):
    """
    Revisão dos nomes das amostras (lidos da ficha de informação ou digitados).
    linhas: [(código, nome, texto da ficha)] dos arquivos da lista; texto None = não está na ficha lida,
    "" = nenhuma ficha lida;
    extras: as mesmas tuplas para códigos que estão na ficha mas não na lista de arquivos.
    ao_salvar({código: nome}) recebe só os nomes preenchidos.
    """

    def __init__(self, master, titulo, linhas, extras, ao_salvar):
        super().__init__(master)
        self.title("Nomes das amostras")
        self.geometry("760x560")
        self.minsize(560, 300)
        self.ao_salvar = ao_salvar
        self.entradas = {}  # código -> CTkEntry

        ctk.CTkLabel(self, text=titulo, font=("Arial", 14, "bold"), anchor="w", justify="left").pack(
            fill="x", padx=20, pady=(15, 2)
        )
        sem_nome = sum(1 for _, nome, _ in linhas if not nome)
        resumo = f"{len(linhas) - sem_nome} de {len(linhas)} arquivos com nome." if linhas else ""
        if any(texto is None for _, _, texto in linhas):
            resumo += " Os que não estão na ficha ficam destacados: dá para digitar o nome aqui."
        ctk.CTkLabel(
            self, text=resumo + "\nO código continua sendo o identificador; o nome aparece ao lado dele.",
            font=("Arial", 12), text_color=COR_APAGADA, anchor="w", justify="left",
        ).pack(fill="x", padx=20, pady=(0, 10))

        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(side="bottom", fill="x", padx=20, pady=15)
        ctk.CTkButton(botoes, text="Salvar", width=110, fg_color="#0D740F", command=self._salvar).pack(side="right")
        ctk.CTkButton(
            botoes, text="Cancelar", width=110, fg_color="#555555", hover_color="#666666", command=self.destroy,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            botoes, text="Apagar todos", width=110, fg_color="#8B1E1E", hover_color="#B22222", command=self._apagar,
        ).pack(side="left")

        lista = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b")
        lista.pack(fill="both", expand=True, padx=20)
        lista.grid_columnconfigure(2, weight=1)

        linha = 0
        for texto, itens in (("Arquivos da lista", linhas), ("Na ficha, mas fora da lista de arquivos", extras)):
            if not itens:
                continue
            ctk.CTkLabel(lista, text=texto, font=("Arial", 12, "bold"), text_color=COR_APAGADA, anchor="w").grid(
                row=linha, column=0, columnspan=3, padx=10, pady=(8, 2), sticky="w"
            )
            linha += 1
            for codigo, nome, texto_ficha in itens:
                self._linha(lista, linha, codigo, nome, texto_ficha)
                linha += 1

        if not linhas and not extras:
            ctk.CTkLabel(
                lista, text="Nenhum arquivo na lista e nenhuma ficha lida.", font=("Arial", 13),
            ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # janela modal, por cima da principal
        self.transient(master.winfo_toplevel())
        self.after(50, self._focar)

    def _linha(self, lista, linha, codigo, nome, texto_ficha):
        ctk.CTkLabel(lista, text=codigo, font=("Consolas", 13), width=90, anchor="w").grid(
            row=linha, column=0, padx=(10, 6), pady=3, sticky="w"
        )
        entrada = ctk.CTkEntry(lista, width=200, font=("Arial", 12), placeholder_text="sem nome")
        if nome:
            entrada.insert(0, nome)
        elif texto_ficha is None:
            entrada.configure(border_color=COR_AVISO)
        entrada.grid(row=linha, column=1, padx=6, pady=3, sticky="w")
        self.entradas[codigo] = entrada

        if texto_ficha is None:
            ficha, cor = "não encontrado na ficha", COR_AVISO
        else:
            ficha, cor = (f"ficha: {texto_ficha}" if texto_ficha else ""), COR_APAGADA
        ctk.CTkLabel(lista, text=ficha, font=("Arial", 11), text_color=cor, anchor="w").grid(
            row=linha, column=2, padx=(6, 10), pady=3, sticky="w"
        )

    def _focar(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def _apagar(self):
        for entrada in self.entradas.values():
            entrada.delete(0, "end")

    def _salvar(self):
        nomes = {codigo: entrada.get().strip() for codigo, entrada in self.entradas.items()}
        self.ao_salvar({codigo: nome for codigo, nome in nomes.items() if nome})
        self.destroy()
