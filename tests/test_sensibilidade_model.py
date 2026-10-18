import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.sensibilidadeModel import SensibilidadeModel


class SensibilidadeModelTests(unittest.TestCase):
    def test_calcula_por_amostra_e_elemento_correspondente(self):
        model = SensibilidadeModel()
        concentracoes = {
            "concentracao1": {
                "amostra-a": {
                    ("Fe", 6.4): "2.0",
                    ("Ca", 3.7): "4.0",
                }
            }
        }
        areas = {
            "amostra-a": {
                ("Fe", 6.4): 100.0,
                ("Ca", 3.7): 80.0,
            }
        }
        c_padrao = {
            "elementos": {
                "Fe": {"valor": 10.0, "unidade": "g/kg"},
                "Ca": {"valor": 20.0, "unidade": "g/kg"},
            }
        }

        resultado = model.calcular(concentracoes, areas, c_padrao, 10)

        self.assertAlmostEqual(resultado["amostra-a"][("Fe", 6.4)], 1.0)
        self.assertAlmostEqual(resultado["amostra-a"][("Ca", 3.7)], 0.4)

    def test_converte_mg_por_kg_para_g_por_kg(self):
        model = SensibilidadeModel()
        concentracoes = {"concentracao1": {"amostra-a": {("Fe", 6.4): "1"}}}
        areas = {"amostra-a": {("Fe", 6.4): 100.0}}
        c_padrao = {"elementos": {"Fe": {"valor": 10.0, "unidade": "mg/kg"}}}

        resultado = model.calcular(concentracoes, areas, c_padrao, 10)

        self.assertAlmostEqual(resultado["amostra-a"][("Fe", 6.4)], 1000.0)

    def test_rejeita_tempo_zero(self):
        with self.assertRaises(ValueError):
            SensibilidadeModel().calcular({}, {}, {}, 0)


if __name__ == "__main__":
    unittest.main()