from models.limitedeteccaoModel import LimiteDeteccaoModel
from views.limiteDeteccaoView import LimiteDeteccaoView


class LimiteDeteccaoVM:
    def __init__(self, master, service, variaveis):

        self.service = service
        self.variaveis = variaveis

        #self.arquivo_padrao = self.variaveis.lista_arquivo_padrao
        #self.c_padrao = self.variaveis.c_padrao

        self.limitedeteccao_view = LimiteDeteccaoView(master)
        # self.limitedeteccao_view.pack(fill="x", padx=10, pady=10)  # Removido para evitar botão duplicado
        # self.limitedeteccao_view.botao_limite.configure(command=self.calcula_resultado_limite)  # Botão removido da view

        self.limitedeteccao_model = LimiteDeteccaoModel()

    def habilita_limite(self, arquivo_padrao, c_padrao):
        """Habilita o botão Limites"""
        self.arquivo_padrao = arquivo_padrao
        self.c_padrao = c_padrao
        # self.limitedeteccao_view.botao_limite.configure(state="normal")  # Botão removido da view
        return self.arquivo_padrao, self.c_padrao

    def calcula_resultado_limite(self, fullreports_por_arquivo):
        """fullreports_por_arquivo: {caminho_txt: caminho_pdf}, vindo da lista de arquivos."""

        # backgrounds indexados pelo .txt, para o vínculo não depender do nome do .pdf
        self.arquivos_fullReport = {
            arquivo_txt: self.service.extrair_backgrounds(arquivo_pdf)
            for arquivo_txt, arquivo_pdf in fullreports_por_arquivo.items()
        }

        concentracoes = self.variaveis.resultados[0]
        areas_normalizadas = self.variaveis.resultados[1]

        area_padrao = None
        if self.variaveis.resultados and len(self.variaveis.resultados) > 4:
            area_padrao = self.variaveis.resultados[4]

        self.resultado_limite = self.limitedeteccao_model.calcular_limite_deteccao(
            self.arquivos_fullReport,
            self.arquivo_padrao,
            self.c_padrao,
            areas_normalizadas,
            concentracoes,
            area_padrao=area_padrao,
        )

        if hasattr(self, "limitedeteccao_model") and hasattr(self.limitedeteccao_model, "arredondamento"):
            self.limitedeteccao_model.arredondamento.atualizar_casas_padrao(self.c_padrao)

        self.variaveis.resultado_limite = self.resultado_limite

        return self.variaveis.resultado_limite

