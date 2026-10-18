import os
import sys
import unittest

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
        self.assertEqual(valores_exportados, [valor_calculado, erro_calculado])


if __name__ == "__main__":
    unittest.main()
