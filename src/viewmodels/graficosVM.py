import threading
from tkinter import TclError, filedialog, messagebox

from views.graficosView import GraficosView, GraficosJanela
from models.graficosModel import GraficosModel, TIPOS
from models.coresElementosModel import carregar_cores
from models.configModel import (
    carregar_formato_imagem,
    carregar_tipo_grafico,
    carregar_ultimo_diretorio,
    salvar_tipo_grafico,
)


class GraficosVM:
    def __init__(self, master, variaveis, alvo=None, obter_resultados=None):
        """
        obter_resultados(): os ResultadoPadrao dos gráficos (os calculados ou, antes do Calcular, só normalizados).
        Sem ele, usa os calculados (variaveis.resultados_por_padrao).
        """
        self.variaveis = variaveis
        self.obter_resultados = obter_resultados or (lambda: list(self.variaveis.resultados_por_padrao))
        self.resultados = []  # os da janela aberta (a exportação usa os mesmos)

        self.graficos_view = GraficosView(master)
        self.graficos_view.pack(fill="x")
        self.graficos_view.botao_grafico.configure(command=self.faz_graficos)

        self.graficos_model = GraficosModel(excluidos={alvo} if alvo else ())
        # vale enquanto o programa estiver aberto (a escolha de cada amostra fica no ResultadoPadrao)
        tipo = carregar_tipo_grafico()
        self.estado = {
            "automatico": False, "tipo": tipo if tipo in TIPOS else "anel", "base": "concentracao", "avancado": False,
        }

    def habilita_graficos(self, habilitar=True):
        """Habilita (ou desabilita) o botão Graficos"""
        self.graficos_view.botao_grafico.configure(state="normal" if habilitar else "disabled")

    def faz_graficos(self):
        resultados = self.obter_resultados()
        if not resultados:
            return None
        self.resultados = resultados
        tem_concentracao = any(r.concentracoes for r in resultados)
        if not tem_concentracao:
            self.estado["base"] = "area"  # sem Calcular, só há a área normalizada
        # relê as cores a cada abertura: trocar o arquivo de cores não exige reiniciar o programa
        self.graficos_model.cores = carregar_cores()
        return GraficosJanela(
            self.graficos_view, resultados, self.graficos_model, self.estado, self.exportar_imagens,
            ao_trocar_tipo=salvar_tipo_grafico,
            nomes=self.variaveis.nomes_amostras, tem_concentracao=tem_concentracao,
        )

    def exportar_imagens(self, janela):
        """
        Grava as pizzas de todas as amostras (de todos os padrões), cada uma com o traço escolhido.
        As imagens são desenhadas numa thread, para a janela não travar; o botão mostra o andamento.
        """
        pasta = filedialog.askdirectory(
            parent=janela, title="Escolha a pasta para salvar os gráficos", initialdir=carregar_ultimo_diretorio() or "",
        )
        if not pasta:
            return

        resultados = self.resultados
        varios = len(resultados) > 1
        itens = []
        for r in resultados:
            for amostra in self.graficos_model.amostras(r):
                valores = self.graficos_model.valores_da_amostra(r, amostra, self.estado["base"])
                n = self.graficos_model.n_traco_da_amostra(
                    r, amostra, valores, self.estado["automatico"], self.estado["base"]
                )
                excluidos = self.graficos_model.excluidos_da_amostra(r, amostra, self.estado["base"])
                # cópia: a janela continua aberta e pode mudar a seleção durante a exportação
                excluidos = {grafico: set(elementos) for grafico, elementos in excluidos.items()}
                itens.append((r.rotulo if varios else None, amostra, valores, n, r.nome, excluidos))

        andamento = {"feitos": 0, "total": len(itens), "gravados": None, "erro": None}

        def progresso(feitos, total):
            andamento["feitos"] = feitos

        def trabalhar():
            try:
                andamento["gravados"] = self.graficos_model.exportar(
                    pasta, itens, self.estado["tipo"], self.estado["base"], self.variaveis.nomes_amostras,
                    carregar_formato_imagem(), progresso,
                )
            except Exception as erro:  # mostrado na janela, na thread principal
                andamento["erro"] = erro

        thread = threading.Thread(target=trabalhar, daemon=True)
        botao = janela.botao_exportar
        botao.configure(state="disabled")
        thread.start()
        self._acompanhar(janela, botao, thread, andamento, pasta, varios)

    def _acompanhar(self, janela, botao, thread, andamento, pasta, varios):
        """Atualiza o botão a cada 100 ms até a thread terminar; depois avisa o resultado."""
        try:
            if thread.is_alive():
                botao.configure(text=f"Exportando {andamento['feitos']}/{andamento['total']}…")
                janela.after(100, self._acompanhar, janela, botao, thread, andamento, pasta, varios)
                return
            botao.configure(text="Exportar imagens", state="normal")
        except TclError:
            return  # a janela foi fechada: a exportação termina sozinha, sem aviso
        if andamento["erro"] is not None:
            messagebox.showerror("Gráficos", f"Não foi possível exportar os gráficos:\n{andamento['erro']}",
                                 parent=janela)
            return
        messagebox.showinfo(
            "Gráficos exportados",
            f"{len(andamento['gravados'])} imagens salvas em:\n{pasta}"
            + ("\n\nCom vários padrões, cada padrão ganhou a sua subpasta." if varios else ""),
            parent=janela,
        )
