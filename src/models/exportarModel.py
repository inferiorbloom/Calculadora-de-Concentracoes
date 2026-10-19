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

    def _buscar_ld_para_elemento(self, ld_resultado, nome_padrao, elemento):
        if not ld_resultado or not isinstance(ld_resultado, dict):
            return None

        nome_padrao_normalizado = os.path.basename(str(nome_padrao or "")).replace(".txt", "")

        #print(f"\nBuscando {elemento}")
        #print("nome_padrao =", nome_padrao_normalizado)

        #print("dados desse padrão:")
        #print(ld_resultado.get(nome_padrao_normalizado))

        valor_padrao = ld_resultado.get(nome_padrao_normalizado, {}).get(elemento, "")

        #print("valor encontrado =", valor_padrao)
        
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
        nome_limpo = "".join("_" if c in self.CARACTERES_INVALIDOS_ABA else c for c in str(nome_padrao)).strip()
        nomes = {}
        for base in self.ABAS:
            nome = base
            if varios_padroes:
                sufixo = f" - {nome_limpo}"
                nome = (base + sufixo)[: self.LIMITE_NOME_ABA].rstrip()
            candidato, n = nome, 2
            while candidato.lower() in usados:
                extra = f" ({n})"
                candidato = nome[: self.LIMITE_NOME_ABA - len(extra)] + extra
                n += 1
            usados.add(candidato.lower())
            nomes[base] = candidato
        return nomes

    def exportar_para_excel(self, lista_arquivos, resultados_por_padrao, caminho_arquivo=None, abas_exportar=None):
        """
        resultados_por_padrao: lista de ResultadoPadrao; cada padrão vira o seu próprio conjunto de abas.
        abas_exportar: nomes de TODAS_ABAS a gravar; None grava todas.
        """
        arquivos = lista_arquivos or []
        resultados_por_padrao = list(resultados_por_padrao or [])
        abas_exportar = set(self.TODAS_ABAS if abas_exportar is None else abas_exportar)
        if not abas_exportar & set(self.TODAS_ABAS):
            raise ValueError("Escolha pelo menos uma aba para exportar.")

        # Se o usuário não escolheu um local para salvar, salva em um diretório gravável pelo usuário
        if not caminho_arquivo:
            pasta_saida = ensure_directory(user_data_path("exports"))
            caminho_arquivo = os.path.join(pasta_saida, "amostras.xlsx")

        def _salvar_excel(path):
            usados = {self.ABA_DADOS.lower(), self.ABA_SLD.lower()}
            varios_padroes = len(resultados_por_padrao) > 1
            with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                if self.ABA_DADOS in abas_exportar:
                    self._escrever_dados(writer, arquivos, resultados_por_padrao)
                if self.ABA_SLD in abas_exportar:
                    self._escrever_sld(writer, resultados_por_padrao)
                if not abas_exportar & set(self.ABAS):
                    return
                for resultado_padrao in resultados_por_padrao:
                    abas = self.nomes_abas(resultado_padrao.nome, varios_padroes, usados)
                    abas = {base: nome for base, nome in abas.items() if base in abas_exportar}
                    self._escrever_padrao(writer, arquivos, resultado_padrao, abas)

        try:
            _salvar_excel(caminho_arquivo)
        except PermissionError:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pasta_saida = ensure_directory(user_data_path("exports"))
            caminho_arquivo = os.path.join(pasta_saida, f"amostras_{timestamp}.xlsx")
            _salvar_excel(caminho_arquivo)

        print("Exportacao concluida!")
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

    def _escrever_dados(self, writer, arquivos, resultados_por_padrao):
        """
        Aba "Dados" única: o bloco de cada padrão fica ao lado do anterior, separado por uma coluna vazia.
        Com vários padrões, a primeira linha identifica o padrão de cada bloco.
        """
        varios_padroes = len(resultados_por_padrao) > 1
        linha_inicial = 1 if varios_padroes else 0
        coluna = 0

        for r in resultados_por_padrao:
            df_dados = self.aba_dados.montar(arquivos, r.areas_normalizadas, r.erros_normalizados, r.fatores_normalizacao)
            df_dados = self._normalizar_valores_para_excel(df_dados)
            df_dados.to_excel(
                writer,
                sheet_name=self.ABA_DADOS,
                index=False,
                header=False,
                startrow=linha_inicial,
                startcol=coluna,
                na_rep="-",
            )

            if varios_padroes:
                identificacao = f"Padrão: {r.nome}"
                if r.nome_certificado:
                    identificacao += f" ({r.nome_certificado})"
                writer.sheets[self.ABA_DADOS].write(0, coluna, identificacao)

            coluna += max(df_dados.shape[1], 1) + 1  # +1 = coluna separadora

        if not resultados_por_padrao:
            pd.DataFrame().to_excel(writer, sheet_name=self.ABA_DADOS, index=False)

    def _escrever_sld(self, writer, resultados_por_padrao):
        """
        Aba "SLD" única. Com um padrão, fica como sempre foi; com vários, Amostra/Elemento/Energia
        aparecem uma vez e cada padrão ganha as colunas LD e Sensibilidade, com o nome do padrão mesclado em cima.
        """
        if len(resultados_por_padrao) <= 1:
            r = resultados_por_padrao[0] if resultados_por_padrao else None
            if r:
                df_sld = self.aba_sld.montar(r.resultado_limite, r.sensibilidade_resultado, r.concentracoes)
            else:
                df_sld = self.aba_sld.montar()
            df_sld = self._normalizar_valores_para_excel(df_sld)
            df_sld.to_excel(writer, sheet_name=self.ABA_SLD, index=False, na_rep="-")
            return

        df_sld = self.aba_sld.montar_varios(
            [(r.nome, r.resultado_limite, r.sensibilidade_resultado, r.concentracoes) for r in resultados_por_padrao]
        )
        df_sld = self._normalizar_valores_para_excel(df_sld)
        df_sld.to_excel(writer, sheet_name=self.ABA_SLD, index=False, header=False, startrow=2, na_rep="-")

        worksheet = writer.sheets[self.ABA_SLD]
        chaves, valores = self.aba_sld.CHAVES, self.aba_sld.VALORES
        for col, nome in enumerate(chaves):
            worksheet.write(1, col, nome)

        col = len(chaves)
        for r in resultados_por_padrao:
            identificacao = f"Padrão: {r.nome}"
            if r.nome_certificado:
                identificacao += f" ({r.nome_certificado})"
            worksheet.merge_range(0, col, 0, col + len(valores) - 1, identificacao)
            for i, valor in enumerate(valores):
                worksheet.write(1, col + i, valor)
            col += len(valores)

    def _escrever_padrao(self, writer, arquivos, resultado_padrao, abas):
        """Escreve as abas de UM padrão. abas: nome base -> nome da aba no arquivo (só as que serão exportadas)."""
        dfs, elementos_ordenados, contagem_elementos = self.montar_dataframes(arquivos, resultado_padrao)
        dfs = {nome: self._normalizar_valores_para_excel(df) for nome, df in dfs.items()}

        ld_resultado = resultado_padrao.resultado_limite or {}
        unidade_padrao = resultado_padrao.unidade_padrao or {}
        nome_padrao = os.path.basename(resultado_padrao.arquivo_padrao or "").replace(".txt", "")

        if "Concentrações" in abas:
            dfs["Concentrações"].to_excel(
                writer,
                sheet_name=abas["Concentrações"],
                index=True,
                index_label="Amostra",
                na_rep="-"
            )

        if "Resultados" in abas:
            dfs["Resultados"].to_excel(
                writer,
                sheet_name=abas["Resultados"],
                index=True,
                header=False,
                startrow=2,
                na_rep="-"
            )

            # Média, desvio padrão e DPR (%) das amostras (sem o padrão), logo abaixo da última amostra
            # (mesmo startrow das amostras, deslocado pelo número de amostras)
            df_estatisticas = self.aba_resultados.montar_estatisticas(
                dfs["Resultados"],
                os.path.splitext(os.path.basename(resultado_padrao.arquivo_padrao or ""))[0].strip(),
            )
            if not df_estatisticas.empty:
                df_estatisticas.to_excel(
                    writer,
                    sheet_name=abas["Resultados"],
                    index=True,
                    header=False,
                    startrow=2 + len(dfs["Resultados"]),
                    na_rep="-"
                )

        if "Z-Score" in abas:
            dfs["Z-Score"].to_excel(writer, sheet_name=abas["Z-Score"], index=False, na_rep="-")

        if "Resultados" not in abas:
            return

        worksheet = writer.sheets[abas["Resultados"]]
        formato_percentual = writer.book.add_format({"num_format": "0.0"})

        # Cabeçalho linha 0: identifica o padrão usado nesta aba
        identificacao = f"Padrão: {resultado_padrao.nome}"
        if resultado_padrao.nome_certificado:
            identificacao += f" ({resultado_padrao.nome_certificado})"
        worksheet.write(0, 0, identificacao)
        worksheet.set_column(0, 0, max(12, len(identificacao) + 2))

        # Cabeçalho linha 1
        worksheet.write(1, 0, "LD")

        # Cabeçalho linha 2
        worksheet.write(2, 0, "")

        col = 1

        for elemento, energia in elementos_ordenados:

            unidade = unidade_padrao.get(elemento, "")
            possui_duplicata = contagem_elementos[elemento] > 1
            titulo = montar_titulo_coluna(elemento, energia, unidade, possui_duplicata)

            # Linha 0 -> nome do elemento + unidade
            worksheet.merge_range(0, col, 0, col + 2, titulo)

            # Busca LD
            ld = "-"

            if ld_resultado:
                ld_bruto = self._buscar_ld_para_elemento(ld_resultado, nome_padrao, elemento)

                if ld_bruto not in ["", None]:
                    try:
                        ld = float(ld_bruto)
                    except (TypeError, ValueError):
                        ld = ld_bruto

            # Linha 1 -> LD
            worksheet.merge_range(1, col, 1, col + 2, ld)

            # Linha 2 -> C / Erro / Erro (%)
            worksheet.write(2, col, "C")
            worksheet.write(2, col + 1, "Erro")
            worksheet.write(2, col + 2, "Erro (%)")
            worksheet.set_column(col + 2, col + 2, None, formato_percentual)

            col += 3

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