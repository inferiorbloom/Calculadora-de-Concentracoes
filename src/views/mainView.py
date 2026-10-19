from tkinter import messagebox

import customtkinter as ctk
from service.logErros import mensagem_erro_inesperado
from viewmodels.concentracaoVM import ConcentracaoVM
from views.abasLateraisView import ALVOS, GERAIS, AbasLateraisView

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

TITULO = "🧪 Calculadora de Concentrações"


class TelaAlvo(ctk.CTkFrame):
    """
    Uma calculadora completa para UM alvo (menu + arquivos + resultados), com o seu próprio ConcentracaoVM.
    Nada é compartilhado entre os alvos, a não ser o cadastro de padrões certificados (o padroes.json).
    """

    def __init__(self, master, alvo):
        super().__init__(master, fg_color="transparent")
        self.alvo = alvo

        # --- SIDEBAR (menu deste alvo) ---
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y")

        # --- MAIN AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        # --- Frame dinâmico (conteúdo que muda) ---
        self.dynamic_frame = ctk.CTkFrame(self.main_frame)
        self.dynamic_frame.pack(fill="both", expand=True, pady=10, padx=40)

        ctk.CTkLabel(self.sidebar, text=f"☰ Menu · {alvo}", font=("Arial Black", 18, "bold")).pack(pady=20)

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

        # --- Instância da ViewModel ---
        self.calculo_vm = ConcentracaoVM(
            self.sidebar,
            self.result_frame,
            self.arquivos_frame,
            self.dynamic_frame,
            lambda: None,  # não há "tela inicial" para voltar: cada alvo mantém a sua tela
            alvo=alvo,
        )
        self.calculo_vm.botoes()


class TelaEmBreve(ctk.CTkFrame):
    """Abas que vão trabalhar com todos os alvos juntos (ainda sem função)."""

    def __init__(self, master, titulo, texto):
        super().__init__(master, corner_radius=10)
        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(centro, text=titulo, font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(centro, text=texto, font=("Segoe UI", 13), text_color="#898781", justify="center").pack(pady=10)


class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        # o .exe não tem console: erro em qualquer botão vira mensagem na tela (e vai para o log)
        self.report_callback_exception = self._mostrar_erro

        self.title(TITULO)
        self.geometry("1400x800")
        self.resizable(True, True)

        # --- ABAS LATERAIS: um alvo por aba (Ag, Au, Rh) + análise estatística e exportar ---
        self.abas_laterais = AbasLateraisView(self, ao_trocar=self.mostrar_aba)
        self.abas_laterais.pack(side="left", fill="y")

        # --- Conteúdo da aba selecionada ---
        self.area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.area.pack(side="left", fill="both", expand=True)

        self.telas = {}  # chave da aba -> tela (criada na primeira vez que a aba é aberta)
        self.tela_atual = None
        self.mostrar_aba(self.abas_laterais.selecionada)

    def _mostrar_erro(self, _tipo, erro, _traceback):
        messagebox.showerror("Erro", mensagem_erro_inesperado(erro), parent=self)

    # compatibilidade: o primeiro alvo continua acessível como antes
    @property
    def calculo_vm(self):
        return self._tela("Ag").calculo_vm

    @property
    def sidebar(self):
        return self._tela("Ag").sidebar

    def _tela(self, chave):
        if chave not in self.telas:
            if chave in ALVOS:
                tela = TelaAlvo(self.area, chave)
                vm = tela.calculo_vm
                vm.ao_calcular = lambda n, c=chave: self.abas_laterais.definir_status(c, f"{n} amostras")
                vm.ao_editar_padroes = self._repassar_padroes
            elif chave == "estatistica":
                tela = TelaEmBreve(self.area, GERAIS[chave][0],
                                   "Em breve: estatísticas com os resultados de Ag, Au e Rh juntos.")
            else:
                tela = TelaEmBreve(self.area, GERAIS[chave][0],
                                   "Em breve: uma exportação com os resultados de Ag, Au e Rh juntos.\n"
                                   "Por enquanto, use o Exportar para Excel no menu de cada alvo.")
            self.telas[chave] = tela
        return self.telas[chave]

    def mostrar_aba(self, chave):
        tela = self._tela(chave)
        if self.tela_atual is tela:
            return
        if self.tela_atual is not None:
            self.tela_atual.pack_forget()  # só esconde: arquivos e resultados da aba continuam lá
        tela.pack(fill="both", expand=True)
        self.tela_atual = tela
        self.title(f"{TITULO} · {chave}" if chave in ALVOS else TITULO)

    def _repassar_padroes(self, origem, lista):
        """Padrões certificados editados numa aba: as outras abas de alvo passam a ver a mesma lista."""
        for tela in self.telas.values():
            if isinstance(tela, TelaAlvo) and tela.calculo_vm is not origem:
                tela.calculo_vm.receber_padroes(lista)
