import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.zscoreModel import ZScoreModel


class ZScoreModelTests(unittest.TestCase):
    def test_desconsidera_amostra_com_mesmo_nome_do_padrao(self):
        concentracoes = {
            "concentracao1": {"padrao": {("Fe", 6.4): "100"}},
            "concentracao2": {"amostra1": {("Fe", 6.4): "10"}},
            "concentracao3": {"amostra2": {("Fe", 6.4): "14"}},
        }
        c_padrao = {"elementos": {"Fe": {"valor": 12, "erro": 1}}}

        resultado = ZScoreModel().calcular(
            concentracoes,
            c_padrao,
            nome_padrao="C:/dados/padrao.txt",
        )["Fe"]

        self.assertEqual(resultado["n"], 2)
        self.assertEqual(resultado["media_amostras"], 12)
        self.assertAlmostEqual(resultado["desvio_padrao_amostras"], math.sqrt(8))

    def test_calcula_media_desvio_amostral_e_z_score(self):
        concentracoes = {
            "concentracao1": {"amostra1": {("Fe", 6.4): "10"}},
            "concentracao2": {"amostra2": {("Fe", 6.4): "12"}},
            "concentracao3": {"amostra3": {("Fe", 6.4): "14"}},
        }
        c_padrao = {
            "elementos": {
                "Fe": {"valor": 11, "erro": 1},
            }
        }

        resultado = ZScoreModel().calcular(concentracoes, c_padrao)["Fe"]

        self.assertEqual(resultado["n"], 3)
        self.assertEqual(resultado["media_amostras"], 12)
        self.assertAlmostEqual(resultado["desvio_padrao_amostras"], 2)
        self.assertAlmostEqual(resultado["z_score"], 1 / math.sqrt(5))

    def test_agrega_energias_diferentes_do_mesmo_elemento(self):
        concentracoes = {
            "concentracao1": {"amostra1": {("K", 3.5): "10"}},
            "concentracao2": {"amostra2": {("K", 3.6): "12"}},
            "concentracao3": {"amostra3": {("K", 3.5): "14"}},
        }
        c_padrao = {"elementos": {"K": {"valor": 11, "erro": 1}}}

        resultado = ZScoreModel().calcular(concentracoes, c_padrao)["K"]

        self.assertEqual(resultado["n"], 3)
        self.assertEqual(resultado["media_amostras"], 12)
        self.assertAlmostEqual(resultado["desvio_padrao_amostras"], 2)

    def test_ignora_elemento_com_apenas_uma_amostra(self):
        concentracoes = {"concentracao1": {"amostra1": {("Fe", 6.4): "10"}}}
        c_padrao = {"elementos": {"Fe": {"valor": 10, "erro": 1}}}

        self.assertEqual(ZScoreModel().calcular(concentracoes, c_padrao), {})

    def test_usa_media_ponderada_apenas_para_concentracoes_duplicadas(self):
        concentracoes = {
            "concentracao1": {
                "amostra1": {
                    ("Ag", 3.5): "10",
                    ("Ag", 4.0): "14",
                }
            },
            "concentracao2": {"amostra2": {("Ag", 3.5): "11"}},
        }
        erros_concentracao = {
            "concentracao1": {
                "amostra1": {
                    ("Ag", 3.5): 1,
                    ("Ag", 4.0): 2,
                }
            },
            "concentracao2": {"amostra2": {("Ag", 3.5): 1}},
        }
        c_padrao = {"elementos": {"Ag": {"valor": 11, "erro": 1}}}

        resultado = ZScoreModel().calcular(
            concentracoes, c_padrao, erros_concentracao
        )["Ag"]

        self.assertEqual(resultado["n"], 2)
        self.assertAlmostEqual(resultado["media_amostras"], 10.9)


if __name__ == "__main__":
    unittest.main()