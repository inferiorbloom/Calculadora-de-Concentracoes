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


class CoresETiposTests(unittest.TestCase):
    def setUp(self):
        self.model = GraficosModel()

    def test_cada_elemento_tem_a_mesma_cor_em_qualquer_posicao(self):
        cores_a = {r: c for r, _, c in self.model.montar_fatias([("Fe", 9.0), ("Cu", 1.0)], None, "claro")[0]}
        cores_b = {r: c for r, _, c in self.model.montar_fatias([("Cu", 9.0), ("Zn", 5.0), ("Fe", 1.0)], None, "escuro")[0]}
        self.assertEqual(cores_a["Fe"], cores_b["Fe"])
        self.assertEqual(cores_a["Cu"], cores_b["Cu"])
        self.assertNotEqual(cores_a["Fe"], cores_a["Cu"])

    def test_todos_os_elementos_da_tabela_tem_cor(self):
        from models.elementosQuimicos import ELEMENTOS
        self.assertEqual(set(ELEMENTOS.values()) - set(self.model.cores), set())

    def test_arquivo_do_laboratorio_sobrepoe_so_os_elementos_dele(self):
        import json
        from models import coresElementosModel as cores_model
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "cores.json")
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump({"Fe": "#123456", "Cu": "vermelho"}, f)  # cor inválida é ignorada
            original = cores_model.ARQUIVO_USUARIO
            cores_model.ARQUIVO_USUARIO = caminho
            try:
                cores = cores_model.carregar_cores()
            finally:
                cores_model.ARQUIVO_USUARIO = original
        self.assertEqual(cores["Fe"], "#123456")
        self.assertEqual(cores["Cu"], self.model.cores["Cu"])

    def test_barras_mostram_todos_e_pizzas_agrupam_em_outros(self):
        itens = [(f"E{i}", float(20 - i)) for i in range(14)]
        pizza, outros = self.model.montar_fatias(itens, None, "claro")
        barras, _ = self.model.montar_fatias(itens, None, "claro", limite=None)
        self.assertEqual(len(pizza), 10)
        self.assertEqual(len(outros), 5)
        self.assertEqual(len(barras), 14)

    def test_os_quatro_tipos_desenham(self):
        from models.graficosModel import TIPOS
        for tipo in TIPOS:
            for tema in ("claro", "escuro"):
                for figura in self.model.criar_figuras("a", VALORES, 2, tema, "pd", tipo):
                    figura.canvas.draw()  # quebra aqui se algo no desenho estiver errado


if __name__ == "__main__":
    unittest.main()
