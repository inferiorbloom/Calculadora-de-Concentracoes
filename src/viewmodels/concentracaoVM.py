import os
import tkinter.messagebox as messagebox
import customtkinter as ctk
from views.concentracaoView import ConcentracaoView, ConcentracaoResultadoView, ListaArquivosView
from models.concentracaoModel import ConcentracaoModel
from models.propagacaoErrosModel import PropagacaoErrosModel
from service.fileService import Service
from store.variaveis import Variaveis
from viewmodels.exportarVM import ExportarVM
from viewmodels.padraoVM import PadraoVM
from viewmodels.graficosVM import GraficosVM
from viewmodels.limiteDeteccaoVM import LimiteDeteccaoVM
from models.zscoreModel import ZScoreModel
from models.sensibilidadeModel import SensibilidadeModel



class ConcentracaoVM:
    def __init__(self,
                sidebar_frame,
                result_frame,
                arquivos_frame,
                dynamic_frame,
                mostrar_tela_inicial):

        self.sidebar_frame = sidebar_frame
        self.result_frame = result_frame
        self.arquivos_frame = arquivos_frame
        self.dynamic_frame = dynamic_frame
        self.mostrar_tela_inicial = mostrar_tela_inicial
        self.botoes_criados = False
        self.erro_model = PropagacaoErrosModel()

        # Variáveis para armazenar arquivos selecionados
        self.variaveis = Variaveis(sidebar_frame)
        self.arquivo_padrao = self.variaveis.lista_arquivo_padrao
        self.arquivos_amostras = self.variaveis.lista_arquivos
        self.resultado_limite = self.variaveis.resultado_limite

        # Chama os arquivos de service
        self.service = Service(sidebar_frame)

        # Chama o PadraoVM
        self.padrao_vm = PadraoVM(sidebar_frame, dynamic_frame, sidebar_frame)
        self.padrao_vm.padrao_view
        self.lista_padrao = self.padrao_vm.volta_padrao()

        # Chama os calculos de concentracao
        self.model = ConcentracaoModel()
        self.z_score_model = ZScoreModel()
        self.sensibilidade_model = SensibilidadeModel()

        # Chama a view dos botoes de calcular
        self.view = ConcentracaoView(sidebar_frame)
        self.view.pack(fill="x", padx=10, pady=10)

        # Chama o resultado
        self.resultados_view = ConcentracaoResultadoView(self.result_frame)
        self.resultados_view.pack(padx=10, pady=10, fill="both", expand=True)

        # Chama a lista de arquivos (marcação de Padrão e Amostras)
        self.lista_arquivos_view = ListaArquivosView(
            self.arquivos_frame, ao_alterar=self._atualizar_selecao, ao_escolher_pdf=self.escolher_fullreport
        )
        self.lista_arquivos_view.pack(fill="both", expand=True)

        # Chama a Exportacao
        self.export = ExportarVM(sidebar_frame, self.variaveis)
        #self.export.export

        # Chama os Graficos
        self.graficos = GraficosVM(sidebar_frame, self.variaveis)

        # Chama os Limite
        self.limite_deteccao = LimiteDeteccaoVM(sidebar_frame, self.service, self.variaveis)

    def botoes(self):
        if not self.botoes_criados:
        # impede recriação de botoes
        # Conectar os botões da View aos métodos da VM
            self.view.selecionar_arquivos.configure(command=self.selecionar_arquivos)
            self.view.calcular.configure(command=self.calcular)
            self.view.calcular_z_score.configure(command=self.calcular_z_score)
            self.view.calcular_sensibilidade.configure(command=self.calcular_sensibilidade)
            self.botoes_criados = True

    def selecionar_arquivos(self):
        arquivos = list(self.service.selecionar_arquivos())
        if arquivos:
            self.lista_arquivos_view.carregar(arquivos)
            self._atualizar_selecao()
        return arquivos

    def _atualizar_selecao(self):
        """Lê da lista qual arquivo é o padrão e quais são as amostras."""
        self.arquivo_padrao = self.lista_arquivos_view.arquivo_padrao()
        self.arquivos_amostras = self.lista_arquivos_view.arquivos_amostras()
        self._verificar_pronto()

    def escolher_fullreport(self, indice):
        """Vincula um FullReport (.pdf) ao arquivo da linha clicada na coluna LD."""
        caminho_pdf = self.service.selecionar_fullReport()
        if caminho_pdf:
            self.lista_arquivos_view.definir_pdf(indice, caminho_pdf)

    def _verificar_pronto(self):
        """Habilita o botão Calcular só quando houver padrão e amostras marcados."""
        pronto = bool(self.arquivos_amostras and self.arquivo_padrao)
        self.view.calcular.configure(state="normal" if pronto else "disabled")

    def calcular_limite_deteccao(self):
        """Calcula o LD das linhas com PDF vinculado; sem PDFs, limpa o resultado anterior."""
        fullreports = self.lista_arquivos_view.fullreports_por_arquivo()
        if not fullreports:
            self.variaveis.resultado_limite = {}
            return {}
        return self.limite_deteccao.calcula_resultado_limite(fullreports)

    def calcular(self):
        self.c_padrao = self.padrao_vm.c_padrao_lista_selecionado()
        self.resultado = self.model.calcular_concentracoes(self.arquivos_amostras,
                                                           self.arquivo_padrao,
                                                           self.c_padrao)
        if not self.resultado:
            return
        self.concentracoes = self.resultado[0]
        self.areas_normalizadas = self.resultado[1]
        self.fatores_normalizacao = self.resultado[2]
        self.erros_normalizados = self.resultado[3]
        self.area_padrao = self.resultado[4]
        self.erro_padrao = self.resultado[5]



        # calcula propagação de erro
        self.erros_concentracao, self.unidade_padrao = self.erro_model.calcular(
            self.concentracoes,
            self.areas_normalizadas,
            self.erros_normalizados,
            self.c_padrao,
            self.area_padrao,
            self.erro_padrao
        )



        # Atualiza Variaveis global
        self.variaveis.lista_arquivos = self.arquivos_amostras
        self.variaveis.lista_arquivo_padrao = self.arquivo_padrao
        self.variaveis.c_padrao = self.c_padrao

        from models.arredondamentoModel import ArredondamentoModel
        self.arredondamento = ArredondamentoModel()
        self.arredondamento.atualizar_casas_padrao(self.c_padrao)
        self.export.exportar_model.arredondamento = self.arredondamento
        self.export.exportar_model.aba_resultados.arredondamento = self.arredondamento
        self.variaveis.resultados = self.resultado
        self.variaveis.erros_concentracao = self.erros_concentracao
        self.variaveis.unidade_padrao = self.unidade_padrao

        # Atualiza a instância dentro de ExportarVM
        self.export.arquivos_amostras = self.variaveis.lista_arquivos
        self.export.resultados = self.variaveis.resultados
        if self.resultado:
            self.export.habilita_exporta_excel()
            self.graficos.habilita_graficos()
            self.limite_deteccao.habilita_limite(self.arquivo_padrao, self.c_padrao)
            self.calcular_limite_deteccao()
            self.view.calcular_z_score.configure(state="normal")
            self.view.calcular_sensibilidade.configure(state="normal")
        return self.resultados_view.mostrar_resultados(
            self.resultado[0],
            self.variaveis.resultado_limite,
            self.unidade_padrao,
            os.path.splitext(os.path.basename(self.arquivo_padrao))[0].strip(),
            erros=self.erros_concentracao,
            formatar_resultado=self.arredondamento.formatar_resultado,
        )

    def calcular_z_score(self):
        if not hasattr(self, "concentracoes") or not self.c_padrao:
            return {}

        self.z_score_resultado = self.z_score_model.calcular(
            self.concentracoes,
            self.c_padrao,
            self.erros_concentracao,
            self.arquivo_padrao,
        )
        self.variaveis.z_score_resultado = self.z_score_resultado
        self.resultados_view.mostrar_z_score(self.z_score_resultado)
        return self.z_score_resultado

    def calcular_sensibilidade(self):
        if not hasattr(self, "concentracoes"):
            return {}

        dialogo = ctk.CTkInputDialog(
            text="Informe o tempo de contagem (segundos):",
            title="Tempo de contagem",
        )
        tempo = dialogo.get_input()
        if tempo is None:
            return {}

        try:
            resultado = self.sensibilidade_model.calcular(
                self.concentracoes,
                self.areas_normalizadas,
                self.c_padrao,
                tempo,
            )
        except ValueError as erro:
            messagebox.showerror("Tempo inválido", str(erro))
            return {}

        self.sensibilidade_resultado = resultado
        self.variaveis.sensibilidade_resultado = resultado
        self.resultados_view.mostrar_sensibilidade(resultado)
        return resultado
