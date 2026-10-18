import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.abaZScoreModel import AbaZScoreModel


class AbaZScoreModelTests(unittest.TestCase):
    def test_monta_colunas_do_preview(self):
        resultado = AbaZScoreModel().montar(
            {
                "Fe": {
                    "n": 3,
                    "media_amostras": 12.0,
                    "desvio_padrao_amostras": 2.0,
                    "valor_certificado": 11.0,
                    "erro_certificado": 1.0,
                    "z_score": 0.447,
                }
            }
        )

        self.assertEqual(list(resultado.columns), AbaZScoreModel.COLUNAS)
        self.assertEqual(resultado.loc[0, "Elemento"], "Fe")
        self.assertEqual(resultado.loc[0, "n"], 3)
        self.assertEqual(resultado.loc[0, "Z'-Score"], 0.447)


if __name__ == "__main__":
    unittest.main()