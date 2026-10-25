import json
import os
import shutil

from resource_utils import ensure_directory, resource_path, user_data_path


class Variaveis:
    """Estado de uma aba de alvo (arquivos, resultados, nomes) e o cadastro de padrões certificados."""

    def __init__(self):
        self.lista_arquivos = []
        # um ResultadoPadrao para cada padrão marcado na lista de arquivos
        self.resultados_por_padrao = []
        # nomes das amostras (ficha de informação ou digitados): {código da medida: nome}
        self.nomes_amostras = {}

        self.padroes = {}
        self.path = user_data_path("padroes", "padroes.json")
        ensure_directory(os.path.dirname(self.path))

        pacote_json = resource_path("padroes", "padroes.json")
        if not os.path.exists(self.path) and os.path.exists(pacote_json):
            shutil.copy2(pacote_json, self.path)

        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.padroes = json.load(f)
