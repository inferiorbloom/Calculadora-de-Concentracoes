import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.analiseModel import (
    AnaliseInvalidaError,
    abrir_analise,
    escolhas_graficos_de_json,
    escolhas_graficos_para_json,
    salvar_analise,
)
from models.qualidadeModel import abaixo_do_ld, ld_de_referencia, recuperacao, recuperacao_fora
from models.sensibilidadeModel import SensibilidadeModel, familia_da_linha


class QualidadeTests(unittest.TestCase):
    def test_ld_da_amostra_depois_do_padrao_depois_qualquer_um(self):
        ld = {"a": {"Fe": 1.0}, "pd": {"Fe": 2.0, "Zn": 3.0}, "b": {"Cu": 4.0}}
        self.assertEqual(ld_de_referencia(ld, "a", "Fe", "pd"), 1.0)
        self.assertEqual(ld_de_referencia(ld, "a", "Zn", "pd"), 3.0)
        self.assertEqual(ld_de_referencia(ld, "a", "Cu", "pd"), 4.0)
        self.assertIsNone(ld_de_referencia(ld, "a", "Ni", "pd"))
        self.assertIsNone(ld_de_referencia({}, "a", "Fe", "pd"))

    def test_abaixo_do_ld_e_estrito(self):
        self.assertTrue(abaixo_do_ld(0.9, 1.0))
        self.assertFalse(abaixo_do_ld(1.0, 1.0))
        self.assertFalse(abaixo_do_ld(0.5, None))
        self.assertFalse(abaixo_do_ld("", 1.0))

    def test_recuperacao_converte_as_unidades(self):
        # medido 1,2 g/kg contra certificado 1000 mg/kg: 120%
        self.assertAlmostEqual(recuperacao(1.2, "g/kg", {"valor": 1000, "unidade": "mg/kg"}), 120.0)
        self.assertIsNone(recuperacao(1.2, "g/kg", None))
        self.assertIsNone(recuperacao(None, "g/kg", {"valor": 1, "unidade": "g/kg"}))
        self.assertTrue(recuperacao_fora(120.0))
        self.assertFalse(recuperacao_fora(95.0))
        self.assertFalse(recuperacao_fora(None))


class SensibilidadePorZTests(unittest.TestCase):
    def test_familia_k_ou_l_pela_energia(self):
        self.assertEqual(familia_da_linha(26, 6.399), "K")  # Fe Kα
        self.assertEqual(familia_da_linha(82, 10.55), "L")  # Pb Lα
        self.assertEqual(familia_da_linha(47, 22.1), "K")  # Ag Kα
        self.assertEqual(familia_da_linha(47, 2.98), "L")  # Ag Lα

    def test_pontos_so_das_linhas_com_valor_certificado(self):
        from models.resultadoPadraoModel import ResultadoPadrao

        r = ResultadoPadrao("pd", "pd.txt", {"elementos": {"Fe": {"valor": 2.0, "unidade": "g/kg"}}}, {}, {}, {}, {},
                            {("Fe", 6.399): 1000.0, ("Zn", 8.6): 50.0, ("Ar", 2.957): 10.0}, {})
        pontos = SensibilidadeModel().pontos_do_padrao(r, "10")
        self.assertEqual(pontos, [(26, "Fe", 6.399, "K", 50.0)])  # (1000 / 10) / 2


class AnaliseSalvaTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        self.dados = os.path.join(self.pasta, "dados")
        os.makedirs(self.dados)
        for nome in ("a.txt", "b.txt", "a.pdf"):
            open(os.path.join(self.dados, nome), "w").close()

    def _estado(self):
        return {"Ag": {
            "linhas": [
                {"arquivo": os.path.join(self.dados, "a.txt"), "padrao": True, "amostra": False, "certificado": "X",
                 "pdf": os.path.join(self.dados, "a.pdf")},
                {"arquivo": os.path.join(self.dados, "b.txt"), "padrao": False, "amostra": True, "certificado": "",
                 "pdf": None},
            ],
            "nomes": {"b": "Folha"}, "calculado": True, "graficos": {},
        }}

    def test_ida_e_volta(self):
        caminho = os.path.join(self.pasta, "x.cxa")
        salvar_analise(caminho, self._estado(), "Ag")
        dados, faltando = abrir_analise(caminho)
        self.assertEqual(faltando, [])
        self.assertEqual(dados["aba_aberta"], "Ag")
        linhas = dados["abas"]["Ag"]["linhas"]
        self.assertEqual([os.path.basename(linha["arquivo"]) for linha in linhas], ["a.txt", "b.txt"])
        self.assertEqual(os.path.basename(linhas[0]["pdf"]), "a.pdf")
        self.assertEqual(dados["abas"]["Ag"]["nomes"], {"b": "Folha"})

    def test_pasta_copiada_acha_pelo_caminho_relativo(self):
        caminho = os.path.join(self.pasta, "x.cxa")
        salvar_analise(caminho, self._estado())
        nova = os.path.join(self.pasta, "copia")
        shutil.copytree(self.dados, os.path.join(nova, "dados"))
        shutil.copy(caminho, nova)
        shutil.rmtree(self.dados)
        dados, faltando = abrir_analise(os.path.join(nova, "x.cxa"))
        self.assertEqual(faltando, [])
        self.assertTrue(dados["abas"]["Ag"]["linhas"][0]["arquivo"].startswith(nova))

    def test_arquivo_sumido_sai_da_lista_e_e_avisado(self):
        caminho = os.path.join(self.pasta, "x.cxa")
        salvar_analise(caminho, self._estado())
        os.remove(os.path.join(self.dados, "b.txt"))
        dados, faltando = abrir_analise(caminho)
        self.assertEqual(len(dados["abas"]["Ag"]["linhas"]), 1)
        self.assertEqual(len(faltando), 1)

    def test_arquivo_que_nao_e_analise(self):
        caminho = os.path.join(self.pasta, "x.cxa")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump({"outra": "coisa"}, f)
        with self.assertRaises(AnaliseInvalidaError):
            abrir_analise(caminho)

    def test_escolhas_dos_graficos_com_chave_de_tupla(self):
        traco = {"a": 2, ("area", "a"): 3}
        excluidos = {"a": {"majoritario": {"K"}, "traco": set()}}
        texto = json.loads(json.dumps(escolhas_graficos_para_json(traco, excluidos)))
        self.assertEqual(escolhas_graficos_de_json(texto), (traco, excluidos))


if __name__ == "__main__":
    unittest.main()
