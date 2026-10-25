from tkinter import filedialog, messagebox

from models.comparacaoModel import ESTILOS, ComparacaoModel
from models.configModel import carregar_estilo_comparacao, carregar_ultimo_diretorio, salvar_estilo_comparacao
from views.comparacaoView import AnaliseEstatisticaView, ComparacaoJanela, CompararPadroesView


class _ComparacaoBase:
    """O que as duas comparações dividem: o estilo (Barras/Linhas) lembrado e a exportação das imagens."""

    def __init__(self):
        self.model = ComparacaoModel()
        estilo = carregar_estilo_comparacao()
        self.estado = {"estilo": estilo if estilo in ESTILOS else "barras"}
        self.comparacao = None

    def _abrir(self, master, titulo, comparacao):
        if not self.model.elementos(comparacao):
            messagebox.showinfo(titulo, "Nenhum elemento com concentração para comparar.", parent=master)
            return None
        self.comparacao = comparacao
        return ComparacaoJanela(
            master, titulo, comparacao, self.model, self.estado, self.exportar_imagens,
            ao_trocar_estilo=salvar_estilo_comparacao,
        )

    def exportar_imagens(self, janela):
        """Grava um gráfico por elemento, no estilo escolhido na janela."""
        pasta = filedialog.askdirectory(
            parent=janela, title="Escolha a pasta para salvar os gráficos", initialdir=carregar_ultimo_diretorio() or "",
        )
        if not pasta:
            return
        gravados = self.model.exportar(pasta, self.comparacao, self.estado["estilo"])
        messagebox.showinfo("Gráficos exportados", f"{len(gravados)} imagens salvas em:\n{pasta}", parent=janela)


class CompararPadroesVM(_ComparacaoBase):
    """
    1ª situação, dentro da aba de um alvo: os resultados de cada padrão nas mesmas amostras.
    obter_resultados(): lista de ResultadoPadrao do último Calcular; obter_nomes(): {código: nome} da ficha.
    """

    def __init__(self, master, alvo, obter_resultados, obter_nomes):
        super().__init__()
        self.alvo = alvo
        self.obter_resultados = obter_resultados
        self.obter_nomes = obter_nomes
        self.view = CompararPadroesView(master)
        self.view.pack(fill="x")
        self.view.botao.configure(command=self.abrir)

    def habilita(self, habilitar=True):
        self.view.botao.configure(state="normal" if habilitar else "disabled")

    def abrir(self):
        resultados = self.obter_resultados()
        if len(resultados) < 2:
            return None
        comparacao = self.model.entre_padroes(resultados, self.alvo, self.obter_nomes())
        titulo = f"Comparar padrões · {self.alvo}" if self.alvo else "Comparar padrões"
        return self._abrir(self.view, titulo, comparacao)


class CompararAlvosVM(_ComparacaoBase):
    """
    2ª situação, na aba lateral "Análise estatística": os alvos já calculados, lado a lado.
    obter_resultados(): {alvo: lista de ResultadoPadrao}; obter_nomes(): {alvo: {código: nome}}.
    """

    def __init__(self, master, alvos, obter_resultados, obter_nomes):
        super().__init__()
        self.alvos = list(alvos)
        self.obter_resultados = obter_resultados
        self.obter_nomes = obter_nomes
        self.view = AnaliseEstatisticaView(master, self.alvos)
        self.view.botao.configure(command=self.abrir)
        self.atualizar()

    def atualizar(self):
        """Mostra quais alvos já foram calculados (chamado sempre que a aba é aberta)."""
        resultados = self.obter_resultados()
        for alvo in self.alvos:
            padroes = resultados.get(alvo) or []
            if padroes:
                nomes = ", ".join(r.nome_certificado or r.nome for r in padroes)
                self.view.mostrar_status(alvo, f"Calculado · {nomes}", True)
            else:
                self.view.mostrar_status(alvo, "Não calculado · fica fora dos gráficos", False)
        calculados = sum(1 for alvo in self.alvos if resultados.get(alvo))
        self.view.botao.configure(state="normal" if calculados >= 2 else "disabled")

    def abrir(self):
        resultados = {alvo: lista for alvo, lista in self.obter_resultados().items() if lista}
        if len(resultados) < 2:
            return None
        comparacao = self.model.entre_alvos(resultados, self.obter_nomes())
        return self._abrir(self.view, "Comparar alvos", comparacao)
