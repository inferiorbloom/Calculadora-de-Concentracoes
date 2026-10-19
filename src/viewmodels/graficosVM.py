from views.graficosView import GraficosView
from models.graficosModel import GraficosModel


class GraficosVM:
    def __init__(self, master, variaveis):

        self.variaveis = variaveis

        self.graficos_view = GraficosView(master)
        self.graficos_view.pack(fill="x", padx=10, pady=10)
        self.graficos_view.botao_grafico.configure(command=self.faz_graficos)

        self.graficos_model = GraficosModel()

    def habilita_graficos(self):
        """Habilita o botão Graficos"""
        self.graficos_view.botao_grafico.configure(state="normal")

    def faz_graficos(self):
        # self.variaveis.verificar_estado()
        resultados_por_padrao = {r.rotulo: r.resultados for r in self.variaveis.resultados_por_padrao}
        if not resultados_por_padrao:
            return None
        self.graficos_var = self.graficos_model.graficos(resultados_por_padrao)
        return self.graficos_var
