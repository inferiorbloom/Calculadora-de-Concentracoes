import json
import os
import tkinter.messagebox as messagebox
import customtkinter as ctk
from views import tema
from views.componentesView import JanelaFigura
from views.concentracaoView import (
    BarraAvisosView,
    ConcentracaoView,
    ListaArquivosView,
    ResultadosPadroesView,
    chave_natural,
)
from types import SimpleNamespace
from tkinter import filedialog
from models.analiseModel import escolhas_graficos_de_json, escolhas_graficos_para_json
from models.configModel import (
    carregar_certificados,
    carregar_tempo_contagem,
    carregar_ultimo_diretorio,
    salvar_certificado,
    salvar_tempo_contagem,
)
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



ORIGEM_NORMALIZACAO = "Gráficos (normalização)"


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
        # chamados pela tela principal: ao_status(texto curto para a aba lateral) e ao_editar_padroes(vm, lista)
        self.ao_status = None
        self.ao_editar_padroes = None
        self.sidebar_frame = sidebar_frame
        self.result_frame = result_frame
        self.arquivos_frame = arquivos_frame
        self.dynamic_frame = dynamic_frame
        self.mostrar_tela_inicial = mostrar_tela_inicial
        self.botoes_criados = False
        self.erro_model = PropagacaoErrosModel()

        # Variáveis para armazenar arquivos selecionados
        self.variaveis = Variaveis()
        self.padroes_marcados = []  # [(caminho do arquivo padrão, nome do padrão certificado)]
        self.arquivos_amostras = self.variaveis.lista_arquivos
        self.resultados_por_padrao = []
        # o que os gráficos mostram: os calculados ou, antes do Calcular, só as áreas normalizadas
        self.resultados_graficos = []
        self._selecao_calculada = None  # seleção da lista usada no último Calcular
        self._selecao_graficos = None  # e na última normalização para os gráficos
        self._assinatura_calculada = None  # tudo o que muda o resultado (_assinatura_calculo) no último Calcular

        # Chama os arquivos de service
        self.service = Service(sidebar_frame)

        # Chama os calculos de concentracao
        self.model = ConcentracaoModel()
        self.z_score_model = ZScoreModel()
        self.sensibilidade_model = SensibilidadeModel()

        # Chama a view dos botoes de calcular (seções ENTRADA e CÁLCULO do menu)
        self.view = ConcentracaoView(sidebar_frame)
        self.view.pack(fill="x", padx=16, pady=(0, 4))
        self.view.tempo_contagem.insert(0, carregar_tempo_contagem())

        # Chama o PadraoVM: o botão "Padrões certificados" fica na seção ENTRADA
        self.padrao_vm = PadraoVM(self.view.slot_padroes, dynamic_frame, sidebar_frame)
        self.padrao_vm.padrao_view
        self.lista_padrao = self.padrao_vm.volta_padrao()

        # Chama o resultado (um conjunto de abas para cada padrão)
        self.resultados_view = ResultadosPadroesView(self.result_frame)
        self.resultados_view.pack(padx=10, pady=10, fill="both", expand=True)
        # "resultados desatualizados" e os avisos do último cálculo, acima dos resultados
        self.barra_avisos = BarraAvisosView(self.result_frame, antes=self.resultados_view)
        self.resultados_view.ao_grafico_sensibilidade = self.grafico_sensibilidade

        # Chama a lista de arquivos (marcação de Padrão, padrão certificado e Amostras)
        self.lista_arquivos_view = ListaArquivosView(
            self.arquivos_frame,
            ao_alterar=self._atualizar_selecao,
            ao_escolher_pdf=self.escolher_fullreport,
            nomes_padroes=self.padrao_vm.nomes_padroes(),
            sugerir_certificado=self._sugerir_certificado,
            ao_vincular_pdfs=self.vincular_pdfs,
            ao_soltar=self.receber_arquivos,
        )
        self.lista_arquivos_view.pack(fill="both", expand=True, padx=6, pady=6)
        self.padrao_vm.padrao_view.ao_atualizar = self._padroes_editados

        # Exportar e Gráficos dividem a mesma caixa no menu
        self.caixa_saidas = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        self.caixa_saidas.pack(fill="x", padx=16, pady=(14, 10))
        tema.rotulo_secao(self.caixa_saidas, "Saídas", fill="x", pady=(0, 6))

        # Chama a Exportacao
        nome_planilha = f"amostras_{alvo}.xlsx" if alvo else "amostras.xlsx"
        self.export = ExportarVM(
            self.caixa_saidas, self.variaveis, nome_planilha, conferir=self._confirmar_exportacao, alvo=alvo
        )

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
        self._atualizar_status()

    def selecionar_arquivos(self):
        arquivos = sorted(self.service.selecionar_arquivos(), key=lambda c: chave_natural(os.path.basename(c)))
        if arquivos and not self._nomes_repetidos(arquivos):
            self.lista_arquivos_view.carregar(arquivos, self.variaveis.nomes_amostras)
            self._atualizar_selecao()
        return arquivos

    def receber_arquivos(self, caminhos):
        """
        Arquivos arrastados para a lista: os .txt entram no fim (o que já estava marcado continua);
        os .pdf são vinculados à linha do .txt de mesmo nome. Outros tipos são ignorados, com aviso.
        """
        txts = [c for c in caminhos if c.lower().endswith(".txt")]
        pdfs = [c for c in caminhos if c.lower().endswith(".pdf")]
        ignorados = [os.path.basename(c) for c in caminhos if c not in txts and c not in pdfs]

        estado = self.lista_arquivos_view.estado()
        ja_na_lista = {os.path.normcase(os.path.abspath(linha["arquivo"])) for linha in estado}
        # o Windows entrega os arquivos soltos numa ordem qualquer: entram em ordem de nome
        novos = sorted(
            (c for c in txts if os.path.normcase(os.path.abspath(c)) not in ja_na_lista),
            key=lambda c: chave_natural(os.path.basename(c)),
        )
        if novos:
            if self._nomes_repetidos([linha["arquivo"] for linha in estado] + novos):
                return
            estado += [{"arquivo": c, "padrao": False, "amostra": True, "certificado": "", "pdf": None} for c in novos]
            self.lista_arquivos_view.restaurar(estado, self.variaveis.nomes_amostras)

        sem_txt = []
        if pdfs:
            por_nome = {nome_amostra(c).lower(): c for c in pdfs}
            for indice, (caminho, _, _) in enumerate(self.lista_arquivos_view.linhas):
                pdf = por_nome.pop(nome_amostra(caminho).lower(), None)
                if pdf:
                    self.lista_arquivos_view.definir_pdf(indice, pdf)
            sem_txt = [os.path.basename(c) for c in por_nome.values()]

        problemas = []
        if sem_txt:
            problemas.append("PDFs sem um .txt de mesmo nome na lista (não vinculados):\n  " + "\n  ".join(sem_txt))
        if ignorados:
            problemas.append("Só .txt e .pdf entram na lista. Ignorados:\n  " + "\n  ".join(ignorados))
        if problemas:
            messagebox.showwarning("Arquivos arrastados", "\n\n".join(problemas))

    def vincular_pdfs(self):
        """
        Vincula, nas linhas ainda sem PDF, o FullReport com o mesmo nome do .txt (maiúsculas/minúsculas tanto faz),
        procurando primeiro na pasta de cada .txt. Se faltar algum, oferece escolher outra pasta.
        O vínculo de cada linha continua podendo ser trocado ou removido à mão.
        """
        linhas = self.lista_arquivos_view.linhas
        if not linhas:
            return

        def sem_pdf():
            return [i for i in range(len(linhas)) if i not in self.lista_arquivos_view.pdfs]

        def procurar(indices, pasta_de):
            vinculados = 0
            for indice in indices:
                caminho = linhas[indice][0]
                pasta = pasta_de(caminho)
                try:
                    candidatos = {nome_amostra(n).lower(): n for n in os.listdir(pasta) if n.lower().endswith(".pdf")}
                except OSError:
                    continue
                nome = candidatos.get(nome_amostra(caminho).lower())
                if nome:
                    self.lista_arquivos_view.definir_pdf(indice, os.path.join(pasta, nome), notificar=False)
                    vinculados += 1
            return vinculados

        antes = len(self.lista_arquivos_view.pdfs)
        procurar(sem_pdf(), os.path.dirname)
        faltam = sem_pdf()
        if faltam:
            outra = messagebox.askyesno(
                "Vincular PDFs",
                f"{len(faltam)} arquivo(s) sem um PDF de mesmo nome na pasta do .txt.\n\n"
                "Procurar em outra pasta?",
            )
            if outra:
                pasta = filedialog.askdirectory(title="Pasta dos FullReports (.pdf)", initialdir=carregar_ultimo_diretorio() or "")
                if pasta:
                    procurar(faltam, lambda _caminho: pasta)
        self.lista_arquivos_view._notificar()

        vinculados = len(self.lista_arquivos_view.pdfs) - antes
        faltam = [os.path.basename(linhas[i][0]) for i in sem_pdf()]
        texto = f"{vinculados} PDF(s) vinculado(s)."
        if faltam:
            texto += "\n\nContinuam sem PDF:\n  " + "\n  ".join(faltam)
        messagebox.showinfo("Vincular PDFs", texto)

    # --- análise salva (.cxa) ---------------------------------------------------------------------------
    def estado_analise(self):
        """O que o arquivo de análise guarda desta aba (os números são recalculados ao abrir)."""
        graficos = {}
        for r in self.resultados_graficos:
            if r.graficos_traco or r.graficos_excluidos:
                graficos[os.path.basename(r.arquivo_padrao)] = escolhas_graficos_para_json(
                    r.graficos_traco, r.graficos_excluidos
                )
        return {
            "linhas": self.lista_arquivos_view.estado(),
            "nomes": dict(self.variaveis.nomes_amostras),
            "z_score": self.view.var_z_score.get(),
            "sensibilidade": self.view.var_sensibilidade.get(),
            "tempo": self.view.tempo_contagem.get().strip(),
            "calculado": bool(self.resultados_por_padrao),  # ao abrir, calcula de novo com a seleção salva
            "graficos": graficos,
        }

    def restaurar_analise(self, estado):
        """Recria a aba a partir de estado_analise() e, se ela estava calculada, calcula de novo."""
        self.variaveis.nomes_amostras.clear()
        self.variaveis.nomes_amostras.update(estado.get("nomes") or {})
        self.view.var_z_score.set(bool(estado.get("z_score")))
        self.view.var_sensibilidade.set(bool(estado.get("sensibilidade")))
        self.view.tempo_contagem.delete(0, "end")
        if estado.get("tempo"):
            self.view.tempo_contagem.insert(0, estado["tempo"])

        # os ajustes dos gráficos passam para os resultados novos (o mesmo caminho do _herdar_escolhas)
        self.resultados_graficos = []
        for arquivo, escolhas in (estado.get("graficos") or {}).items():
            traco, excluidos = escolhas_graficos_de_json(escolhas)
            caminho = next(
                (linha["arquivo"] for linha in estado.get("linhas", []) if os.path.basename(linha["arquivo"]) == arquivo),
                arquivo,
            )
            self.resultados_graficos.append(
                SimpleNamespace(arquivo_padrao=caminho, graficos_traco=traco, graficos_excluidos=excluidos)
            )
        self.resultados_por_padrao = []
        self._selecao_calculada = self._selecao_graficos = self._assinatura_calculada = None
        self.variaveis.resultados_por_padrao = []
        self.resultados_view.limpar()
        self.barra_avisos.definir_avisos([])
        self.export.export.exportar_botao.configure(state="disabled")
        self.comparar_padroes.habilita(False)

        self.lista_arquivos_view.restaurar(estado.get("linhas") or [], self.variaveis.nomes_amostras)
        self._nomes_alterados()
        if estado.get("calculado") and str(self.view.calcular.cget("state")) == "normal":
            self.calcular()

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
        self._atualizar_status()

    def _assinatura_calculo(self):
        """Tudo o que muda o resultado do Calcular: a seleção, os PDFs (LD) e os valores dos certificados."""
        certificados = [self.padrao_vm.buscar_padrao(nome) for _, nome in self.padroes_marcados]
        return (
            self._selecao(),
            tuple(sorted(self.lista_arquivos_view.fullreports_por_arquivo().items())),
            json.dumps(certificados, sort_keys=True, default=str),
        )

    def desatualizado(self):
        """True se há resultados, mas a lista (ou um PDF, ou um certificado) mudou depois do Calcular."""
        return bool(self.resultados_por_padrao) and self._assinatura_calculada != self._assinatura_calculo()

    def _proximo_passo(self):
        """(texto, tipo) do status abaixo do Calcular: o que falta para calcular, ou o estado do cálculo."""
        if not self.lista_arquivos_view.linhas:
            return "Selecione os arquivos .txt (Ctrl+O) ou arraste-os para a lista.", "info"
        if not self.padroes_marcados:
            return "Marque um arquivo como Padrão.", "info"
        sem_certificado = [c for c, nome in self.padroes_marcados if not self.padrao_vm.buscar_padrao(nome)]
        if sem_certificado:
            if not self.padrao_vm.nomes_padroes():
                return "Cadastre um padrão certificado em Gerenciar padrões.", "info"
            return f"Escolha o padrão certificado de {nome_amostra(sem_certificado[0])}.", "info"
        if not self.arquivos_amostras:
            return "Marque pelo menos uma amostra.", "info"
        if not self.resultados_por_padrao:
            return "Pronto para calcular (F5).", "pronto"
        if self.desatualizado():
            return "A seleção mudou depois do cálculo: calcule de novo (F5).", "atencao"
        n = len(self.variaveis.lista_arquivos)
        return f"Calculado · {n} amostra{'s' if n != 1 else ''}.", "feito"

    def _atualizar_status(self):
        texto, tipo = self._proximo_passo()
        self.view.mostrar_status(texto, tipo)
        desatualizado = self.desatualizado()
        self.barra_avisos.mostrar_desatualizado(
            "A seleção mudou depois do último Calcular: a tabela, os gráficos de concentração e o Excel ainda "
            "mostram o cálculo anterior. Calcule de novo (F5)." if desatualizado else ""
        )
        if self.ao_status:
            n = len(self.variaveis.lista_arquivos)
            texto_aba = f"{n} amostras" if self.resultados_por_padrao else ""
            self.ao_status(f"{texto_aba} · desatualizado" if desatualizado else texto_aba)

    def _confirmar_exportacao(self):
        """Antes de exportar o Excel: com resultados desatualizados, pergunta se exporta mesmo assim."""
        if not self.desatualizado():
            return True
        return messagebox.askyesno(
            "Resultados desatualizados",
            "A lista de arquivos (ou um PDF, ou um padrão certificado) mudou depois do último Calcular.\n\n"
            "Exportar mesmo assim os resultados do cálculo anterior?",
            icon="warning",
        )

    def _sugerir_certificado(self, caminho, usados):
        """
        Certificado para um arquivo recém-marcado como Padrão: o usado da última vez com esse arquivo; senão,
        o último usado neste alvo. None deixa a lista escolher (o primeiro ainda não usado).
        """
        nomes = self.padrao_vm.nomes_padroes()
        lembrados = carregar_certificados(self.alvo)
        for certificado in (lembrados["arquivos"].get(os.path.basename(caminho)), lembrados["ultimo"]):
            if certificado in nomes and certificado not in usados:
                return certificado
        return None

    def _selecao(self):
        # sem a ordem: reorganizar a lista não muda nenhum número, então não deixa o cálculo desatualizado
        return tuple(sorted(self.arquivos_amostras)), tuple(sorted(self.padroes_marcados))

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
            antigos = [a for a in self.barra_avisos.avisos if a[0] != ORIGEM_NORMALIZACAO]
            self.barra_avisos.definir_avisos(antigos + [(ORIGEM_NORMALIZACAO, a) for a in avisos])
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

        self.barra_avisos.definir_avisos([("Cálculo", a) for a in avisos])
        if avisos:
            messagebox.showwarning("Atenção", "\n\n".join(f"• {a}" for a in avisos))

        if not resultados_por_padrao:
            return None

        self.resultados_por_padrao = resultados_por_padrao
        self._herdar_escolhas(resultados_por_padrao)
        self._selecao_calculada = self._selecao_graficos = self._selecao()
        self._assinatura_calculada = self._assinatura_calculo()
        for arquivo_padrao, nome_certificado in self.padroes_marcados:
            salvar_certificado(self.alvo, os.path.basename(arquivo_padrao), nome_certificado)

        # Atualiza Variaveis global
        self.variaveis.lista_arquivos = self.arquivos_amostras
        self.variaveis.resultados_por_padrao = resultados_por_padrao

        self.export.habilita_exporta_excel()
        self.graficos.habilita_graficos()
        self.comparar_padroes.habilita(len(resultados_por_padrao) > 1)

        self.resultados_view.mostrar_resultados(resultados_por_padrao)
        self._atualizar_status()

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
                self.barra_avisos.definir_avisos(
                    self.barra_avisos.avisos + [(nome, f"Não foi possível calcular: {erro}")]
                )
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
            texto = (
                "Nenhum Z'-Score calculado para: " + ", ".join(vazios) + ". "
                "É preciso pelo menos 2 amostras (sem contar o próprio padrão) com elementos "
                "que tenham valor e erro no padrão certificado."
            )
            messagebox.showwarning("Z'-Score", texto)
            self.barra_avisos.definir_avisos(self.barra_avisos.avisos + [("Z'-Score", texto)])
        self.resultados_view.mostrar_z_score(self.resultados_por_padrao)
        return {r.nome: r.z_score_resultado for r in self.resultados_por_padrao}

    def calcular_sensibilidade(self):
        if not self.resultados_por_padrao:
            return {}

        tempo = self.view.tempo_contagem.get().strip()
        if not tempo:
            messagebox.showerror(
                "Tempo de contagem", "Informe o tempo de contagem (em segundos) no campo ao lado de Sensibilidade."
            )
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
        salvar_tempo_contagem(tempo)

        for resultado_padrao, resultado in zip(self.resultados_por_padrao, calculados):
            resultado_padrao.sensibilidade_resultado = resultado
            resultado_padrao.tempo_contagem = tempo
        self.resultados_view.mostrar_sensibilidade(self.resultados_por_padrao)
        return {r.nome: r.sensibilidade_resultado for r in self.resultados_por_padrao}

    def grafico_sensibilidade(self, nome_padrao):
        """Sensibilidade × Z das linhas do próprio padrão (botão da aba Sensibilidade)."""
        resultado = next((r for r in self.resultados_por_padrao if r.nome == nome_padrao), None)
        if resultado is None or not resultado.tempo_contagem:
            return None
        pontos = self.sensibilidade_model.pontos_do_padrao(resultado, resultado.tempo_contagem)
        titulo = f"Sensibilidade × Z · padrão {resultado.rotulo}" + (f" · alvo {self.alvo}" if self.alvo else "")
        return JanelaFigura(
            self.result_frame,
            "Sensibilidade × Z",
            lambda tema: self.sensibilidade_model.figura_por_z(pontos, titulo, tema),
            f"sensibilidade_por_Z_{resultado.nome}",
        )
