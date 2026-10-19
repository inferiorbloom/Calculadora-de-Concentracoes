import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models.PadraoModel import padroes_semelhantes

PADROES = os.path.join(os.path.dirname(__file__), "..", "padroes", "padroes.json")


def _padrao(nome, valores, unidade="mg/kg"):
    return {"nome": nome, "elementos": {el: {"valor": v, "unidade": unidade} for el, v in valores.items()}}


MONTANA_MG = _padrao("b) Montana Soil - 2710", {"Al": 64400, "K": 21100, "Ca": 12500, "Fe": 33800, "Cr": 39})


class PadroesSemelhantesTests(unittest.TestCase):
    def test_nome_igual_ignorando_prefixo_hifen_e_maiusculas(self):
        novo = _padrao("a) MONTANA soil 2710", {"Zn": 1})
        self.assertEqual(padroes_semelhantes(novo, [MONTANA_MG]), [("b) Montana Soil - 2710", ["nome parecido"])])

    def test_mesmos_valores_em_outra_unidade_com_outro_nome(self):
        novo = _padrao("Solo de referência", {"Al": 64.4, "K": 21.1, "Ca": 12.5, "Fe": 33.8}, "g/kg")
        resultado = padroes_semelhantes(novo, [MONTANA_MG])
        self.assertEqual(len(resultado), 1)
        self.assertIn("4 de 4 elementos", resultado[0][1][0])

    def test_valores_diferentes_e_nome_diferente_nao_avisa(self):
        novo = _padrao("Tomato Leaves", {"Al": 598, "K": 27000, "Ca": 50500})
        self.assertEqual(padroes_semelhantes(novo, [MONTANA_MG]), [])

    def test_poucos_elementos_iguais_nao_bastam(self):
        novo = _padrao("Outro solo", {"Al": 64400, "K": 21100, "Ca": 999, "Fe": 999})
        self.assertEqual(padroes_semelhantes(novo, [MONTANA_MG]), [])

    def test_padroes_do_laboratorio_nao_se_acusam_entre_si(self):
        with open(PADROES, encoding="utf-8") as arquivo:
            padroes = json.load(arquivo)
        for padrao in padroes:
            outros = [p for p in padroes if p is not padrao]
            self.assertEqual(padroes_semelhantes(padrao, outros), [], padrao["nome"])


if __name__ == "__main__":
    unittest.main()
