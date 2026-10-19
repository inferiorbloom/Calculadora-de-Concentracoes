from tkinter import filedialog, messagebox

from views.graficosView import GraficosView, GraficosJanela
from models.graficosModel import GraficosModel, TIPOS
from models.coresElementosModel import carregar_cores
from models.configModel import carregar_tipo_grafico, carregar_ultimo_diretorio, salvar_tipo_grafico


class GraficosVM:
    def __init__(self, master, variaveis):

        self.variaveis = variaveis

        self.graficos_view = GraficosView(master)
        self.graficos_view.pack(fill="x", padx=10, pady=10)
        self.graficos_view.botao_grafico.configure(command=self.faz_graficos)

        self.graficos_model = GraficosModel()
        # vale enquanto o programa estiver aberto (a escolha de cada amostra fica no ResultadoPadrao)
        tipo = carregar_tipo_grafico()
        self.estado = {"automatico": False, "tipo": tipo if tipo in TIPOS else "anel", "base": "concentracao"}

    def habilita_graficos(self):
        """Habilita o botão Graficos"""
        self.graficos_view.botao_grafico.configure(state="normal")

    def faz_graficos(self):
        resultados = list(self.variaveis.resultados_por_padrao)
        if not resultados:
            return None
        # relê as cores a cada abertura: trocar o arquivo de cores não exige reiniciar o programa
        self.graficos_model.cores = carregar_cores()
        return GraficosJanela(
            self.graficos_view, resultados, self.graficos_model, self.estado, self.exportar_imagens,
            ao_trocar_tipo=salvar_tipo_grafico,
        )

    def exportar_imagens(self, janela):
        """Grava as pizzas de todas as amostras (de todos os padrões), cada uma com o traço escolhido."""
        pasta = filedialog.askdirectory(
            parent=janela, title="Escolha a pasta para salvar os gráficos", initialdir=carregar_ultimo_diretorio() or "",
        )
        if not pasta:
            return

        resultados = self.variaveis.resultados_por_padrao
        varios = len(resultados) > 1
        itens = []
        for r in resultados:
            for amostra in self.graficos_model.amostras(r):
                valores = self.graficos_model.valores_da_amostra(r, amostra, self.estado["base"])
                n = self.graficos_model.n_traco_da_amostra(
                    r, amostra, valores, self.estado["automatico"], self.estado["base"]
                )
                itens.append((r.rotulo if varios else None, amostra, valores, n, r.nome))

        gravados = self.graficos_model.exportar(pasta, itens, self.estado["tipo"], self.estado["base"])
        messagebox.showinfo(
            "Gráficos exportados",
            f"{len(gravados)} imagens salvas em:\n{pasta}"
            + ("\n\nCom vários padrões, cada padrão ganhou a sua subpasta." if varios else ""),
            parent=janela,
        )
