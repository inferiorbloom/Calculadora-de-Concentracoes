import customtkinter as ctk
from views import tema


class PadraoView(ctk.CTkFrame):
    """
    Guarda a lista de padrões certificados e o botão de gerenciá-los.
    A escolha do padrão em si é feita na lista de arquivos, ao lado de cada arquivo marcado como Padrão.
    """

    def __init__(self, master, frame):
        super().__init__(master)

        self.frame = frame

        # o próprio botão (do Gerenciar Padrões) já diz "Padrões certificados"
        self.label_opcoes = ctk.CTkLabel(self.frame, text="Padrões certificados:", font=tema.fonte(13, "bold"))

        self.lista_dados = []
        self.ao_atualizar = None  # chamado com a nova lista quando os padrões são editados

    def lista_box(self, lista, gerenciar_padraovm):
        self.gerenciar_padraovm = gerenciar_padraovm
        self.gerenciar_padraovm.botao_gerenciar()

        if not isinstance(lista, list) or not all(isinstance(item, dict) for item in lista):
            print("Lista precisa ser uma lista de dicionários com chave 'nome'")
            self.lista_dados = []
            return self.lista_dados

        self.lista_dados = lista
        return self.lista_dados

    def atualizar_lista(self, nova_lista):
        """Chamado pelo Gerenciar Padrões depois de salvar o JSON."""
        self.lista_dados = nova_lista
        if self.ao_atualizar:
            self.ao_atualizar(nova_lista)
