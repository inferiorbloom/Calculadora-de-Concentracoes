from importlib.resources import path

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

    def exportar_para_excel(
        self,
        lista_arquivos,
        concentracoes=None,
        areas_normalizadas=None,
        fatores_normalizacao=None,
        erros_normalizados=None,
        erros_propagados=None,
        ld_resultado=None,
        unidade_padrao=None,
        arquivo_padrao=None,
        caminho_arquivo=None,
        sensibilidade_resultado=None,
        z_score_resultado=None,
    ):
        arquivos = lista_arquivos or []
        concentracoes = concentracoes or {}
        areas_normalizadas = areas_normalizadas or {}
        fatores_normalizacao = fatores_normalizacao or {}
        erros_normalizados = erros_normalizados or {}
        erros_propagados = erros_propagados or {}
        ld_resultado = ld_resultado or {}
        unidade_padrao = unidade_padrao or {}
        arquivo_padrao = arquivo_padrao or ""
        sensibilidade_resultado = sensibilidade_resultado or {}
        z_score_resultado = z_score_resultado or {}
        nome_padrao = os.path.basename(arquivo_padrao).replace(".txt", "")
        #print("[DEBUG] nome_padrao para exportação:", nome_padrao)
        #print("[DEBUG] chaves_ld_resultado:", list(ld_resultado.keys()) if ld_resultado else [])

        #print("\n===== LD DO PADRÃO =====")
        #print(ld_resultado.get(nome_padrao))


        # --- Aba "Dados" ---
        df_dados = self.aba_dados.montar(
            arquivos, areas_normalizadas, erros_normalizados, fatores_normalizacao
        )

        # --- Aba "Resultados" ---
        df_analise, elementos_ordenados, contagem_elementos = self.aba_resultados.montar(
            concentracoes, erros_propagados, unidade_padrao, aplicar_arredondamento=False
        )

        # --- Aba "Concentrações" ---
        df_concentracoes = self.aba_concentracoes.montar(df_analise)
        df_sld = self.aba_sld.montar(
            ld_resultado,
            sensibilidade_resultado,
            concentracoes,
        )
        df_zscore = self.aba_zscore.montar(z_score_resultado)

        #print("\n========== DF_CONCENTRACOES ==========")
        #print(df_concentracoes.to_string())

        #df_analise.to_excel("DEBUG_RESULTADOS.xlsx")
        #df_concentracoes.to_excel("DEBUG_CONCENTRACOES.xlsx")

        # Se o usuário não escolheu um local para salvar, salva em um diretório gravável pelo usuário
        if not caminho_arquivo:
            pasta_saida = ensure_directory(user_data_path("exports"))
            caminho_arquivo = os.path.join(pasta_saida, "amostras.xlsx")

        def _salvar_excel(path):

            df_dados_excel = self._normalizar_valores_para_excel(df_dados)
            df_concentracoes_excel = self._normalizar_valores_para_excel(df_concentracoes)
            df_analise_excel = self._normalizar_valores_para_excel(df_analise)
            df_sld_excel = self._normalizar_valores_para_excel(df_sld)
            df_zscore_excel = self._normalizar_valores_para_excel(df_zscore)

            with pd.ExcelWriter(
                path,
                engine="xlsxwriter",
            ) as writer:

                df_dados_excel.to_excel(writer, sheet_name="Dados", index=False, header=False, na_rep="-")

                df_concentracoes_excel.to_excel(
                    writer,
                    sheet_name="Concentrações",
                    index=True,
                    index_label="Amostra",
                    na_rep="-"
                )

                df_analise_excel.to_excel(
                    writer,
                    sheet_name="Resultados",
                    index=True,
                    header=False,
                    startrow=2,
                    na_rep="-"
                )

                df_sld_excel.to_excel(
                    writer,
                    sheet_name="SLD",
                    index=False,
                    na_rep="-",
                )

                df_zscore_excel.to_excel(
                    writer,
                    sheet_name="Z-Score",
                    index=False,
                    na_rep="-",
                )

                worksheet = writer.sheets["Resultados"]

                # Cabeçalho linha 0
                worksheet.write(0, 0, "")

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
                    worksheet.merge_range(
                        0,
                        col,
                        0,
                        col + 1,
                        titulo
                    )

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
                    worksheet.merge_range(
                        1,
                        col,
                        1,
                        col + 1,
                        ld
                    )

                    # Linha 2 -> C / Erro
                    worksheet.write(2, col, "C")
                    worksheet.write(2, col + 1, "Erro")

                    col += 2

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