import os
from tkinter import filedialog, messagebox

from models.configModel import carregar_formato_imagem, carregar_ultimo_diretorio, salvar_ultimo_diretorio
from models.graficosModel import salvar_figura
from models.multivariadaModel import MultivariadaModel
from views.multivariadaView import MultivariadaJanela

NOMES_FIGURAS = {"biplot": "PCA biplot", "correlacao": "correlacao rho p", "hca": "HCA dendrograma"}


class MultivariadaVM:
    """
    "Análise multivariada" na aba lateral Análise estatística: PCA, correlação e HCA de um alvo já calculado.
    obter_resultados(): {alvo: lista de ResultadoPadrao}; obter_nomes(): {alvo: {código: nome}}.
    """

    def __init__(self, botao, obter_resultados, obter_nomes):
        self.botao = botao
        self.obter_resultados = obter_resultados
        self.obter_nomes = obter_nomes
        self.model = MultivariadaModel()
        self.resultado = None
        self.titulo = ""
        self.botao.configure(command=self.abrir)
        self.atualizar()

    def _opcoes(self):
        return {alvo: [r.rotulo for r in lista] for alvo, lista in self.obter_resultados().items() if lista}

    def atualizar(self):
        self.botao.configure(state="normal" if self._opcoes() else "disabled")

    def abrir(self):
        opcoes = self._opcoes()
        if not opcoes:
            return None
        return MultivariadaJanela(
            self.botao, opcoes, self.calcular, self.figura, self.exportar_imagens, self.exportar_excel,
        )

    def calcular(self, alvo, rotulo_padrao, modo):
        """Refaz a análise; devolve o resumo em texto. Erros sobem com a mensagem para a janela mostrar."""
        resultados = self.obter_resultados().get(alvo) or []
        r = next((r for r in resultados if r.rotulo == rotulo_padrao), None)
        if r is None:
            raise ValueError("Escolha um alvo e um padrão.")
        self.resultado = None
        dados = self.model.montar_dados(r, resultados, alvo, self.obter_nomes().get(alvo), modo)
        self.resultado = self.model.analisar(dados)
        self.titulo = f"Alvo {alvo} · padrão {r.rotulo}"
        return self.model.resumo(self.resultado)

    def figura(self, aba, tema):
        criar = {
            "biplot": self.model.figura_biplot,
            "correlacao": self.model.figura_correlacao,
            "hca": self.model.figura_dendrograma,
        }[aba]
        return criar(self.resultado, self.titulo, tema)

    def exportar_imagens(self, janela):
        """Os três gráficos (tema claro) numa pasta, no formato escolhido."""
        if self.resultado is None:
            return
        pasta = filedialog.askdirectory(
            parent=janela, title="Pasta para os gráficos", initialdir=carregar_ultimo_diretorio() or "",
        )
        if not pasta:
            return
        salvar_ultimo_diretorio(pasta)
        formato = carregar_formato_imagem()
        prefixo = self.titulo.replace(" · ", " - ").replace("/", "-")
        gravados = [
            salvar_figura(self.figura(aba, "claro"), os.path.join(pasta, f"{prefixo} - {nome}"), formato)
            for aba, nome in NOMES_FIGURAS.items()
        ]
        messagebox.showinfo("Gráficos exportados", f"{len(gravados)} imagens salvas em:\n{pasta}", parent=janela)

    def exportar_excel(self, janela):
        if self.resultado is None:
            return
        caminho = filedialog.asksaveasfilename(
            parent=janela, title="Salvar análise multivariada", defaultextension=".xlsx",
            filetypes=[("Planilhas Excel", "*.xlsx")], initialfile="analise_multivariada.xlsx",
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho:
            return
        salvar_ultimo_diretorio(caminho)
        try:
            self.model.exportar_excel(caminho, self.resultado, self.titulo)
        except OSError as erro:
            messagebox.showerror("Exportar Excel", f"Não foi possível salvar (o arquivo está aberto?):\n{erro}",
                                 parent=janela)
            return
        messagebox.showinfo("Excel exportado", f"Salvo em:\n{caminho}", parent=janela)
