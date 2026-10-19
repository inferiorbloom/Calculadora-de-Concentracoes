import os

from models.leitorArquivoModel import ArquivoInvalidoError
from models.limitedeteccaoModel import LimiteDeteccaoModel
from views.limiteDeteccaoView import LimiteDeteccaoView


class LimiteDeteccaoVM:
    def __init__(self, master, service, variaveis):

        self.service = service
        self.variaveis = variaveis

        self.limitedeteccao_view = LimiteDeteccaoView(master)
        self.limitedeteccao_model = LimiteDeteccaoModel()

    def extrair_backgrounds(self, fullreports_por_arquivo):
        """
        fullreports_por_arquivo: {caminho_txt: caminho_pdf}, vindo da lista de arquivos.
        Retorna os backgrounds indexados pelo .txt, para o vínculo não depender do nome do .pdf.
        Os backgrounds não dependem do padrão, então são lidos uma vez só e reaproveitados.
        """
        backgrounds = {}
        for arquivo_txt, arquivo_pdf in fullreports_por_arquivo.items():
            try:
                backgrounds[arquivo_txt] = self.service.extrair_backgrounds(arquivo_pdf)
            except Exception as erro:
                raise ArquivoInvalidoError(
                    f"Não foi possível ler o FullReport {os.path.basename(arquivo_pdf)}:\n{erro}"
                ) from erro
        return backgrounds

    def calcula_resultado_limite(self, backgrounds, resultado_padrao):
        """Calcula o LD com os dados de UM padrão (ResultadoPadrao) e guarda nele."""
        resultado_padrao.resultado_limite = self.limitedeteccao_model.calcular_limite_deteccao(
            backgrounds,
            resultado_padrao.arquivo_padrao,
            resultado_padrao.c_padrao,
            resultado_padrao.areas_normalizadas,
            resultado_padrao.concentracoes,
            area_padrao=resultado_padrao.area_padrao,
        )
        return resultado_padrao.resultado_limite
