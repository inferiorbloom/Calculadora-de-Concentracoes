import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.comparacaoModel import CORES_ALVOS, ComparacaoModel
from models.resultadoPadraoModel import ResultadoPadrao


def _resultado(nome, certificado, concs, erros, areas=None, unidades=None):
    """concs/erros: {amostra: {(elemento, energia): valor}}, todas no mesmo bloco de concentração."""
    r = ResultadoPadrao(nome, f"{nome}.txt", {"nome": certificado}, {"concentracao1": concs}, areas or {}, {}, {}, {}, {})
    r.erros_concentracao = {"concentracao1": erros}
    r.unidade_padrao = unidades or {}
    return r


class ComparacaoModelTests(unittest.TestCase):
    def setUp(self):
        self.model = ComparacaoModel()

    def test_linha_mais_intensa_e_unidade_em_mg_kg(self):
        concs = {"a": {("Ca", 3.69): 2.0, ("Ca", 4.01): 3.0, ("Ag", 22.1): 9.0, ("Ar", 2.96): 1.0}}
        erros = {"a": {("Ca", 3.69): 0.1, ("Ca", 4.01): 0.5, ("Ag", 22.1): 1.0, ("Ar", 2.96): 0.1}}
        areas = {"a": {("Ca", 3.69): 5000, ("Ca", 4.01): 700}}
        r = _resultado("pd", "NIST", concs, erros, areas, {"Ca": "g/kg"})
        valores = self.model.valores_com_erro(r, "a", {"Ag"})
        self.assertEqual(valores, {"Ca": (2000.0, 100.0)})  # Kα (maior área), em mg/kg; sem Ag (alvo) e Ar

    def test_entre_padroes_uma_serie_por_padrao(self):
        # p1 e p2 são as medidas dos próprios padrões: ficam fora do eixo X
        r1 = _resultado("p1", "NIST", {"a": {("Fe", 6.4): 10.0}, "b": {("Fe", 6.4): 20.0}, "p2": {("Fe", 6.4): 1.0}},
                        {"a": {}, "b": {}, "p2": {}})
        r2 = _resultado("p2", "BCR", {"a": {("Fe", 6.4): 12.0}, "b": {("Zn", 8.6): 5.0}}, {"a": {}, "b": {}})
        c = self.model.entre_padroes([r1, r2], "Ag", {"b": "Solo"})
        self.assertEqual(c.amostras, [("a", "a"), ("b", "Solo")])
        self.assertEqual(len(c.paineis), 1)
        self.assertEqual([s.rotulo for s in c.paineis[0].series], ["p1 · NIST", "p2 · BCR"])
        self.assertEqual(self.model.elementos(c), ["Fe", "Zn"])  # ordem de Z

    def test_entre_alvos_liga_amostras_pelo_nome_e_padroes_pelo_certificado(self):
        ag = [_resultado("x1", "NIST", {"ag01": {("Fe", 6.4): 10.0}}, {"ag01": {("Fe", 6.4): 1.0}}),
              _resultado("x2", "BCR", {"ag01": {("Fe", 6.4): 11.0}}, {"ag01": {}})]
        au = [_resultado("y1", "NIST", {"au01": {("Fe", 6.4): 9.0}, "au02": {("Fe", 6.4): 4.0}}, {"au01": {}, "au02": {}})]
        nomes = {"Ag": {"ag01": "Solo 1"}, "Au": {"au01": "solo 1 "}}
        c = self.model.entre_alvos({"Ag": ag, "Au": au}, nomes)

        self.assertEqual([p.titulo for p in c.paineis], ["Padrão NIST", "Padrão BCR"])
        nist = c.paineis[0]
        self.assertEqual([s.rotulo for s in nist.series], ["Ag", "Au"])
        self.assertEqual(nist.series[1].cor, CORES_ALVOS["Au"])
        # au02 não tem nome e os códigos não têm data: liga pela ordem (Solo 1 com a 1ª do Au)
        self.assertEqual([r for _, r in c.amostras], ["Solo 1", "au02"])
        chave_solo = c.amostras[0][0]
        self.assertEqual(nist.series[0].valores[chave_solo]["Fe"], (10.0, 1.0))
        self.assertEqual(nist.series[1].valores[chave_solo]["Fe"], (9.0, 0.0))
        self.assertTrue(c.avisos)

    def _alvos(self, codigos_ag, codigos_au):
        def resultado(codigos):
            concs = {c: {("Fe", 6.4): float(i + 1)} for i, c in enumerate(codigos)}
            return [_resultado("p", "NIST", concs, {c: {} for c in codigos})]
        return {"Ag": resultado(codigos_ag), "Au": resultado(codigos_au)}

    def test_sem_ficha_liga_pelas_letras_depois_da_data(self):
        c = self.model.entre_alvos(self._alvos(["251026ab", "251026ac"], ["261026ac", "261026ab"]))
        self.assertEqual(len(c.amostras), 2)  # ab com ab, ac com ac, mesmo fora de ordem
        ag, au = c.paineis[0].series
        self.assertEqual(ag.valores[("sufixo", "ab")]["Fe"][0], 1.0)  # 251026ab é a 1ª do Ag
        self.assertEqual(au.valores[("sufixo", "ab")]["Fe"][0], 2.0)  # 261026ab é a 2ª do Au
        self.assertIn("letras", c.avisos[0])

    def test_sem_ficha_nem_letras_em_comum_liga_pela_ordem(self):
        c = self.model.entre_alvos(self._alvos(["251026ab", "251026ac"], ["261026xa", "261026xb"]))
        self.assertEqual([r for _, r in c.amostras], ["251026ab", "251026ac"])
        _, au = c.paineis[0].series
        self.assertEqual(au.valores[("ordem", 0)]["Fe"][0], 1.0)  # a primeira do Au com a primeira do Ag
        self.assertIn("ordem", c.avisos[0])

    def test_figura_e_exportacao(self):
        r1 = _resultado("p1", "NIST", {"a": {("Fe", 6.4): 20000.0}}, {"a": {("Fe", 6.4): 500.0}})
        r2 = _resultado("p2", "BCR", {"a": {("Fe", 6.4): 21000.0}}, {"a": {}})
        c = self.model.entre_padroes([r1, r2], "Ag")
        for estilo in ("barras", "linhas"):
            figura = self.model.criar_figura(c, "Fe", estilo, "escuro")
            self.assertEqual(figura.axes[0].get_ylabel(), "Fe, g/kg")  # acima de 10 000 mg/kg
        with tempfile.TemporaryDirectory() as pasta:
            gravados = self.model.exportar(pasta, c, "linhas")
            self.assertEqual([os.path.basename(g) for g in gravados], ["26 Fe - padroes.png"])
            self.assertTrue(os.path.exists(gravados[0]))


if __name__ == "__main__":
    unittest.main()
