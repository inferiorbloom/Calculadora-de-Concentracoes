import customtkinter as ctk
import json
import os
import shutil

from resource_utils import ensure_directory, resource_path, user_data_path


class Variaveis(ctk.CTkFrame):
    def __init__(self, master=None):
        super().__init__(master)
        self.lista_arquivo_padrao = None
        self.lista_arquivos = []
        self.resultado_limite = []
        self.sensibilidade_resultado = {}
        self.c_padrao = []
        self.resultados = [None, None]  # armazena os resultados (concentracoes e areas normalizadas)

        self.padroes = {}
        self.path = user_data_path("padroes", "padroes.json")
        ensure_directory(os.path.dirname(self.path))

        pacote_json = resource_path("padroes", "padroes.json")
        if not os.path.exists(self.path) and os.path.exists(pacote_json):
            shutil.copy2(pacote_json, self.path)

        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.padroes = json.load(f)

    def verificar_estado(self):
        print("Verificando estado atual das variáveis:")
        print(f"- Arquivo padrão: {self.lista_arquivo_padrao}")
        print(f"- Amostras: {self.lista_arquivos}")
        print(f"- Resultado_limite: {self.resultado_limite}")
        print(f"- Resultados: {'OK' if self.resultados else 'Nenhum'}")
