import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.graficosModel import GraficosModel
from models.resultadoPadraoModel import ResultadoPadrao

# total 1000: Ca 600, K 300, Fe 60, Zn 30, Cu 10
VALORES = {"K": 300.0, "Ca": 600.0, "Fe": 60.0, "Cu": 10.0, "Zn": 30.0}


def _resultado():
    concentracoes = {"concentracao1": {"a": {("K", 3.3): 0.3, ("Ca", 3.7): 0.6, ("Fe", 6.4): 60.0}}}
    unidades = {"K": "g/kg", "Ca": "g/kg", "Fe": "mg/kg"}
    r = ResultadoPadrao("pd", "pd.txt", {}, concentracoes, {}, {}, {}, {}, {})
    r.unidade_padrao = unidades
    return r


class GraficosModelTests(unittest.TestCase):
    def setUp(self):
        self.model = GraficosModel()

    def test_slider_manda_os_menores_para_o_traco(self):
        majoritarios, traco = self.model.dividir(VALORES, 2)
        self.assertEqual([e for e, _ in majoritarios], ["Ca", "K", "Fe"])
        self.assertEqual([e for e, _ in traco], ["Zn", "Cu"])

        _, traco = self.model.dividir(VALORES, 3)
        self.assertEqual([e for e, _ in traco], ["Fe", "Zn", "Cu"])

    def test_majoritario_nunca_fica_vazio(self):
        majoritarios, traco = self.model.dividir(VALORES, 99)
        self.assertEqual([e for e, _ in majoritarios], ["Ca"])
        self.assertEqual(len(traco), 4)
        self.assertEqual(self.model.dividir({"K": 1.0}, 3), ([("K", 1.0)], []))

    def test_automatico_fica_perto_de_5_por_cento(self):
        # traço com 1, 2, 3 elementos = 1%, 4%, 10% -> o mais perto de 5% é 2 (Cu + Zn)
        self.assertEqual(self.model.n_traco_automatico(VALORES), 2)
        self.assertEqual(self.model.n_traco_automatico({"K": 50.0, "Ca": 50.0}), 0)

    def test_escolha_por_amostra_e_automatico(self):
        r = _resultado()
        valores = self.model.valores_da_amostra(r, "a")
        self.assertEqual(valores, {"K": 300.0, "Ca": 600.0, "Fe": 60.0})

        # sem mexer no slider: começa no automático
        self.assertEqual(self.model.n_traco_da_amostra(r, "a", valores, automatico=False), 1)
        r.graficos_traco["a"] = 0
        self.assertEqual(self.model.n_traco_da_amostra(r, "a", valores, automatico=False), 0)
        # a caixinha ignora a escolha manual, sem apagá-la
        self.assertEqual(self.model.n_traco_da_amostra(r, "a", valores, automatico=True), 1)
        self.assertEqual(r.graficos_traco["a"], 0)

    def test_exportar_grava_majoritario_e_traco(self):
        with tempfile.TemporaryDirectory() as pasta:
            gravados = self.model.exportar(pasta, [
                (None, "amostra 1", VALORES, 2),
                (None, "sem traço", VALORES, 0),
                ("Padrão: x/y", "a", VALORES, 1),
                (None, "vazia", {}, 1),
            ])
            nomes = sorted(os.path.relpath(g, pasta) for g in gravados)
            self.assertTrue(all(os.path.getsize(g) > 0 for g in gravados))
        self.assertEqual(nomes, sorted([
            "amostra 1 - majoritario.png",
            "amostra 1 - traco.png",
            "sem traço - majoritario.png",
            os.path.join("Padrão_ x_y", "a - majoritario.png"),
            os.path.join("Padrão_ x_y", "a - traco.png"),
        ]))


if __name__ == "__main__":
    unittest.main()
