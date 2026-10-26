import html
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.concentracaoModel import ConcentracaoModel
from models.abaSLDModel import AbaSLDModel
from models.exportarModel import ExportarModel
from models.propagacaoErrosModel import PropagacaoErrosModel
from models.resultadoPadraoModel import ResultadoPadrao

RAIZ = os.path.join(os.path.dirname(__file__), "..")
AQUISICOES = os.path.join(RAIZ, "aquisicoes")


def _padroes_certificados():
    with open(os.path.join(RAIZ, "padroes", "padroes.json"), encoding="utf-8") as f:
        return json.load(f)


def _calcular(amostras, arquivo_padrao, c_padrao):
    nome = os.path.splitext(os.path.basename(arquivo_padrao))[0]
    resultado = ResultadoPadrao(
        nome, arquivo_padrao, c_padrao, *ConcentracaoModel().calcular_concentracoes(amostras, arquivo_padrao, c_padrao)
    )
    resultado.erros_concentracao, resultado.unidade_padrao = PropagacaoErrosModel().calcular(
        resultado.concentracoes,
        resultado.areas_normalizadas,
        resultado.erros_normalizados,
        c_padrao,
        resultado.area_padrao,
        resultado.erro_padrao,
    )
    return resultado


def _textos_da_primeira_aba(caminho):
    """{(linha, coluna): texto} das células de texto da primeira aba (índices a partir de 0)."""
    with zipfile.ZipFile(caminho) as xlsx:
        compartilhadas = xlsx.read("xl/sharedStrings.xml").decode("utf-8")
        planilha = xlsx.read("xl/worksheets/sheet1.xml").decode("utf-8")
    textos = [html.unescape(t) for t in re.findall(r"<t[^>]*>([^<]*)</t>", compartilhadas)]
    celulas = {}
    for ref, indice in re.findall(r'<c r="([A-Z]+\d+)"[^>]*t="s"[^>]*><v>(\d+)</v>', planilha):
        letras, numero = re.match(r"([A-Z]+)(\d+)", ref).groups()
        coluna = 0
        for letra in letras:
            coluna = coluna * 26 + ord(letra) - 64
        celulas[(int(numero) - 1, coluna - 1)] = textos[int(indice)]
    return celulas


class NomesAbasTests(unittest.TestCase):
    def test_um_padrao_mantem_nomes_originais(self):
        abas = ExportarModel().nomes_abas("290426ab", varios_padroes=False)
        self.assertEqual(list(abas.values()), ExportarModel.ABAS)

    def test_varios_padroes_recebem_sufixo_valido_e_unico(self):
        model = ExportarModel()
        usados = set()
        abas_1 = model.nomes_abas("290426ab", True, usados)
        abas_2 = model.nomes_abas("um/nome:muito*longo?de[padrao]", True, usados)

        self.assertEqual(abas_1["Concentrações"], "Concentrações - 290426ab")
        todas = list(abas_1.values()) + list(abas_2.values())
        self.assertEqual(len({n.lower() for n in todas}), len(todas))
        for nome in todas:
            self.assertLessEqual(len(nome), 31)
            self.assertFalse(set(nome) & set(ExportarModel.CARACTERES_INVALIDOS_ABA))

    def test_nomes_repetidos_nao_colidem(self):
        model = ExportarModel()
        usados = set()
        abas_1 = model.nomes_abas("x" * 40, True, usados)
        abas_2 = model.nomes_abas("x" * 40, True, usados)
        self.assertNotEqual(abas_1["Concentrações"], abas_2["Concentrações"])


class ExportarVariosPadroesTests(unittest.TestCase):
    def test_cada_padrao_gera_suas_abas_sem_misturar_resultados(self):
        padroes = _padroes_certificados()
        amostras = [os.path.join(AQUISICOES, f"290426a{c}.txt") for c in "cdefg"]
        padrao_1 = _calcular(amostras, os.path.join(AQUISICOES, "290426ab.txt"), padroes[0])
        padrao_2 = _calcular(amostras, os.path.join(AQUISICOES, "290426ak.txt"), padroes[1])

        model = ExportarModel()
        model.mostrar_popup_sucesso = lambda caminho: None

        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "saida.xlsx")
            model.exportar_para_excel(amostras, [padrao_1, padrao_2], caminho)
            with zipfile.ZipFile(caminho) as xlsx:
                workbook = xlsx.read("xl/workbook.xml").decode("utf-8")
        abas = re.findall(r'<sheet name="([^"]+)"', workbook)

        esperadas = [ExportarModel.ABA_DADOS, ExportarModel.ABA_SLD]
        for resultado in (padrao_1, padrao_2):
            esperadas += list(model.nomes_abas(resultado.nome, True).values())
        self.assertEqual([html.unescape(a) for a in abas], esperadas)

        # cada padrão monta as suas tabelas só com os próprios resultados
        amostra = os.path.splitext(os.path.basename(amostras[0]))[0]
        conc_1 = model.montar_dataframes(amostras, padrao_1)[0]["Concentrações"].loc[amostra].dropna()
        conc_2 = model.montar_dataframes(amostras, padrao_2)[0]["Concentrações"].loc[amostra].dropna()
        for resultado, conc in ((padrao_1, conc_1), (padrao_2, conc_2)):
            esperado = sorted(float(v) for v in resultado.concentracoes["concentracao1"][amostra].values())
            self.assertEqual(sorted(float(v) for v in conc), esperado)
        self.assertFalse(conc_1.equals(conc_2))

    def test_dados_dos_padroes_ficam_lado_a_lado_na_mesma_aba(self):
        padroes = _padroes_certificados()
        amostras = [os.path.join(AQUISICOES, f"290426a{c}.txt") for c in "cd"]
        padrao_1 = _calcular(amostras, os.path.join(AQUISICOES, "290426ab.txt"), padroes[0])
        padrao_2 = _calcular(amostras, os.path.join(AQUISICOES, "290426ak.txt"), padroes[1])

        model = ExportarModel()
        model.mostrar_popup_sucesso = lambda caminho: None

        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "saida.xlsx")
            model.exportar_para_excel(amostras, [padrao_1, padrao_2], caminho)
            dados = _textos_da_primeira_aba(caminho)

        # cada padrão: "Padrão: ..." na linha 0; cada amostra com o nome em cima e o cabeçalho logo abaixo
        largura = len(model.aba_dados.CABECALHO)
        self.assertEqual(dados[(0, 0)], f"Padrão: {padrao_1.nome} ({padrao_1.nome_certificado})")
        self.assertEqual(dados[(0, largura + 1)], f"Padrão: {padrao_2.nome} ({padrao_2.nome_certificado})")
        self.assertFalse([c for c in dados if c[1] == largura])  # coluna separadora vazia
        amostra = os.path.splitext(os.path.basename(amostras[0]))[0]
        for coluna in (0, largura + 1):
            self.assertEqual(dados[(2, coluna)], amostra)
            self.assertEqual(dados[(2, coluna + largura - 2)], "Normalização:")
            self.assertEqual(dados[(3, coluna)], "Elemento")

    def test_sld_dos_padroes_em_colunas_na_mesma_tabela(self):
        padroes = _padroes_certificados()
        amostras = [os.path.join(AQUISICOES, f"290426a{c}.txt") for c in "cd"]
        padrao_1 = _calcular(amostras, os.path.join(AQUISICOES, "290426ab.txt"), padroes[0])
        padrao_2 = _calcular(amostras, os.path.join(AQUISICOES, "290426ak.txt"), padroes[1])
        padrao_1.sensibilidade_resultado = {"290426ac": {("K", 3.313): 1.5}}
        padrao_2.sensibilidade_resultado = {"290426ac": {("K", 3.313): 2.5}}

        aba_sld = AbaSLDModel()
        df = aba_sld.montar_varios(
            [(r.nome, r.resultado_limite, r.sensibilidade_resultado, r.concentracoes) for r in (padrao_1, padrao_2)]
        )
        self.assertEqual(
            list(df.columns),
            aba_sld.CHAVES + [aba_sld.coluna_do_padrao(v, r.nome) for r in (padrao_1, padrao_2) for v in aba_sld.VALORES],
        )
        self.assertFalse(df.duplicated(subset=aba_sld.CHAVES).any())  # uma linha por amostra/elemento/energia
        linha = df[(df["Amostra"] == "290426ac") & (df["Elemento"] == "K")].iloc[0]
        self.assertEqual(linha[aba_sld.coluna_do_padrao("Sensibilidade", padrao_1.nome)], 1.5)
        self.assertEqual(linha[aba_sld.coluna_do_padrao("Sensibilidade", padrao_2.nome)], 2.5)

    def test_sld_mostra_so_linhas_com_ld_ou_sensibilidade(self):
        concentracoes = {"concentracao1": {"a1": {("K", 3.313): 10, ("Ca", 3.69): 5, ("Fe", 6.4): 2}}}
        df = AbaSLDModel().montar({"a1": {"K": 0.4}}, {"a1": {("Ca", 3.69): 1.2}}, concentracoes)
        self.assertEqual(list(df["Elemento"]), ["K", "Ca"])  # Fe não tem LD nem sensibilidade


def _abas_do_arquivo(caminho):
    with zipfile.ZipFile(caminho) as xlsx:
        return [html.unescape(n) for n in re.findall(r'<sheet name="([^"]+)"', xlsx.read("xl/workbook.xml").decode("utf-8"))]


class NomeDaFichaEDestaquesTests(unittest.TestCase):
    def setUp(self):
        padroes = _padroes_certificados()
        self.amostras = [os.path.join(AQUISICOES, f"290426a{c}.txt") for c in "cde"]
        self.padrao_1 = _calcular(self.amostras, os.path.join(AQUISICOES, "290426ab.txt"), padroes[0])
        self.padrao_2 = _calcular(self.amostras, os.path.join(AQUISICOES, "290426ak.txt"), padroes[1])
        self.model = ExportarModel()
        self.model.mostrar_popup_sucesso = lambda caminho: None
        self.nomes = {"290426ab": "Pd Solo"}  # só o primeiro padrão tem nome na ficha

    def test_abas_com_o_nome_da_ficha_do_padrao(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "saida.xlsx")
            self.model.exportar_para_excel(
                self.amostras, [self.padrao_1, self.padrao_2], caminho, abas_exportar=["Concentrações"],
                nomes_amostras=self.nomes,
            )
            self.assertEqual(_abas_do_arquivo(caminho), ["Concentrações - Pd Solo", "Concentrações - 290426ak"])

            caminho = os.path.join(pasta, "todos.xlsx")
            self.model.exportar_todos_alvos({"Ag": [self.padrao_1, self.padrao_2]}, caminho, {"Ag": self.nomes})
            self.assertEqual(_abas_do_arquivo(caminho), ["Ag - Pd Solo", "Ag - 290426ak"])
            self.assertEqual(_textos_da_primeira_aba(caminho)[(0, 0)], "Padrão: Pd Solo · 290426ab (a) PS. Mexilhão)")

    def test_dados_com_nome_da_ficha_e_razao_do_alvo(self):
        nomes = {"290426ac": "R2"}
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "saida.xlsx")
            self.model.exportar_para_excel(
                self.amostras, [self.padrao_1], caminho, abas_exportar=["Dados"], nomes_amostras=nomes, alvo="Ag",
            )
            dados = _textos_da_primeira_aba(caminho)
            with zipfile.ZipFile(caminho) as xlsx:
                planilha = xlsx.read("xl/worksheets/sheet1.xml").decode("utf-8")

        self.assertEqual(dados[(0, 0)], "290426ac")
        self.assertEqual(dados[(0, 1)], "R2")
        self.assertIn('<mergeCell ref="B1:D1"/>', planilha)
        self.assertEqual(dados[(0, 4)], "Razão Ag:")
        self.assertEqual(dados[(0, 6)], "Normalização:")

    def test_razao_das_linhas_de_cada_alvo(self):
        from models.abaDadosModel import razao_do_alvo
        from models.leitorArquivoModel import Pico

        picos = [Pico(47, 2.984, 1000, 10), Pico(47, 22.103, 250, 5), Pico(45, 2.696, 300, 3), Pico(45, 20.167, 100, 2),
                 Pico(79, 9.707, 900, 9), Pico(78, 9.434, 300, 3)]
        self.assertAlmostEqual(razao_do_alvo(picos, "Ag"), 4.0)
        self.assertAlmostEqual(razao_do_alvo(picos, "Rh"), 3.0)
        self.assertAlmostEqual(razao_do_alvo(picos, "Au"), 3.0)
        self.assertEqual(razao_do_alvo(picos[:1], "Ag"), "-")  # sem a linha K
        self.assertEqual(razao_do_alvo(picos, "X"), "-")

    def test_destaques_seguem_a_regra_da_tabela(self):
        r = self.padrao_1
        amostra = "290426ac"
        r.resultado_limite = {amostra: {"K": 1e9}}  # K de 290426ac fica ≤ 3×LD
        classes = self.model._classes(r)
        chave_k = next(c for c in r.concentracoes["concentracao1"][amostra] if c[0] == "K")
        self.assertIn(classes[(amostra, chave_k)], ("abaixo_ld", "ambos"))

        elementos = sorted({c for b in r.concentracoes.values() for v in b.values() for c in v})
        destaques = self.model._destaques(r, [amostra], elementos, 1, 2)
        k = elementos.index(chave_k)
        self.assertIn(destaques[(0, 1 + 2 * k)], ("abaixo_ld", "ambos"))
        self.assertEqual(destaques[(0, 1 + 2 * k)], destaques[(0, 2 + 2 * k)])  # C e Erro juntos

        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "saida.xlsx")
            self.model.exportar_para_excel(self.amostras, [r], caminho, abas_exportar=["Resultados"])
            with zipfile.ZipFile(caminho) as xlsx:
                self.assertIn("F8D7DA", xlsx.read("xl/styles.xml").decode("utf-8").upper())
            self.assertIn("Valor ≤ 3×LD", _textos_da_primeira_aba(caminho).values())


if __name__ == "__main__":
    unittest.main()
