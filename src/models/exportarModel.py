import pandas as pd
import os
import customtkinter as ctk

from resource_utils import ensure_directory, user_data_path

from models.arredondamentoModel import ArredondamentoModel
from models.abaDadosModel import AbaDadosModel
from models.abaResultadosModel import AbaResultadosModel, montar_titulo_coluna
from models.abaConcentracoesModel import AbaConcentracoesModel
from models.abaSLDModel import AbaSLDModel
from models.abaZScoreModel import AbaZScoreModel
from models.leitorArquivoModel import nome_amostra
from models.fichaInformacaoModel import nome_da_amostra
from models.estiloTabelaModel import EstiloTabela
from models.qualidadeModel import TEXTO_MENOR_LD, abaixo_do_ld, ld_de_referencia


class ExportarModel:

    ABA_DADOS = "Dados"  # aba única: os padrões ficam lado a lado
    ABA_SLD = "SLD"  # aba única: LD e Sensibilidade de cada padrão em colunas próprias
    ABAS = ["Concentrações", "Resultados", "Z-Score"]  # abas repetidas para cada padrão
    TODAS_ABAS = [ABA_DADOS, ABA_SLD, *ABAS]  # tudo o que pode ser escolhido para exportar

    def __init__(self):
        self.arredondamento = ArredondamentoModel()
        self.aba_dados = AbaDadosModel()
        self.aba_resultados = AbaResultadosModel()
        self.aba_concentracoes = AbaConcentracoesModel()
        self.aba_sld = AbaSLDModel()
        self.aba_zscore = AbaZScoreModel()
        # True: valores abaixo do LD saem como "< LD" (sem o erro) em Concentrações e Resultados.
        # A média e o desvio das estatísticas continuam calculados com os valores medidos.
        self.menor_ld = False

    def _aplicar_menor_ld(self, df_analise, resultado_padrao, elementos_ordenados, contagem_elementos):
        """Cópia do df_analise com "< LD" no C (e o erro vazio) das amostras abaixo do LD do elemento."""
        if not self.menor_ld or df_analise is None or df_analise.empty or not resultado_padrao.resultado_limite:
            return df_analise
        df = df_analise.astype(object)  # "< LD" é texto: a coluna deixa de ser só número
        unidades = resultado_padrao.unidade_padrao or {}
        nome_padrao = nome_amostra(resultado_padrao.arquivo_padrao or "")
        for elemento, energia in elementos_ordenados:
            titulo = montar_titulo_coluna(elemento, energia, unidades.get(elemento, ""), contagem_elementos[elemento] > 1)
            if (titulo, "C") not in df.columns:
                continue
            for amostra in df.index:
                ld = ld_de_referencia(resultado_padrao.resultado_limite, amostra, elemento, nome_padrao)
                if abaixo_do_ld(df.at[amostra, (titulo, "C")], ld):
                    df.at[amostra, (titulo, "C")] = TEXTO_MENOR_LD
                    for subcoluna in ("Erro", "Erro (%)"):
                        if (titulo, subcoluna) in df.columns:
                            df.at[amostra, (titulo, subcoluna)] = ""
        return df

    def _normalizar_valores_para_excel(self, df):
        """Converte valores que parecem numéricos para tipos numéricos reais antes de gravar no Excel."""
        if df is None or df.empty:
            return df

        df_export = df.copy()

        for coluna in df_export.columns:
            serie = df_export[coluna]

            if not pd.api.types.is_object_dtype(serie) and not pd.api.types.is_string_dtype(serie):
                continue

            valores_normalizados = []
            for valor in serie:
                if pd.isna(valor):
                    valores_normalizados.append(valor)
                    continue

                if valor in ["", None]:
                    valores_normalizados.append(valor)
                    continue

                if isinstance(valor, str):
                    texto = valor.strip()
                    if texto in ["-", "--", "—", "NaN", "nan", "None", "none"]:
                        valores_normalizados.append(valor)
                        continue

                    try:
                        valores_normalizados.append(float(texto))
                    except ValueError:
                        valores_normalizados.append(valor)
                else:
                    valores_normalizados.append(valor)

            df_export[coluna] = valores_normalizados

        return df_export

    @staticmethod
    def _inserir_nomes(df, nomes):
        """
        Coluna "Nome" (ficha de informação) logo depois da amostra, só quando alguma amostra tem nome.
        Devolve (df, tem_nome). Vem depois do _normalizar_valores_para_excel, para um nome como "2" não virar número.
        """
        if df is None or df.empty:
            return df, False
        valores = [nome_da_amostra(nomes, amostra) for amostra in df.index]
        if not any(valores):
            return df, False
        df = df.copy()
        df.insert(0, ("Nome", "") if isinstance(df.columns, pd.MultiIndex) else "Nome", valores)
        return df, True

    def _buscar_ld_para_elemento(self, ld_resultado, nome_padrao, elemento):
        if not ld_resultado or not isinstance(ld_resultado, dict):
            return None

        nome_padrao_normalizado = nome_amostra(nome_padrao or "")

        valor_padrao = ld_resultado.get(nome_padrao_normalizado, {}).get(elemento, "")

        if valor_padrao not in ["", None]:
            return valor_padrao

        for chave, dados in ld_resultado.items():
            if chave == nome_padrao_normalizado:
                continue

            if isinstance(dados, dict):
                valor_fallback = dados.get(elemento, "")
                if valor_fallback not in ["", None]:
                    return valor_fallback
                
        return valor_padrao
        #return None

    LIMITE_NOME_ABA = 31  # limite do Excel
    CARACTERES_INVALIDOS_ABA = "[]:*?/\\"

    def nomes_abas(self, nome_padrao, varios_padroes, usados=None):
        """
        Nomes das abas de um padrão: {"Concentrações": ..., "Resultados": ..., ...}.
        Com um padrão só, mantém os nomes de sempre; com vários, cada aba ganha o nome do padrão.
        """
        usados = set() if usados is None else usados
        return {
            base: self._nome_aba_unico(f"{base} - {nome_padrao}" if varios_padroes else base, usados)
            for base in self.ABAS
        }

    def _nome_aba_unico(self, nome, usados):
        """Nome de aba válido no Excel (sem caracteres proibidos, até 31 caracteres) e que ainda não está em usados."""
        nome = "".join("_" if c in self.CARACTERES_INVALIDOS_ABA else c for c in str(nome)).strip()
        nome = nome[: self.LIMITE_NOME_ABA].rstrip()
        candidato, n = nome, 2
        while candidato.lower() in usados:
            extra = f" ({n})"
            candidato = nome[: self.LIMITE_NOME_ABA - len(extra)] + extra
            n += 1
        usados.add(candidato.lower())
        return candidato

    def _gravar(self, salvar, caminho_arquivo, nome_padrao_arquivo):
        """
        Chama salvar(caminho). Sem caminho, ou com o arquivo aberto no Excel (PermissionError),
        grava na pasta de exportações do usuário. Devolve o caminho onde o arquivo ficou.
        """
        if not caminho_arquivo:
            pasta_saida = ensure_directory(user_data_path("exports"))
            caminho_arquivo = os.path.join(pasta_saida, f"{nome_padrao_arquivo}.xlsx")

        try:
            salvar(caminho_arquivo)
        except PermissionError:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pasta_saida = ensure_directory(user_data_path("exports"))
            caminho_arquivo = os.path.join(pasta_saida, f"{nome_padrao_arquivo}_{timestamp}.xlsx")
            salvar(caminho_arquivo)
        return caminho_arquivo

    def exportar_todos_alvos(self, resultados_por_alvo, caminho_arquivo=None, nomes_por_alvo=None):
        """
        Planilha simples com todos os alvos: uma aba por padrão de cada alvo ("Ag", ou "Ag - <padrão>" com vários),
        com C e Erro de cada elemento nas amostras e o LD abaixo do nome do elemento
        (a aba "Resultados" sem o Erro (%) e sem as estatísticas).
        resultados_por_alvo: {alvo: lista de ResultadoPadrao}, só com os alvos já calculados.
        nomes_por_alvo: {alvo: {código: nome}} da ficha de informação de cada alvo.
        """
        nomes_por_alvo = nomes_por_alvo or {}
        resultados_por_alvo = {alvo: lista for alvo, lista in resultados_por_alvo.items() if lista}
        if not resultados_por_alvo:
            raise ValueError("Nenhum alvo calculado para exportar.")

        def _salvar_excel(path):
            usados = set()
            with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                self.estilo = EstiloTabela(writer.book)
                for alvo, resultados_por_padrao in resultados_por_alvo.items():
                    varios_padroes = len(resultados_por_padrao) > 1
                    for resultado_padrao in resultados_por_padrao:
                        nome = f"{alvo} - {resultado_padrao.nome}" if varios_padroes else alvo
                        self._escrever_resumo(
                            writer, self._nome_aba_unico(nome, usados), resultado_padrao, nomes_por_alvo.get(alvo)
                        )

        caminho_arquivo = self._gravar(_salvar_excel, caminho_arquivo, "todos_alvos")
        self.mostrar_popup_sucesso(caminho_arquivo)
        return caminho_arquivo

    def _escrever_resumo(self, writer, nome_aba, resultado_padrao, nomes=None):
        """Aba do Exportar de todos os alvos: amostras x (C, Erro) de cada elemento, com o LD no cabeçalho."""
        r = resultado_padrao
        df, elementos_ordenados, contagem_elementos = self.aba_resultados.montar(
            r.concentracoes, r.erros_concentracao, r.unidade_padrao, aplicar_arredondamento=False
        )
        worksheet = self._aba(writer, nome_aba)
        if df.empty:
            return

        df = self._aplicar_menor_ld(df, r, elementos_ordenados, contagem_elementos)
        df = self._normalizar_valores_para_excel(df.drop(columns="Erro (%)", level=1))
        self._escrever_resultados(worksheet, r, df, elementos_ordenados, contagem_elementos, ["C", "Erro"], nomes)

    def exportar_para_excel(self, lista_arquivos, resultados_por_padrao, caminho_arquivo=None, abas_exportar=None,
                            nomes_amostras=None):
        """
        resultados_por_padrao: lista de ResultadoPadrao; cada padrão vira o seu próprio conjunto de abas.
        abas_exportar: nomes de TODAS_ABAS a gravar; None grava todas.
        nomes_amostras: {código: nome} da ficha de informação (coluna "Nome" em Concentrações e Resultados).
        """
        arquivos = lista_arquivos or []
        resultados_por_padrao = list(resultados_por_padrao or [])
        abas_exportar = set(self.TODAS_ABAS if abas_exportar is None else abas_exportar)
        if not abas_exportar & set(self.TODAS_ABAS):
            raise ValueError("Escolha pelo menos uma aba para exportar.")

        def _salvar_excel(path):
            usados = {self.ABA_DADOS.lower(), self.ABA_SLD.lower()}
            varios_padroes = len(resultados_por_padrao) > 1
            with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                self.estilo = EstiloTabela(writer.book)
                if self.ABA_DADOS in abas_exportar:
                    self._escrever_dados(writer, arquivos, resultados_por_padrao)
                if self.ABA_SLD in abas_exportar:
                    self._escrever_sld(writer, resultados_por_padrao)
                if not abas_exportar & set(self.ABAS):
                    return
                for resultado_padrao in resultados_por_padrao:
                    abas = self.nomes_abas(resultado_padrao.nome, varios_padroes, usados)
                    abas = {base: nome for base, nome in abas.items() if base in abas_exportar}
                    self._escrever_padrao(writer, arquivos, resultado_padrao, abas, nomes_amostras)

        caminho_arquivo = self._gravar(_salvar_excel, caminho_arquivo, "amostras")

        self.mostrar_popup_sucesso(caminho_arquivo)

    def montar_dataframes(self, arquivos, resultado_padrao):
        """Monta os DataFrames das abas de UM padrão ("Dados" e "SLD" são montadas em _escrever_dados/_escrever_sld)."""
        r = resultado_padrao

        # --- Aba "Resultados" ---
        df_analise, elementos_ordenados, contagem_elementos = self.aba_resultados.montar(
            r.concentracoes, r.erros_concentracao, r.unidade_padrao, aplicar_arredondamento=False
        )

        # --- Aba "Concentrações" ---
        df_concentracoes = self.aba_concentracoes.montar(df_analise)
        df_zscore = self.aba_zscore.montar(r.z_score_resultado)

        return {
            "Concentrações": df_concentracoes,
            "Resultados": df_analise,
            "Z-Score": df_zscore,
        }, elementos_ordenados, contagem_elementos

    # --- escrita das abas (célula a célula, no estilo de tabela de artigo: ver EstiloTabela) ---

    @staticmethod
    def _aba(writer, nome_aba):
        worksheet = writer.book.add_worksheet(nome_aba)
        worksheet.hide_gridlines(2)  # sem a grade cinza do Excel: só as réguas da tabela aparecem
        return worksheet

    @staticmethod
    def _identificacao(resultado_padrao):
        identificacao = f"Padrão: {resultado_padrao.nome}"
        if resultado_padrao.nome_certificado:
            identificacao += f" ({resultado_padrao.nome_certificado})"
        return identificacao

    @staticmethod
    def _linhas(df, index=True):
        """Linhas do DataFrame como listas (com o índice na frente, se index=True)."""
        valores = df.values.tolist()
        if not index:
            return valores
        return [[indice, *linha] for indice, linha in zip(df.index, valores)]

    def _escrever_dados(self, writer, arquivos, resultados_por_padrao):
        """
        Aba "Dados" única: o bloco de cada padrão fica ao lado do anterior, separado por uma coluna vazia.
        Com vários padrões, a primeira linha identifica o padrão de cada bloco. Cada amostra é uma tabela,
        com o nome e o fator de normalização (pelo Ar) logo acima.
        """
        worksheet = self._aba(writer, self.ABA_DADOS)
        varios_padroes = len(resultados_por_padrao) > 1
        cabecalho = self.aba_dados.CABECALHO
        coluna = 0

        for r in resultados_por_padrao:
            linha = 0
            if varios_padroes:
                self.estilo.escrever_celula(worksheet, 0, coluna, self._identificacao(r), negrito=True)
                linha = 2

            blocos = self.aba_dados.montar(arquivos, r.areas_normalizadas, r.erros_normalizados, r.fatores_normalizacao)
            for nome, fator, picos in blocos:
                self.estilo.escrever_celula(worksheet, linha, coluna, nome, negrito=True)
                self.estilo.escrever_celula(worksheet, linha, coluna + len(cabecalho) - 2, "Normalização:")
                self.estilo.escrever_celula(worksheet, linha, coluna + len(cabecalho) - 1, fator)
                linha += 1
                linha += self.estilo.escrever(worksheet, linha, coluna, [cabecalho], picos, colunas_rotulo=1)
                linha += 1  # linha em branco entre as amostras

            coluna += len(cabecalho) + 1  # +1 = coluna separadora

    def _escrever_sld(self, writer, resultados_por_padrao):
        """
        Aba "SLD" única. Com um padrão, uma tabela simples; com vários, Amostra/Elemento/Energia
        aparecem uma vez e cada padrão ganha as colunas LD e Sensibilidade, com o nome do padrão mesclado em cima.
        """
        worksheet = self._aba(writer, self.ABA_SLD)
        chaves, valores = self.aba_sld.CHAVES, self.aba_sld.VALORES

        if len(resultados_por_padrao) <= 1:
            r = resultados_por_padrao[0] if resultados_por_padrao else None
            if r:
                df_sld = self.aba_sld.montar(r.resultado_limite, r.sensibilidade_resultado, r.concentracoes)
            else:
                df_sld = self.aba_sld.montar()
            df_sld = self._normalizar_valores_para_excel(df_sld)
            self.estilo.escrever(
                worksheet, 0, 0, [list(df_sld.columns)], self._linhas(df_sld, index=False), colunas_rotulo=len(chaves)
            )
            return

        df_sld = self.aba_sld.montar_varios(
            [(r.nome, r.resultado_limite, r.sensibilidade_resultado, r.concentracoes) for r in resultados_por_padrao]
        )
        df_sld = self._normalizar_valores_para_excel(df_sld)

        topo, mesclas = [None] * len(chaves), []
        for r in resultados_por_padrao:
            mesclas.append((0, len(topo), len(topo) + len(valores) - 1))
            topo += [self._identificacao(r)] + [None] * (len(valores) - 1)
        titulos = list(chaves) + list(valores) * len(resultados_por_padrao)

        self.estilo.escrever(
            worksheet, 0, 0, [topo, titulos], self._linhas(df_sld, index=False),
            colunas_rotulo=len(chaves), mesclas=mesclas,
        )

    def _escrever_padrao(self, writer, arquivos, resultado_padrao, abas, nomes=None):
        """Escreve as abas de UM padrão. abas: nome base -> nome da aba no arquivo (só as que serão exportadas)."""
        dfs, elementos_ordenados, contagem_elementos = self.montar_dataframes(arquivos, resultado_padrao)
        dfs = {nome: self._normalizar_valores_para_excel(df) for nome, df in dfs.items()}

        nome_padrao = nome_amostra(resultado_padrao.arquivo_padrao or "")
        # estatísticas com os valores medidos, antes de um "< LD" tomar o lugar de algum deles
        df_estatisticas = self.aba_resultados.montar_estatisticas(dfs["Resultados"], nome_padrao)
        if self.menor_ld:
            dfs["Resultados"] = self._aplicar_menor_ld(
                dfs["Resultados"], resultado_padrao, elementos_ordenados, contagem_elementos
            )
            dfs["Concentrações"] = self.aba_concentracoes.montar(dfs["Resultados"])

        if "Concentrações" in abas:
            worksheet = self._aba(writer, abas["Concentrações"])
            df_concentracoes, tem_nome = self._inserir_nomes(dfs["Concentrações"], nomes)
            if not df_concentracoes.empty:
                self.estilo.escrever(
                    worksheet, 0, 0, [["Amostra", *df_concentracoes.columns]], self._linhas(df_concentracoes),
                    colunas_rotulo=2 if tem_nome else 1,
                )

        if "Resultados" in abas:
            worksheet = self._aba(writer, abas["Resultados"])
            if not dfs["Resultados"].empty:
                # Média, desvio padrão e DPR (%) das amostras (sem o padrão), logo abaixo da última amostra
                self._escrever_resultados(
                    worksheet, resultado_padrao, dfs["Resultados"], elementos_ordenados, contagem_elementos,
                    ["C", "Erro", "Erro (%)"], nomes, df_estatisticas,
                )

        if "Z-Score" in abas:
            worksheet = self._aba(writer, abas["Z-Score"])
            df_zscore = dfs["Z-Score"]
            self.estilo.escrever(
                worksheet, 0, 0, [list(df_zscore.columns)], self._linhas(df_zscore, index=False), colunas_rotulo=1
            )

    def _ld_do_elemento(self, resultado_padrao, elemento):
        """LD do elemento (do padrão; se não houver, de outra medida com FullReport), ou "-"."""
        ld_resultado = resultado_padrao.resultado_limite or {}
        if not ld_resultado:
            return "-"
        nome_padrao = nome_amostra(resultado_padrao.arquivo_padrao or "")
        ld_bruto = self._buscar_ld_para_elemento(ld_resultado, nome_padrao, elemento)
        if ld_bruto in ["", None]:
            return "-"
        try:
            return float(ld_bruto)
        except (TypeError, ValueError):
            return ld_bruto

    def _escrever_resultados(self, worksheet, resultado_padrao, df, elementos_ordenados, contagem_elementos,
                             subcolunas, nomes=None, df_estatisticas=None):
        """
        Tabela no formato da aba "Resultados". Cabeçalho em 3 linhas: padrão + nome do elemento (+ unidade),
        o LD do elemento e as subcolunas (C, Erro, ...). Depois as amostras e, se houver, as estatísticas.
        df: colunas MultiIndex (elemento, subcoluna), na ordem de elementos_ordenados x subcolunas.
        """
        df, tem_nome = self._inserir_nomes(df, nomes)
        unidade_padrao = resultado_padrao.unidade_padrao or {}
        largura = len(subcolunas)

        topo = [self._identificacao(resultado_padrao)]
        linha_ld = ["LD"]
        linha_sub = [""]
        if tem_nome:
            topo.append("")
            linha_ld.append("")
            linha_sub.append("Nome")

        mesclas, formatos_coluna = [], {}
        for elemento, energia in elementos_ordenados:
            col = len(topo)
            unidade = unidade_padrao.get(elemento, "")
            titulo = montar_titulo_coluna(elemento, energia, unidade, contagem_elementos[elemento] > 1)
            topo += [titulo] + [None] * (largura - 1)
            linha_ld += [self._ld_do_elemento(resultado_padrao, elemento)] + [None] * (largura - 1)
            linha_sub += subcolunas
            mesclas += [(0, col, col + largura - 1), (1, col, col + largura - 1)]
            for i, subcoluna in enumerate(subcolunas):
                if subcoluna == "Erro (%)":
                    formatos_coluna[col + i] = "0.0"

        corpo = self._linhas(df)
        separar_antes = ()
        if df_estatisticas is not None and not df_estatisticas.empty:
            if tem_nome:
                df_estatisticas = df_estatisticas.copy()
                df_estatisticas.insert(0, ("Nome", ""), "")
            separar_antes = (len(corpo),)  # régua fina entre as amostras e a média
            corpo += self._linhas(df_estatisticas)

        self.estilo.escrever(
            worksheet, 0, 0, [topo, linha_ld, linha_sub], corpo,
            colunas_rotulo=2 if tem_nome else 1,
            mesclas=mesclas,
            linhas_valor=(1,),
            separar_antes=separar_antes,
            formatos_coluna=formatos_coluna,
        )

    def mostrar_popup_sucesso(self, caminho_arquivo):
        popup = ctk.CTkToplevel()
        popup.title("Exportação Concluída!")
        popup.geometry("400x200")

        label = ctk.CTkLabel(
            popup,
            text=f"Arquivo exportado com sucesso!\n\nSalvo em:\n{caminho_arquivo}",
            font=("Arial", 16),
            justify="center",
            wraplength=360,
        )
        label.pack(pady=20, padx=20)

        botao_ok = ctk.CTkButton(popup, text="Fechar", width=100, command=popup.destroy)
        botao_ok.pack(pady=10)

        popup.update_idletasks()
        w, h = popup.winfo_width() + 100, popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (w // 2)
        y = (popup.winfo_screenheight() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")

        popup.grab_set()