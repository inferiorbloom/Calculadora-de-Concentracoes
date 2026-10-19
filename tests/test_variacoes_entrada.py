"""Variações de entrada do usuário: arquivos fora do formato esperado, vírgula decimal, unidades."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.concentracaoModel import ConcentracaoModel
from models.graficosModel import GraficosModel
from models.leitorArquivoModel import ArquivoInvalidoError, ler_picos, nome_amostra
from models.sensibilidadeModel import SensibilidadeModel

CABECALHO = (
    "Acquisition date and time: 00-00-   0 (00:00:00)\n"
    "Live Time:,        0\n"
    "Real Time:,        0\n"
    " \n"
    "Photopeaks:,    3\n"
)
PICOS = (
    "  18,      2.957,      11742,        245,      21.64\n"
    "  19,      3.313,      70698,        306,      16.89\n"
    "  26,      6.399,      50000,        250,      10.00\n"
)
CERTIFICADO = {
    "nome": "Teste",
    "elementos": {
        "K": {"valor": 10.0, "erro": 1.0, "unidade": "g/kg"},
        "Fe": {"valor": 500.0, "erro": 20.0, "unidade": "mg/kg"},
    },
}


class _ComArquivos(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)

    def arquivo(self, nome, texto, encoding="utf-8", newline=None):
        caminho = os.path.join(self.pasta.name, nome)
        with open(caminho, "w", encoding=encoding, newline=newline) as f:
            f.write(texto)
        return caminho


class LeitorArquivoTests(_ComArquivos):
    def picos(self, texto, **kw):
        return [(p.elemento, p.energia, p.area) for p in ler_picos(self.arquivo("a.txt", texto, **kw))]

    def test_formato_do_equipamento(self):
        self.assertEqual(
            self.picos(CABECALHO + PICOS),
            [("Ar", 2.957, 11742.0), ("K", 3.313, 70698.0), ("Fe", 6.399, 50000.0)],
        )

    def test_linhas_em_branco_e_espacos_no_fim(self):
        self.assertEqual(self.picos(CABECALHO + PICOS + "\n   \n\n"), self.picos(CABECALHO + PICOS))

    def test_cabecalho_com_mais_ou_menos_linhas_nao_perde_picos(self):
        esperado = self.picos(CABECALHO + PICOS)
        self.assertEqual(self.picos("Linha extra\n" + CABECALHO + PICOS), esperado)
        self.assertEqual(self.picos(CABECALHO.split("\n", 1)[1] + PICOS), esperado)
        self.assertEqual(self.picos(PICOS), esperado)

    def test_crlf_e_bom(self):
        self.assertEqual(
            self.picos(CABECALHO + PICOS, encoding="utf-8-sig", newline="\r\n"), self.picos(CABECALHO + PICOS)
        )

    def test_ponto_e_virgula_com_virgula_decimal(self):
        texto = CABECALHO.replace(",", ";") + PICOS.replace(",", ";").replace(".", ",")
        self.assertEqual(self.picos(texto), self.picos(CABECALHO + PICOS))

    def test_z_fora_da_tabela_e_lido_sem_simbolo(self):
        picos = ler_picos(self.arquivo("a.txt", PICOS + "  99,  1.0,  10,  1,  1\n"))
        self.assertIsNone(picos[-1].elemento)

    def test_linha_de_pico_quebrada_diz_arquivo_e_linha(self):
        caminho = self.arquivo("quebrado.txt", CABECALHO + PICOS + "  20,  3.691,  abc,  10,  1\n")
        with self.assertRaises(ArquivoInvalidoError) as ctx:
            ler_picos(caminho)
        self.assertIn("quebrado.txt, linha 9", str(ctx.exception))

    def test_arquivo_sem_picos(self):
        with self.assertRaises(ArquivoInvalidoError):
            ler_picos(self.arquivo("vazio.txt", ""))

    def test_nome_amostra(self):
        self.assertEqual(nome_amostra(r"C:\dados\290426ab .TXT"), "290426ab")


class ConcentracaoVariacoesTests(_ComArquivos):
    def calcular(self, amostra_txt, padrao_txt=CABECALHO + PICOS):
        model = ConcentracaoModel()
        resultado = model.calcular_concentracoes(
            [self.arquivo("amostra.txt", amostra_txt)], self.arquivo("padrao.txt", padrao_txt), CERTIFICADO
        )
        return resultado, model.avisos

    def test_concentracao_e_numero_sem_corte_de_casas(self):
        amostra = PICOS.replace("70698", "70699")
        (conc, *_), avisos = self.calcular(CABECALHO + amostra)
        valor = conc["concentracao1"]["amostra"][("K", 3.313)]
        self.assertIsInstance(valor, float)
        self.assertAlmostEqual(valor, 10.0 * 70699 / 70698, places=12)
        self.assertEqual(avisos, [])

    def test_amostra_sem_ar_avisa_e_nao_normaliza(self):
        sem_ar = "\n".join(linha for linha in PICOS.split("\n") if not linha.strip().startswith("18,"))
        (conc, _, fatores, *_), avisos = self.calcular(sem_ar)
        self.assertNotIn("amostra", fatores)
        self.assertTrue(any("amostra não tem pico de Ar" in a for a in avisos))

    def test_padrao_sem_ar_avisa(self):
        sem_ar = "\n".join(linha for linha in PICOS.split("\n") if not linha.strip().startswith("18,"))
        _, avisos = self.calcular(PICOS, padrao_txt=sem_ar)
        self.assertTrue(any("padrão padrao não tem pico de Ar" in a for a in avisos))

    def test_area_zero_no_padrao_nao_divide_por_zero(self):
        (conc, *_), avisos = self.calcular(PICOS, padrao_txt=PICOS.replace("50000", "0"))
        self.assertNotIn(("Fe", 6.399), conc["concentracao1"]["amostra"])
        self.assertIn(("K", 3.313), conc["concentracao1"]["amostra"])
        self.assertTrue(any("Fe (6.399 keV)" in a for a in avisos))

    def test_z_desconhecido_e_ignorado_com_aviso(self):
        (conc, *_), avisos = self.calcular(PICOS + "  99,  1.0,  10,  1,  1\n")
        self.assertIn(("K", 3.313), conc["concentracao1"]["amostra"])
        self.assertTrue(any("Z = 99" in a for a in avisos))


class OutrasEntradasTests(unittest.TestCase):
    def test_tempo_com_virgula(self):
        resultado = SensibilidadeModel().calcular(
            {"b": {"x": {("K", 3.313): 1.0}}}, {"x": {("K", 3.313): 100.0}}, CERTIFICADO, "100,0"
        )
        self.assertAlmostEqual(resultado["x"][("K", 3.313)], (100.0 / 100.0) / 10.0)

    def test_tempo_invalido_explica(self):
        with self.assertRaises(ValueError) as ctx:
            SensibilidadeModel().calcular({}, {}, CERTIFICADO, "cem")
        self.assertIn("cem", str(ctx.exception))

    def test_graficos_convertem_para_mg_kg_e_juntam_linhas_do_mesmo_elemento(self):
        valores = GraficosModel.valores_em_mg_kg(
            {("K", 3.313): 2.0, ("Fe", 6.399): 300.0, ("Ag", 22.103): 4.0, ("Ag", 2.984): 6.0, ("Cu", 8.0): -1.0},
            {"K": "g/kg", "Fe": "mg/kg", "Ag": "mg/kg", "Cu": "mg/kg"},
        )
        self.assertEqual(valores, {"K": 2000.0, "Fe": 300.0, "Ag": 5.0})


if __name__ == "__main__":
    unittest.main()
