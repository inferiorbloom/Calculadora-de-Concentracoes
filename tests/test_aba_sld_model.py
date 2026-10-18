import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.abaSLDModel import AbaSLDModel


class AbaSLDModelTests(unittest.TestCase):
    def test_ordena_elementos_por_numero_atomico(self):
        resultado = AbaSLDModel().montar(
            {"amostra-a": {"Fe": 1.2, "Al": 0.8}},
            {
                "amostra-a": {
                    ("Fe", 6.4): 2.5,
                    ("Al", 1.5): 1.5,
                }
            },
        )

        self.assertEqual(resultado["Elemento"].tolist(), ["Al", "Al", "Fe", "Fe"])

    def test_monta_ld_e_sensibilidade_por_amostra_e_elemento(self):
        resultado = AbaSLDModel().montar(
            {"amostra-a": {"Fe": 1.2}},
            {"amostra-a": {("Fe", 6.4): 2.5}},
            {"concentracao1": {"amostra-a": {("Fe", 6.4): "3.0"}}},
        )

        self.assertEqual(resultado.loc[0, "Amostra"], "amostra-a")
        self.assertEqual(resultado.loc[0, "Elemento"], "Fe")
        self.assertEqual(resultado.loc[0, "Energia (keV)"], 6.4)
        self.assertEqual(resultado.loc[0, "LD"], 1.2)
        self.assertEqual(resultado.loc[0, "Sensibilidade"], 2.5)


if __name__ == "__main__":
    unittest.main()