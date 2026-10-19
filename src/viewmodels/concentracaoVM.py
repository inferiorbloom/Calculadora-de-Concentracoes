import os
import tkinter.messagebox as messagebox
import customtkinter as ctk
from views.concentracaoView import ConcentracaoView, ResultadosPadroesView, ListaArquivosView
from models.concentracaoModel import ConcentracaoModel
from models.propagacaoErrosModel import PropagacaoErrosModel
from models.resultadoPadraoModel import ResultadoPadrao
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
        self.padroes_marcados = []  # [(caminho do arquivo padrão, nome do padrão certificado)]
        self.arquivos_amostras = self.variaveis.lista_arquivos
        self.resultados_por_padrao = []

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

        # Chama o resultado (um conjunto de abas para cada padrão)
        self.resultados_view = ResultadosPadroesView(self.result_frame)
        self.resultados_view.pack(padx=10, pady=10, fill="both", expand=True)

        # Chama a lista de arquivos (marcação de Padrão, padrão certificado e Amostras)
        self.lista_arquivos_view = ListaArquivosView(
            self.arquivos_frame,
            ao_alterar=self._atualizar_selecao,
            ao_escolher_pdf=self.escolher_fullreport,
            nomes_padroes=self.padrao_vm.nomes_padroes(),
        )
        self.lista_arquivos_view.pack(fill="both", expand=True)
        self.padrao_vm.ao_atualizar_padroes(self.lista_arquivos_view.atualizar_padroes)

        # Chama a Exportacao
        self.export = ExportarVM(sidebar_frame, self.variaveis)

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
            self.botoes_criados = True

    def selecionar_arquivos(self):
        arquivos = list(self.service.selecionar_arquivos())
        if arquivos:
            self.lista_arquivos_view.carregar(arquivos)
            self._atualizar_selecao()
        return arquivos

    def _atualizar_selecao(self):
        """Lê da lista quais arquivos são padrões (com o padrão certificado de cada um) e quais são amostras."""
        self.padroes_marcados = self.lista_arquivos_view.padroes_selecionados()
        self.arquivos_amostras = self.lista_arquivos_view.arquivos_amostras()
        self._verificar_pronto()

    def escolher_fullreport(self, indice):
        """Vincula um FullReport (.pdf) ao arquivo da linha clicada na coluna LD."""
        caminho_pdf = self.service.selecionar_fullReport()
        if caminho_pdf:
            self.lista_arquivos_view.definir_pdf(indice, caminho_pdf)

    def _verificar_pronto(self):
        """Habilita o Calcular só com amostras e pelo menos um padrão, todos com padrão certificado escolhido."""
        pronto = bool(
            self.arquivos_amostras
            and self.padroes_marcados
            and all(self.padrao_vm.buscar_padrao(nome) for _, nome in self.padroes_marcados)
        )
        self.view.calcular.configure(state="normal" if pronto else "disabled")

    @staticmethod
    def _nome_unico(caminho, usados):
        """Nome do arquivo sem extensão; se já existir (mesmo nome em pastas diferentes), ganha um sufixo."""
        base = os.path.splitext(os.path.basename(caminho))[0].strip()
        nome, n = base, 2
        while nome in usados:
            nome, n = f"{base} ({n})", n + 1
        return nome

    def _calcular_para_padrao(self, nome, arquivo_padrao, c_padrao, backgrounds):
        """Executa todo o cálculo com UM padrão e devolve um ResultadoPadrao (ou None)."""
        resultado = self.model.calcular_concentracoes(self.arquivos_amostras, arquivo_padrao, c_padrao)
        if not resultado:
            return None

        resultado_padrao = ResultadoPadrao(nome, arquivo_padrao, c_padrao, *resultado)

        # propagação de erro
        resultado_padrao.erros_concentracao, resultado_padrao.unidade_padrao = self.erro_model.calcular(
            resultado_padrao.concentracoes,
            resultado_padrao.areas_normalizadas,
            resultado_padrao.erros_normalizados,
            c_padrao,
            resultado_padrao.area_padrao,
            resultado_padrao.erro_padrao,
        )

        # arredondamento próprio: as casas decimais dependem do padrão certificado
        resultado_padrao.arredondamento.atualizar_casas_padrao(c_padrao)

        # LD: só das linhas com PDF vinculado
        if backgrounds:
            self.limite_deteccao.calcula_resultado_limite(backgrounds, resultado_padrao)

        return resultado_padrao

    def calcular(self):
        fullreports = self.lista_arquivos_view.fullreports_por_arquivo()
        backgrounds = self.limite_deteccao.extrair_backgrounds(fullreports) if fullreports else {}

        resultados_por_padrao = []
        for arquivo_padrao, nome_certificado in self.padroes_marcados:
            c_padrao = self.padrao_vm.buscar_padrao(nome_certificado)
            if not c_padrao:
                continue
            nome = self._nome_unico(arquivo_padrao, {r.nome for r in resultados_por_padrao})
            resultado_padrao = self._calcular_para_padrao(nome, arquivo_padrao, c_padrao, backgrounds)
            if resultado_padrao:
                resultados_por_padrao.append(resultado_padrao)

        if not resultados_por_padrao:
            return

        self.resultados_por_padrao = resultados_por_padrao

        # Atualiza Variaveis global
        self.variaveis.lista_arquivos = self.arquivos_amostras
        self.variaveis.resultados_por_padrao = resultados_por_padrao

        self.export.habilita_exporta_excel()
        self.graficos.habilita_graficos()

        self.resultados_view.mostrar_resultados(resultados_por_padrao)

        # cálculos extras marcados na lista; um erro em um deles não pode passar despercebido
        extras = [
            (self.view.var_z_score.get(), "Z'-Score", self.calcular_z_score),
            (self.view.var_sensibilidade.get(), "Sensibilidade", self.calcular_sensibilidade),
        ]
        for marcado, nome, calcular_extra in extras:
            if not marcado:
                continue
            try:
                calcular_extra()
            except Exception as erro:
                messagebox.showerror(nome, f"Não foi possível calcular {nome}:\n{erro}")
        return resultados_por_padrao

    def calcular_z_score(self):
        if not self.resultados_por_padrao:
            return {}

        for resultado_padrao in self.resultados_por_padrao:
            resultado_padrao.z_score_resultado = self.z_score_model.calcular(
                resultado_padrao.concentracoes,
                resultado_padrao.c_padrao,
                resultado_padrao.erros_concentracao,
                resultado_padrao.arquivo_padrao,
            )
        vazios = [r.rotulo for r in self.resultados_por_padrao if not r.z_score_resultado]
        if vazios:
            messagebox.showwarning(
                "Z'-Score",
                "Nenhum Z'-Score calculado para: " + ", ".join(vazios) + ".\n\n"
                "É preciso pelo menos 2 amostras (sem contar o próprio padrão) com elementos "
                "que tenham valor e erro no padrão certificado.",
            )
        self.resultados_view.mostrar_z_score(self.resultados_por_padrao)
        return {r.nome: r.z_score_resultado for r in self.resultados_por_padrao}

    def calcular_sensibilidade(self):
        if not self.resultados_por_padrao:
            return {}

        dialogo = ctk.CTkInputDialog(
            text="Informe o tempo de contagem (segundos):",
            title="Tempo de contagem",
        )
        tempo = dialogo.get_input()
        if tempo is None:
            return {}

        # calcula tudo antes de gravar, para um erro não deixar os padrões com resultados de tempos diferentes
        try:
            calculados = [
                self.sensibilidade_model.calcular(
                    r.concentracoes,
                    r.areas_normalizadas,
                    r.c_padrao,
                    tempo,
                )
                for r in self.resultados_por_padrao
            ]
        except ValueError as erro:
            messagebox.showerror("Tempo inválido", str(erro))
            return {}

        for resultado_padrao, resultado in zip(self.resultados_por_padrao, calculados):
            resultado_padrao.sensibilidade_resultado = resultado
        self.resultados_view.mostrar_sensibilidade(self.resultados_por_padrao)
        return {r.nome: r.sensibilidade_resultado for r in self.resultados_por_padrao}
