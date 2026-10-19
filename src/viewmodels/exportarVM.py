from views.exportarView import ExportarView, AbasExportarDialog, ExportarTodosView
from models.exportarModel import ExportarModel
from models.configModel import (
    carregar_abas_exportar,
    carregar_ultimo_diretorio,
    salvar_abas_exportar,
    salvar_ultimo_diretorio,
)
from tkinter import filedialog

class ExportarVM:
    def __init__(self, master, variaveis, nome_planilha="amostras.xlsx"):

        self.variaveis = variaveis
        self.nome_planilha = nome_planilha  # sugestão de nome no "Salvar como" (ex.: amostras_Ag.xlsx)

        self.exportar_model = ExportarModel()

        # abas escolhidas na engrenagem; sem escolha salva, exporta todas
        salvas = carregar_abas_exportar()
        todas = ExportarModel.TODAS_ABAS
        self.abas_exportar = [a for a in todas if a in salvas] if salvas else list(todas)
        if not self.abas_exportar:
            self.abas_exportar = list(todas)

        self.export = ExportarView(master)
        self.export.pack(fill="x")
        self.export.exportar_botao.configure(command=self.exporta_excel)
        self.export.configurar_botao.configure(command=self.configurar_abas)

    def habilita_exporta_excel(self):
        """Habilita o botão Exportar"""
        self.export.exportar_botao.configure(state="normal")

    def configurar_abas(self):
        """Abre a janela da engrenagem para escolher as abas exportadas."""
        AbasExportarDialog(self.export, ExportarModel.TODAS_ABAS, self.abas_exportar, self._salvar_abas)

    def _salvar_abas(self, abas):
        self.abas_exportar = list(abas)
        salvar_abas_exportar(self.abas_exportar)

    def exporta_excel(self):
        # Abre a caixa de diálogo para o usuário escolher onde salvar o arquivo Excel
        initialdir = carregar_ultimo_diretorio() or ""
        caminho_arquivo = filedialog.asksaveasfilename(
            title="Salvar planilha Excel",
            defaultextension=".xlsx",
            filetypes=[
                ("Planilhas Excel", "*.xlsx"),
                ("Todos os arquivos", "*.*")
            ],
            initialfile=self.nome_planilha,
            initialdir=initialdir,
        )

        # usuário cancelou
        if not caminho_arquivo:
            return

        salvar_ultimo_diretorio(caminho_arquivo)

        # Obtem as variáveis atualizadas no fluxo principal (um ResultadoPadrao por padrão)
        self.exporta_excel_var = self.exportar_model.exportar_para_excel(
            self.variaveis.lista_arquivos,
            self.variaveis.resultados_por_padrao,
            caminho_arquivo,
            abas_exportar=self.abas_exportar,
            nomes_amostras=self.variaveis.nomes_amostras,
        )
        return self.exporta_excel_var


class ExportarTodosVM:
    """
    Aba lateral "Exportar". obter_resultados() devolve {alvo: lista de ResultadoPadrao}
    (lista vazia nos alvos ainda não calculados); obter_nomes() devolve {alvo: {código: nome}}.
    """

    def __init__(self, master, alvos, obter_resultados, obter_nomes):
        self.alvos = list(alvos)
        self.obter_resultados = obter_resultados
        self.obter_nomes = obter_nomes
        self.exportar_model = ExportarModel()

        self.view = ExportarTodosView(master, self.alvos)
        self.view.exportar_botao.configure(command=self.exporta_excel)
        self.atualizar()

    def atualizar(self):
        """Mostra quais alvos já foram calculados (chamado sempre que a aba é aberta)."""
        resultados = self.obter_resultados()
        for alvo in self.alvos:
            padroes = resultados.get(alvo) or []
            if padroes:
                texto = f"{len(padroes)} padrão" if len(padroes) == 1 else f"{len(padroes)} padrões"
                self.view.mostrar_status(alvo, f"Calculado · {texto}", True)
            else:
                self.view.mostrar_status(alvo, "Não calculado · fica fora da planilha", False)
        algum = any(resultados.get(alvo) for alvo in self.alvos)
        self.view.exportar_botao.configure(state="normal" if algum else "disabled")

    def exporta_excel(self):
        resultados = {alvo: self.obter_resultados().get(alvo) or [] for alvo in self.alvos}
        if not any(resultados.values()):
            return None

        caminho_arquivo = filedialog.asksaveasfilename(
            title="Salvar planilha Excel",
            defaultextension=".xlsx",
            filetypes=[
                ("Planilhas Excel", "*.xlsx"),
                ("Todos os arquivos", "*.*")
            ],
            initialfile="amostras_todos_alvos.xlsx",
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho_arquivo:
            return None

        salvar_ultimo_diretorio(caminho_arquivo)
        return self.exportar_model.exportar_todos_alvos(resultados, caminho_arquivo, self.obter_nomes())
