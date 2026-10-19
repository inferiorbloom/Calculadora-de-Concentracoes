import os
from tkinter.filedialog import askopenfilenames
from tkinter import filedialog
import math
import pdfplumber
import re
from collections import defaultdict

from resource_utils import resource_path
from models.configModel import carregar_ultimo_diretorio, salvar_ultimo_diretorio


class Service:
    def __init__(self, master):
        super().__init__()
        self.master = master

        self.pasta_txt = resource_path("aquisicoes")
        self.pasta_pdf = resource_path("reports")

    def _obter_initialdir(self):
        diretorio_salvo = carregar_ultimo_diretorio()
        if diretorio_salvo and os.path.isdir(diretorio_salvo):
            return diretorio_salvo
        return self.pasta_txt

    def _atualizar_diretorio(self, caminho):
        if caminho:
            salvar_ultimo_diretorio(caminho)

    # Função para selecionar os arquivos (padrão e amostras são marcados depois, na lista)
    def selecionar_arquivos(self):
        arquivos = askopenfilenames(
            initialdir=self._obter_initialdir(),
            title="Selecione os arquivos.txt (padrão e amostras)",
            filetypes=[("Arquivos de texto", "*.txt")],
        )
        if arquivos:
            self._atualizar_diretorio(arquivos[-1])
        return arquivos

    # Função para selecionar o FullReport (.pdf) de um arquivo da lista
    def selecionar_fullReport(self):
        fullreport = filedialog.askopenfilename(
            initialdir=self._obter_initialdir(),
            title="Selecione o FullReport (.pdf) deste arquivo",
            filetypes=[("FullReports", "*.pdf")]
        )
        self._atualizar_diretorio(fullreport)
        return fullreport

    def extrair_backgrounds(self, caminho_pdf):
        """Lê o FullReport e retorna o background de cada elemento."""
        with pdfplumber.open(caminho_pdf) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() + "\n"

        linhas = texto.splitlines()

        backgrounds_raw = defaultdict(lambda: {"K": [], "L": []})

        elemento_atual = None
        camada_atual = None

        for i, linha in enumerate(linhas):

            m_elem = re.match(r"\s*\d+\s*([A-Z][a-z]?)\s+(K|L)\b", linha)
            if m_elem:
                elemento_atual = m_elem.group(1)
                camada_atual = m_elem.group(2)
                continue

            if elemento_atual and camada_atual == "K":
                if re.match(r"\s*KA[12]\b(?!\s*Escape)", linha):
                    if i + 1 < len(linhas):
                        prox = linhas[i + 1]
                        m_bg = re.search(r"\d+\.\d+\d+\.\d+\s+(\d+)\b", prox)
                        if m_bg:
                            bg = int(m_bg.group(1))
                            backgrounds_raw[elemento_atual]["K"].append(bg)

            if elemento_atual and camada_atual == "L":
                m_area = re.search(r"(\d+)\s*±", linha)
                if m_area and i + 1 < len(linhas):
                    prox = linhas[i + 1]
                    m_bg = re.search(r"\d+\.\d+\d+\.\d+\s+(\d+)\b", prox)
                    if m_bg:
                        area = int(m_area.group(1))
                        bg = int(m_bg.group(1))
                        backgrounds_raw[elemento_atual]["L"].append((area, bg))

        backgrounds = {}

        for elemento, dados in backgrounds_raw.items():

            if dados["K"]:
                if len(dados["K"]) == 1:
                    backgrounds[elemento] = dados["K"][0]
                else:
                    backgrounds[elemento] = round(sum(dados["K"]) / len(dados["K"]))

            elif dados["L"]:
                dados_L_ordenados = sorted(dados["L"], key=lambda x: x[0], reverse=True)

                if len(dados_L_ordenados) >= 2:
                    bg1 = dados_L_ordenados[0][1]
                    bg2 = dados_L_ordenados[1][1]
                    backgrounds[elemento] = round((bg1 + bg2) / 2)
                else:
                    backgrounds[elemento] = dados_L_ordenados[0][1]

        return backgrounds
