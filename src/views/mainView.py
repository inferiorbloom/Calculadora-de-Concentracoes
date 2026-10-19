from tkinter import messagebox

import customtkinter as ctk
from service.logErros import mensagem_erro_inesperado
from viewmodels.concentracaoVM import ConcentracaoVM

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        # o .exe não tem console: erro em qualquer botão vira mensagem na tela (e vai para o log)
        self.report_callback_exception = self._mostrar_erro

        self.title("🧪 Calculadora de Concentrações")
        self.geometry("1400x800")
        self.resizable(True, True)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        # --- MAIN AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # --- Frame dinâmico (conteúdo que muda) ---
        self.dynamic_frame = ctk.CTkFrame(self.main_frame)
        self.dynamic_frame.pack(fill="both", expand=True, pady=10, padx=40)

        titulo = ctk.CTkLabel(self.sidebar, text="☰ Menu", font=("Arial Black", 18, "bold"))
        titulo.pack(pady=20)

        # Botão Sair
        self.botao_sair = ctk.CTkButton(
            self.sidebar, text="Sair", fg_color="red", text_color="#FFFFFF", font=("Arial Black", 12), command=self.quit
        )
        self.botao_sair.pack(side="bottom", pady=20, fill="x", padx=20)

        # Monta tela principal
        self.mostrar_tela_inicial()

    def _mostrar_erro(self, _tipo, erro, _traceback):
        messagebox.showerror("Erro", mensagem_erro_inesperado(erro), parent=self)

    def mostrar_tela_inicial(self):
        # Limpa conteúdo anterior
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        # Configuração: uma coluna; os resultados ocupam o espaço que sobra
        self.dynamic_frame.grid_columnconfigure(0, weight=1)
        self.dynamic_frame.grid_rowconfigure(0, weight=0)
        self.dynamic_frame.grid_rowconfigure(1, weight=1)

        # --- Linha 1: Arquivos (marcação de Padrão e Amostras) ---
        self.arquivos_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="#2b2b2b")
        self.arquivos_frame.grid(row=0, column=0, sticky="we", padx=10, pady=(10, 5))

        # --- Linha 2: Resultados ---
        self.result_frame = ctk.CTkFrame(self.dynamic_frame, height=250)
        self.result_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.result_frame.grid_propagate(False)

        if not hasattr(self, "calculo_vm"):
            # --- Instância da ViewModel ---
            self.calculo_vm = ConcentracaoVM(
                self.sidebar,
                self.result_frame,
                self.arquivos_frame,
                self.dynamic_frame,
                self.mostrar_tela_inicial,
            )
            if not hasattr(self, "botoes_criados"):
                self.calculo_vm.botoes()
                self.botoes_criados = True  # marca que já criou os botoes
