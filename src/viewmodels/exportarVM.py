from views.exportarView import ExportarView, AbasExportarDialog
from models.exportarModel import ExportarModel
from models.configModel import (
    carregar_abas_exportar,
    carregar_ultimo_diretorio,
    salvar_abas_exportar,
    salvar_ultimo_diretorio,
)
from tkinter import filedialog

class ExportarVM:
    def __init__(self, master, variaveis):

        self.variaveis = variaveis

        self.exportar_model = ExportarModel()

        # abas escolhidas na engrenagem; sem escolha salva, exporta todas
        salvas = carregar_abas_exportar()
        todas = ExportarModel.TODAS_ABAS
        self.abas_exportar = [a for a in todas if a in salvas] if salvas else list(todas)
        if not self.abas_exportar:
            self.abas_exportar = list(todas)

        self.export = ExportarView(master)
        self.export.pack(fill="x", padx=10, pady=10)
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
            initialfile="amostras.xlsx",
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
        )
        return self.exporta_excel_var
