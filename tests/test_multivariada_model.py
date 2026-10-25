import os
import sys
import tempfile
import unittest
import zipfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.multivariadaModel import FRACAO_LD, DadosInsuficientesError, MultivariadaModel
from models.resultadoPadraoModel import ResultadoPadrao


def _resultado(valores, ld=None):
    """valores: {amostra: {elemento: mg/kg}} -> ResultadoPadrao com o padrão "pd" (fora da análise)."""
    concentracoes, areas = {}, {}
    for i, (amostra, elementos) in enumerate(valores.items(), start=1):
        concentracoes[f"concentracao{i}"] = {amostra: {(e, 1.0 + j): v for j, (e, v) in enumerate(elementos.items())}}
        areas[amostra] = {(e, 1.0 + j): 100.0 for j, e in enumerate(elementos)}
    r = ResultadoPadrao("pd", "pd.txt", {}, concentracoes, areas, {}, {}, {}, {})
    r.unidade_padrao = {}
    r.resultado_limite = ld or {}
    return r


AMOSTRAS = {
    "a1": {"K": 100.0, "Ca": 200.0, "Fe": 50.0, "Zn": 5.0},
    "a2": {"K": 120.0, "Ca": 180.0, "Fe": 40.0, "Zn": 6.0},
    "a3": {"K": 90.0, "Ca": 260.0, "Fe": 70.0, "Zn": 3.0},
    "a4": {"K": 150.0, "Ca": 150.0, "Fe": 30.0, "Zn": 8.0},
}


class TransformacoesTests(unittest.TestCase):
    def setUp(self):
        self.model = MultivariadaModel()

    def test_clr_soma_zero_e_nao_depende_da_escala(self):
        x = np.array([[1.0, 2.0, 7.0], [3.0, 3.0, 4.0]])
        clr = self.model.clr(x)
        self.assertTrue(np.allclose(clr.sum(axis=1), 0))
        self.assertTrue(np.allclose(self.model.clr(x * 1000), clr))  # mg/kg ou g/kg: mesmo clr

    def test_proporcionalidade_de_colunas_proporcionais_e_um(self):
        rng = np.random.default_rng(1)
        base = rng.uniform(1, 10, size=8)
        x = np.column_stack([base, 3 * base, rng.uniform(1, 10, size=8)])
        rho = self.model.proporcionalidade(self.model.clr(x))
        self.assertAlmostEqual(rho[0, 1], 1.0)
        self.assertTrue(np.allclose(rho, rho.T))
        self.assertTrue(np.allclose(np.diag(rho), 1))

    def test_proporcionalidade_segue_a_formula(self):
        clr = np.array([[0.1, -0.3, 0.2], [0.4, -0.1, -0.3], [-0.2, 0.5, -0.3], [0.0, 0.1, -0.1]])
        rho = self.model.proporcionalidade(clr)
        esperado = 1 - np.var(clr[:, 0] - clr[:, 2], ddof=1) / (np.var(clr[:, 0], ddof=1) + np.var(clr[:, 2], ddof=1))
        self.assertAlmostEqual(rho[0, 2], esperado)

    def test_pca_e_a_decomposicao_da_covariancia_do_clr(self):
        dados = self.model.montar_dados(_resultado(AMOSTRAS), [], modo_abaixo_ld="medido")
        res = self.model.analisar(dados)
        centrado = res.clr - res.clr.mean(axis=0)
        autovalores = np.sort(np.linalg.eigvalsh(np.cov(centrado, rowvar=False)))[::-1][: len(res.variancia)]
        self.assertTrue(np.allclose(res.variancia, autovalores / autovalores.sum()))
        # scores = clr centrado projetado nas cargas
        self.assertTrue(np.allclose(res.scores, centrado @ res.cargas))
        self.assertEqual(res.ligacao.shape, (len(dados.amostras) - 1, 4))


class TratamentoDosValoresTests(unittest.TestCase):
    def setUp(self):
        self.model = MultivariadaModel()

    def test_abaixo_do_ld_entra_com_o_valor_medido_por_padrao(self):
        r = _resultado(AMOSTRAS, ld={"a1": {"Zn": 10.0}})
        dados = self.model.montar_dados(r, [])
        coluna = dados.elementos.index("Zn")
        self.assertEqual(dados.matriz[0, coluna], 5.0)
        self.assertEqual(dados.tratamentos[("a1", "Zn")], "abaixo do LD (medido)")

    def test_abaixo_do_ld_vira_065_ld_quando_escolhido(self):
        r = _resultado(AMOSTRAS, ld={"a1": {"Zn": 10.0}})
        dados = self.model.montar_dados(r, [], modo_abaixo_ld="substituir")
        coluna = dados.elementos.index("Zn")
        self.assertAlmostEqual(dados.matriz[0, coluna], FRACAO_LD * 10.0)
        # a2 não tem LD próprio: vale o mesmo LD da tabela (o da amostra, senão o do padrão, senão o primeiro)
        self.assertAlmostEqual(dados.matriz[1, coluna], FRACAO_LD * 10.0)
        self.assertAlmostEqual(dados.matriz[2, dados.elementos.index("K")], 90.0)

    def test_nao_detectado_com_ld_recebe_065_ld(self):
        valores = {a: dict(v) for a, v in AMOSTRAS.items()}
        del valores["a2"]["Zn"]
        r = _resultado(valores, ld={"a2": {"Zn": 4.0}})
        dados = self.model.montar_dados(r, [])
        self.assertIn("Zn", dados.elementos)
        self.assertAlmostEqual(dados.matriz[1, dados.elementos.index("Zn")], FRACAO_LD * 4.0)
        self.assertEqual(dados.tratamentos[("a2", "Zn")], "0,65 × LD (não detectado)")

    def test_sem_valor_e_sem_ld_o_elemento_sai(self):
        valores = {a: dict(v) for a, v in AMOSTRAS.items()}
        del valores["a3"]["Zn"]
        dados = self.model.montar_dados(_resultado(valores), [])
        self.assertNotIn("Zn", dados.elementos)
        self.assertEqual(dados.excluidos[0][0], "Zn")

    def test_o_alvo_do_tubo_e_o_padrao_ficam_de_fora(self):
        valores = dict(AMOSTRAS, pd={"K": 1.0, "Ca": 1.0, "Fe": 1.0, "Zn": 1.0})
        dados = self.model.montar_dados(_resultado(valores), [_resultado(valores)], alvo="Zn")
        self.assertNotIn("pd", dados.amostras)
        self.assertNotIn("Zn", dados.elementos)

    def test_poucas_amostras_explica_o_que_faltou(self):
        with self.assertRaises(DadosInsuficientesError):
            self.model.montar_dados(_resultado({"a1": AMOSTRAS["a1"], "a2": AMOSTRAS["a2"]}), [])

    def test_figuras_e_excel(self):
        res = self.model.analisar(self.model.montar_dados(_resultado(AMOSTRAS), []))
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        for criar in (self.model.figura_biplot, self.model.figura_correlacao, self.model.figura_dendrograma):
            FigureCanvasAgg(criar(res, "teste")).draw()
        with tempfile.TemporaryDirectory() as pasta:
            caminho = self.model.exportar_excel(os.path.join(pasta, "m.xlsx"), res, "teste")
            with zipfile.ZipFile(caminho) as xlsx:
                self.assertEqual(xlsx.read("xl/workbook.xml").decode("utf-8").count("<sheet "), 9)


if __name__ == "__main__":
    unittest.main()
