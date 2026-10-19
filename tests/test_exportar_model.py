import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.exportarModel import ExportarModel
from models.arredondamentoModel import ArredondamentoModel
from models.abaResultadosModel import AbaResultadosModel


class ExportarModelTests(unittest.TestCase):
    def test_buscar_ld_para_elemento_usa_o_nome_do_arquivo_padrao(self):
        model = ExportarModel()
        ld_resultado = {
            "outro_padrao": {"Fe": 0.111},
            "290426ab": {"Fe": 1.234},
        }

        self.assertEqual(model._buscar_ld_para_elemento(ld_resultado, "290426ab.txt", "Fe"), 1.234)

    def test_formatar_resultado_retorna_float(self):
        model = ArredondamentoModel()
        valor, erro, casas = model.formatar_resultado(20.0, 0.1, "Fe")

        self.assertIsInstance(valor, float)
        self.assertIsInstance(erro, float)
        self.assertEqual(casas, 0)

    def test_montar_resultados_preserva_valores_sem_arredondar(self):
        model = AbaResultadosModel()
        valor_calculado = 1.23456789012345
        erro_calculado = 0.012345678901234

        df, _, _ = model.montar(
            {"arquivo.txt": {"amostra": {("Fe", 1.0): valor_calculado}}},
            {"arquivo.txt": {"amostra": {("Fe", 1.0): erro_calculado}}},
            {},
            aplicar_arredondamento=False,
        )

        valores_exportados = df.iloc[0].tolist()
        self.assertEqual(valores_exportados[:2], [valor_calculado, erro_calculado])
        self.assertAlmostEqual(valores_exportados[2], erro_calculado / valor_calculado * 100)

    def test_erro_percentual_fica_vazio_quando_concentracao_e_zero(self):
        df, _, _ = AbaResultadosModel().montar(
            {"arquivo.txt": {"amostra": {("Fe", 1.0): 0.0}}},
            {"arquivo.txt": {"amostra": {("Fe", 1.0): 0.5}}},
            {},
            aplicar_arredondamento=False,
        )

        self.assertTrue(pd.isna(df.iloc[0][("Fe", "Erro (%)")]))

    def test_estatisticas_media_desvio_e_dpr_sem_o_padrao(self):
        model = AbaResultadosModel()
        df, _, _ = model.montar(
            {"arquivo.txt": {"pd": {("Fe", 1.0): 99.0}, "a": {("Fe", 1.0): 10.0}, "b": {("Fe", 1.0): 20.0}}},
            {"arquivo.txt": {"pd": {("Fe", 1.0): 9.0}, "a": {("Fe", 1.0): 1.0}, "b": {("Fe", 1.0): 3.0}}},
            {},
            aplicar_arredondamento=False,
        )

        estatisticas = model.montar_estatisticas(df, nome_padrao="pd")

        self.assertEqual(list(estatisticas.index), ["Média", "Desvio padrão", "DPR (%)"])
        self.assertEqual(estatisticas.loc["Média", ("Fe", "C")], 15.0)
        self.assertAlmostEqual(estatisticas.loc["Desvio padrão", ("Fe", "C")], 7.0710678, places=6)
        self.assertAlmostEqual(estatisticas.loc["DPR (%)", ("Fe", "C")], 47.140452, places=5)
        self.assertEqual(estatisticas.loc["Média", ("Fe", "Erro")], 2.0)
        self.assertTrue(pd.isna(estatisticas.loc["DPR (%)", ("Fe", "Erro")]))


if __name__ == "__main__":
    unittest.main()
