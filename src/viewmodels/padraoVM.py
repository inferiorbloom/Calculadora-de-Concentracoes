from models.PadraoModel import PadraoModel
from views.PadraoView import PadraoView
from store.variaveis import Variaveis
from viewmodels.gerenciarPadraoVM import Gerenciar_PadraoVM
import customtkinter as ctk


class PadraoVM:
    def __init__(self, master, dynamic_frame, sidebar_frame):
        self.frame = ctk.CTkFrame(master)
        self.frame.pack(pady=10)

        self.padrao_view = PadraoView(master, self.frame)
        self.padrao_model = PadraoModel()

        self.variaveis = Variaveis()

        self.gerenciar_padraovm = Gerenciar_PadraoVM(dynamic_frame, sidebar_frame, self.frame, self.padrao_view)

    def volta_padrao(self):
        self.lista_padrao = self.variaveis.padroes
        return self.padrao_view.lista_box(self.lista_padrao, self.gerenciar_padraovm)

    def nomes_padroes(self):
        return [item["nome"] for item in self.padrao_view.lista_dados]

    def buscar_padrao(self, nome):
        """Retorna o padrão certificado com esse nome (ou None)."""
        return next((item for item in self.padrao_view.lista_dados if item["nome"] == nome), None)

    def ao_atualizar_padroes(self, callback):
        """callback(nomes) é chamado sempre que os padrões forem editados no Gerenciar Padrões."""
        self.padrao_view.ao_atualizar = lambda lista: callback([item["nome"] for item in lista])
