import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from models.analiseModel import EXTENSAO, AnaliseInvalidaError, abrir_analise, salvar_analise
from models.configModel import carregar_ultimo_diretorio, salvar_ultimo_diretorio
from service.logErros import mensagem_erro_inesperado
from viewmodels.comparacaoVM import CompararAlvosVM
from viewmodels.concentracaoVM import ConcentracaoVM
from viewmodels.exportarVM import ExportarTodosVM
from viewmodels.multivariadaVM import MultivariadaVM
from views.abasLateraisView import ALVOS, AbasLateraisView

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


class MainView(ctk.CTk):
    def __init__(self):
        super().__init__()

        # o .exe não tem console: erro em qualquer botão vira mensagem na tela (e vai para o log)
        self.report_callback_exception = self._mostrar_erro

        # arrastar e soltar arquivos na lista (sem a biblioteca, o programa funciona igual, só sem isso)
        try:
            from tkinterdnd2 import TkinterDnD

            TkinterDnD._require(self)
        except Exception:
            pass

        self.title(TITULO)
        self.geometry("1400x800")
        self.resizable(True, True)

        # --- ABAS LATERAIS: um alvo por aba (Ag, Au, Rh) + análise estatística e exportar ---
        self.abas_laterais = AbasLateraisView(
            self, ao_trocar=self.mostrar_aba, ao_abrir_analise=self.abrir_analise, ao_salvar_analise=self.salvar_analise,
        )
        self.abas_laterais.pack(side="left", fill="y")

        # --- Conteúdo da aba selecionada ---
        self.area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.area.pack(side="left", fill="both", expand=True)

        self.telas = {}  # chave da aba -> tela (criada na primeira vez que a aba é aberta)
        self.tela_atual = None
        self.mostrar_aba(self.abas_laterais.selecionada)
        self._ligar_atalhos()

    # --- atalhos de teclado ---------------------------------------------------------------------------
    def _ligar_atalhos(self):
        atalhos = {
            "<F5>": self._atalho_calcular,
            "<Control-Return>": self._atalho_calcular,
            "<Control-o>": self._atalho_abrir,
            "<Control-O>": self._atalho_abrir,  # com Shift (ou Caps Lock)
            "<Control-s>": lambda _e: self.salvar_analise(),
            "<Control-S>": lambda _e: self.salvar_analise(),
            "<Control-e>": self._atalho_exportar,
            "<Control-E>": self._atalho_exportar,
            "<Control-g>": self._atalho_graficos,
            "<Control-G>": self._atalho_graficos,
        }
        for sequencia, acao in atalhos.items():
            self.bind_all(sequencia, lambda evento, a=acao: self._atalho(evento, a))

    def _atalho(self, evento, acao):
        """Só na janela principal: com um gráfico ou diálogo aberto por cima, a tecla fica com ele."""
        try:
            if evento.widget.winfo_toplevel() is not self:
                return None
        except (AttributeError, KeyError):
            return None
        acao(evento)
        return "break"

    def _vm_atual(self):
        tela = self.tela_atual
        return tela.calculo_vm if isinstance(tela, TelaAlvo) else None

    @staticmethod
    def _clicar(botao):
        if str(botao.cget("state")) == "normal":
            botao.invoke()

    def _atalho_calcular(self, _evento):
        vm = self._vm_atual()
        if vm:
            self._clicar(vm.view.calcular)

    def _atalho_abrir(self, evento):
        if evento.state & 0x1:  # Shift: abrir uma análise salva
            self.abrir_analise()
            return
        vm = self._vm_atual()
        if vm:
            vm.selecionar_arquivos()

    def _atalho_exportar(self, _evento):
        vm = self._vm_atual()
        if vm:
            self._clicar(vm.export.export.exportar_botao)
        elif hasattr(self, "exportar_vm") and self.tela_atual is self.exportar_vm.view:
            self._clicar(self.exportar_vm.view.exportar_botao)

    def _atalho_graficos(self, _evento):
        vm = self._vm_atual()
        if vm:
            self._clicar(vm.graficos.graficos_view.botao_grafico)

    # --- análise salva (.cxa) ---------------------------------------------------------------------------
    def salvar_analise(self):
        abas = {
            alvo: tela.calculo_vm.estado_analise()
            for alvo, tela in self.telas.items()
            if isinstance(tela, TelaAlvo) and tela.calculo_vm.lista_arquivos_view.linhas
        }
        if not abas:
            messagebox.showinfo("Salvar análise", "Nenhuma aba de alvo com arquivos para salvar.", parent=self)
            return
        caminho = filedialog.asksaveasfilename(
            parent=self, title="Salvar análise", defaultextension=EXTENSAO,
            filetypes=[("Análise da calculadora", f"*{EXTENSAO}")], initialfile=f"analise{EXTENSAO}",
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho:
            return
        salvar_ultimo_diretorio(caminho)
        try:
            salvar_analise(caminho, abas, self.abas_laterais.selecionada)
        except OSError as erro:
            messagebox.showerror("Salvar análise", f"Não foi possível salvar:\n{erro}", parent=self)
            return
        messagebox.showinfo(
            "Análise salva",
            f"Salva em:\n{caminho}\n\nGuarda a seleção de cada alvo ({', '.join(abas)}), não os números: "
            "ao abrir, os .txt são lidos e calculados de novo.",
            parent=self,
        )

    def abrir_analise(self):
        caminho = filedialog.askopenfilename(
            parent=self, title="Abrir análise", filetypes=[("Análise da calculadora", f"*{EXTENSAO}")],
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho:
            return
        salvar_ultimo_diretorio(caminho)
        try:
            dados, faltando = abrir_analise(caminho)
        except AnaliseInvalidaError as erro:
            messagebox.showerror("Abrir análise", str(erro), parent=self)
            return

        abas = {alvo: estado for alvo, estado in dados["abas"].items() if alvo in ALVOS}
        ocupadas = [
            alvo for alvo, tela in self.telas.items()
            if isinstance(tela, TelaAlvo) and tela.calculo_vm.lista_arquivos_view.linhas
        ]
        if ocupadas and not messagebox.askyesno(
            "Abrir análise",
            f"A análise substitui o que está em {', '.join(ocupadas)}.\n\nContinuar?", parent=self,
        ):
            return
        if faltando:
            messagebox.showwarning(
                "Arquivos não encontrados",
                "Estes arquivos não foram encontrados (nem no caminho salvo, nem na pasta da análise) "
                "e ficaram de fora:\n\n" + "\n".join(f"• {f}" for f in faltando),
                parent=self,
            )
        for alvo in ALVOS:
            if alvo in abas:
                self._tela(alvo).calculo_vm.restaurar_analise(abas[alvo])
            elif alvo in self.telas and alvo in ocupadas:
                self.telas[alvo].calculo_vm.restaurar_analise({})
        aba = dados.get("aba_aberta")
        aba = aba if aba in self.abas_laterais.abas else next(iter(abas), self.abas_laterais.selecionada)
        self.abas_laterais.selecionar(aba)
        self.title(f"{TITULO} · {os.path.basename(caminho)}")

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
                vm.ao_status = lambda texto, c=chave: self.abas_laterais.definir_status(c, texto)
                vm.ao_editar_padroes = self._repassar_padroes
            elif chave == "estatistica":
                self.comparar_alvos_vm = CompararAlvosVM(self.area, ALVOS, self._resultados_por_alvo, self._nomes_por_alvo)
                tela = self.comparar_alvos_vm.view
                self.multivariada_vm = MultivariadaVM(
                    tela.botao_multivariada, self._resultados_por_alvo, self._nomes_por_alvo
                )
            else:
                self.exportar_vm = ExportarTodosVM(
                    self.area, ALVOS, self._resultados_por_alvo, self._nomes_por_alvo, self._alvos_desatualizados
                )
                tela = self.exportar_vm.view
            self.telas[chave] = tela
        return self.telas[chave]

    def mostrar_aba(self, chave):
        tela = self._tela(chave)
        if self.tela_atual is tela:
            return
        if self.tela_atual is not None:
            self.tela_atual.pack_forget()  # só esconde: arquivos e resultados da aba continuam lá
        if chave == "exportar":
            self.exportar_vm.atualizar()  # algum alvo pode ter sido calculado desde a última vez
        elif chave == "estatistica":
            self.comparar_alvos_vm.atualizar()
            self.multivariada_vm.atualizar()
        tela.pack(fill="both", expand=True)
        self.tela_atual = tela
        self.title(f"{TITULO} · {chave}" if chave in ALVOS else TITULO)

    def _resultados_por_alvo(self):
        """{alvo: lista de ResultadoPadrao}; alvo ainda não aberto ou não calculado fica com lista vazia."""
        return {
            alvo: tela.calculo_vm.resultados_por_padrao if isinstance(tela, TelaAlvo) else []
            for alvo, tela in ((alvo, self.telas.get(alvo)) for alvo in ALVOS)
        }

    def _alvos_desatualizados(self):
        """Alvos com resultados que não correspondem mais à lista de arquivos (mudou depois do Calcular)."""
        return [alvo for alvo, tela in self.telas.items() if isinstance(tela, TelaAlvo) and tela.calculo_vm.desatualizado()]

    def _nomes_por_alvo(self):
        """{alvo: {código: nome}} das fichas de informação de cada alvo já aberto."""
        return {
            alvo: tela.calculo_vm.variaveis.nomes_amostras
            for alvo, tela in self.telas.items()
            if isinstance(tela, TelaAlvo)
        }

    def _repassar_padroes(self, origem, lista):
        """Padrões certificados editados numa aba: as outras abas de alvo passam a ver a mesma lista."""
        for tela in self.telas.values():
            if isinstance(tela, TelaAlvo) and tela.calculo_vm is not origem:
                tela.calculo_vm.receber_padroes(lista)
