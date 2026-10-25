import os
import tkinter.messagebox as messagebox
import customtkinter as ctk
from views.concentracaoView import ConcentracaoView, ResultadosPadroesView, ListaArquivosView
from models.concentracaoModel import ConcentracaoModel
from models.propagacaoErrosModel import PropagacaoErrosModel
from models.resultadoPadraoModel import ResultadoPadrao
from models.leitorArquivoModel import ArquivoInvalidoError, nome_amostra
from service.logErros import mensagem_erro_inesperado
from service.fileService import Service
from store.variaveis import Variaveis
from viewmodels.exportarVM import ExportarVM
from viewmodels.fichaVM import FichaVM
from viewmodels.padraoVM import PadraoVM
from viewmodels.graficosVM import GraficosVM
from viewmodels.comparacaoVM import CompararPadroesVM
from viewmodels.limiteDeteccaoVM import LimiteDeteccaoVM
from models.zscoreModel import ZScoreModel
from models.sensibilidadeModel import SensibilidadeModel



class ConcentracaoVM:
    def __init__(self,
                sidebar_frame,
                result_frame,
                arquivos_frame,
                dynamic_frame,
                mostrar_tela_inicial,
                alvo=None):
        """alvo: "Ag", "Au" ou "Rh" quando houver uma calculadora por aba de alvo."""

        self.alvo = alvo
        # chamados pela tela principal: ao_calcular(n_amostras) e ao_editar_padroes(vm, lista)
        self.ao_calcular = None
        self.ao_editar_padroes = None
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
        # o que os gráficos mostram: os calculados ou, antes do Calcular, só as áreas normalizadas
        self.resultados_graficos = []
        self._selecao_calculada = None  # seleção da lista usada no último Calcular
        self._selecao_graficos = None  # e na última normalização para os gráficos

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
        self.padrao_vm.padrao_view.ao_atualizar = self._padroes_editados

        # Exportar e Gráficos dividem a mesma caixa no menu
        self.caixa_saidas = ctk.CTkFrame(sidebar_frame)
        self.caixa_saidas.pack(fill="x", padx=10, pady=10)

        # Chama a Exportacao
        nome_planilha = f"amostras_{alvo}.xlsx" if alvo else "amostras.xlsx"
        self.export = ExportarVM(self.caixa_saidas, self.variaveis, nome_planilha)

        # Chama os Graficos
        # o alvo do tubo fica fora dos gráficos
        self.graficos = GraficosVM(self.caixa_saidas, self.variaveis, alvo, obter_resultados=self._resultados_graficos)

        # Comparar padrões: os mesmos elementos calculados com cada padrão (precisa de 2 ou mais)
        self.comparar_padroes = CompararPadroesVM(
            self.caixa_saidas, alvo, lambda: list(self.resultados_por_padrao), lambda: self.variaveis.nomes_amostras
        )

        # Chama os Limite
        self.limite_deteccao = LimiteDeteccaoVM(sidebar_frame, self.service, self.variaveis)

        # Ficha de informação: nomes das amostras ao lado do código
        self.ficha = FichaVM(
            sidebar_frame,
            self.variaveis,
            lambda: [caminho for caminho, _, _ in self.lista_arquivos_view.linhas],
            self._nomes_alterados,
        )

    def _nomes_alterados(self):
        """Nomes das amostras lidos da ficha ou editados: atualiza a lista de arquivos e as tabelas."""
        nomes = self.variaveis.nomes_amostras
        self.lista_arquivos_view.mostrar_nomes(nomes)
        self.resultados_view.mostrar_nomes(nomes)

    def _padroes_editados(self, lista):
        """Padrões salvos/excluídos no Gerenciar Padrões desta aba: atualiza aqui e avisa as outras abas."""
        self.receber_padroes(lista)
        if self.ao_editar_padroes:
            self.ao_editar_padroes(self, lista)

    def receber_padroes(self, lista):
        """Nova lista de padrões certificados (editada aqui ou em outra aba de alvo)."""
        self.padrao_vm.padrao_view.lista_dados = list(lista)
        self.padrao_vm.variaveis.padroes = list(lista)
        self.lista_arquivos_view.atualizar_padroes([item["nome"] for item in lista])

    def botoes(self):
        if not self.botoes_criados:
        # impede recriação de botoes
        # Conectar os botões da View aos métodos da VM
            self.view.selecionar_arquivos.configure(command=self.selecionar_arquivos)
            self.view.calcular.configure(command=self.calcular)
            self.view.ler_ficha.configure(command=self.ficha.ler_ficha)
            self.view.editar_nomes.configure(command=self.ficha.editar_nomes)
            self.botoes_criados = True

    def selecionar_arquivos(self):
        arquivos = list(self.service.selecionar_arquivos())
        if arquivos and not self._nomes_repetidos(arquivos):
            self.lista_arquivos_view.carregar(arquivos, self.variaveis.nomes_amostras)
            self._atualizar_selecao()
        return arquivos

    @staticmethod
    def _nomes_repetidos(arquivos):
        """
        Cada arquivo é identificado pelo nome (sem a pasta) em todo o programa. Dois arquivos com o
        mesmo nome misturariam áreas, erros e LD, então a seleção é recusada com uma explicação.
        """
        por_nome = {}
        for caminho in arquivos:
            por_nome.setdefault(nome_amostra(caminho), []).append(caminho)
        repetidos = {nome: caminhos for nome, caminhos in por_nome.items() if len(caminhos) > 1}
        if not repetidos:
            return False

        detalhes = "\n\n".join(
            f"{nome}:\n" + "\n".join(f"  • {c}" for c in caminhos) for nome, caminhos in repetidos.items()
        )
        messagebox.showerror(
            "Arquivos com o mesmo nome",
            "Há arquivos diferentes com o mesmo nome. Os resultados de um sobrescreveriam os do outro.\n\n"
            f"{detalhes}\n\nRenomeie um deles (ex.: acrescente a data) e selecione de novo.",
        )
        return True

    def _atualizar_selecao(self):
        """Lê da lista quais arquivos são padrões (com o padrão certificado de cada um) e quais são amostras."""
        self.padroes_marcados = self.lista_arquivos_view.padroes_selecionados()
        self.arquivos_amostras = self.lista_arquivos_view.arquivos_amostras()
        self._verificar_pronto()

    def escolher_fullreport(self, indice):
        """Vincula um FullReport (.pdf) ao arquivo da linha clicada na coluna LD."""
        caminho_pdf = self.service.selecionar_fullReport()
        if not caminho_pdf:
            return
        caminho_txt = self.lista_arquivos_view.linhas[indice][0]
        if nome_amostra(caminho_pdf) != nome_amostra(caminho_txt):
            vincular = messagebox.askyesno(
                "Conferir FullReport",
                f"O PDF \"{os.path.basename(caminho_pdf)}\" não tem o mesmo nome do arquivo "
                f"\"{os.path.basename(caminho_txt)}\".\n\nVincular mesmo assim?",
            )
            if not vincular:
                return
        self.lista_arquivos_view.definir_pdf(indice, caminho_pdf)

    def _verificar_pronto(self):
        """Habilita o Calcular só com amostras e pelo menos um padrão, todos com padrão certificado escolhido."""
        pronto = bool(
            self.arquivos_amostras
            and self.padroes_marcados
            and all(self.padrao_vm.buscar_padrao(nome) for _, nome in self.padroes_marcados)
        )
        self.view.calcular.configure(state="normal" if pronto else "disabled")
        # os gráficos pela área normalizada só precisam do arquivo padrão (o Ar dele), não do padrão certificado
        self.graficos.habilita_graficos(bool(self.arquivos_amostras and self.padroes_marcados))

    def _selecao(self):
        return tuple(self.arquivos_amostras), tuple(self.padroes_marcados)

    def _herdar_escolhas(self, novos):
        """Slider e elementos desmarcados nos gráficos passam para os resultados novos do mesmo arquivo padrão."""
        antigos = {r.arquivo_padrao: r for r in self.resultados_graficos}
        for r in novos:
            antigo = antigos.get(r.arquivo_padrao)
            if antigo is not None and antigo is not r:
                r.graficos_traco = antigo.graficos_traco
                r.graficos_excluidos = antigo.graficos_excluidos
        self.resultados_graficos = novos

    def _resultados_graficos(self):
        """
        Os ResultadoPadrao dos gráficos: os do Calcular, se a seleção da lista não mudou desde então;
        senão, só a normalização (áreas pelo Ar de cada arquivo padrão, sem concentração).
        """
        selecao = self._selecao()
        if self.resultados_por_padrao and self._selecao_calculada == selecao:
            return list(self.resultados_por_padrao)
        if self.resultados_graficos and self._selecao_graficos == selecao:
            return list(self.resultados_graficos)

        novos, avisos = [], []
        try:
            for arquivo_padrao, nome_certificado in self.padroes_marcados:
                nome = self._nome_unico(arquivo_padrao, {r.nome for r in novos})
                normalizado = self.model.normalizar_sem_calcular(self.arquivos_amostras, arquivo_padrao)
                avisos += [a for a in self.model.avisos if a not in avisos]
                c_padrao = (self.padrao_vm.buscar_padrao(nome_certificado) if nome_certificado else None) or {}
                novos.append(ResultadoPadrao(nome, arquivo_padrao, c_padrao, {}, *normalizado))
        except ArquivoInvalidoError as erro:
            messagebox.showerror("Arquivo inválido", str(erro))
            return []
        except Exception as erro:
            messagebox.showerror("Erro na normalização", mensagem_erro_inesperado(erro))
            return []

        if avisos:
            messagebox.showwarning("Atenção", "\n\n".join(f"• {a}" for a in avisos))
        self._herdar_escolhas(novos)
        self._selecao_graficos = selecao
        return list(novos)

    @staticmethod
    def _nome_unico(caminho, usados):
        """Nome do arquivo sem extensão; se já existir (mesmo nome em pastas diferentes), ganha um sufixo."""
        base = nome_amostra(caminho)
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

        # LD: só das linhas com PDF vinculado
        if backgrounds:
            self.limite_deteccao.calcula_resultado_limite(backgrounds, resultado_padrao)

        return resultado_padrao

    def _calcular_todos(self):
        """Lê os arquivos e calcula com cada padrão. Devolve (resultados_por_padrao, avisos)."""
        avisos = []
        fullreports = self.lista_arquivos_view.fullreports_por_arquivo()
        backgrounds = self.limite_deteccao.extrair_backgrounds(fullreports) if fullreports else {}
        for caminho_txt, bg in backgrounds.items():
            if not bg:
                avisos.append(
                    f"Nenhum background encontrado em {os.path.basename(fullreports[caminho_txt])}: "
                    f"{nome_amostra(caminho_txt)} ficou sem LD. O PDF é um FullReport?"
                )
        backgrounds = {caminho: bg for caminho, bg in backgrounds.items() if bg}

        resultados_por_padrao = []
        for arquivo_padrao, nome_certificado in self.padroes_marcados:
            c_padrao = self.padrao_vm.buscar_padrao(nome_certificado)
            if not c_padrao:
                continue
            nome = self._nome_unico(arquivo_padrao, {r.nome for r in resultados_por_padrao})
            resultado_padrao = self._calcular_para_padrao(nome, arquivo_padrao, c_padrao, backgrounds)
            avisos += [a for a in self.model.avisos if a not in avisos]
            if resultado_padrao:
                resultados_por_padrao.append(resultado_padrao)
        return resultados_por_padrao, avisos

    def calcular(self):
        try:
            resultados_por_padrao, avisos = self._calcular_todos()
        except ArquivoInvalidoError as erro:
            messagebox.showerror("Arquivo inválido", str(erro))
            return None
        except Exception as erro:
            messagebox.showerror("Erro no cálculo", mensagem_erro_inesperado(erro))
            return None

        if avisos:
            messagebox.showwarning("Atenção", "\n\n".join(f"• {a}" for a in avisos))

        if not resultados_por_padrao:
            return None

        self.resultados_por_padrao = resultados_por_padrao
        self._herdar_escolhas(resultados_por_padrao)
        self._selecao_calculada = self._selecao_graficos = self._selecao()

        # Atualiza Variaveis global
        self.variaveis.lista_arquivos = self.arquivos_amostras
        self.variaveis.resultados_por_padrao = resultados_por_padrao

        self.export.habilita_exporta_excel()
        self.graficos.habilita_graficos()
        self.comparar_padroes.habilita(len(resultados_por_padrao) > 1)

        self.resultados_view.mostrar_resultados(resultados_por_padrao)
        if self.ao_calcular:
            self.ao_calcular(len(self.arquivos_amostras))

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
                messagebox.showerror(nome, f"Não foi possível calcular {nome}.\n\n{mensagem_erro_inesperado(erro)}")
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
