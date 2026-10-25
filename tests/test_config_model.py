import importlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import configModel


class ConfigModelTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        configModel.CONFIG_FILE = os.path.join(self.temp_dir.name, "config.json")
        if os.path.exists(configModel.CONFIG_FILE):
            os.remove(configModel.CONFIG_FILE)

    def test_carregar_ultimo_diretorio_retorna_none_quando_nao_existe(self):
        self.assertIsNone(configModel.carregar_ultimo_diretorio())

    def test_salvar_e_carregar_ultimo_diretorio(self):
        pasta = os.path.join(self.temp_dir.name, "FRX", "Padrões")
        os.makedirs(pasta)
        configModel.salvar_ultimo_diretorio(pasta)

        self.assertEqual(configModel.carregar_ultimo_diretorio(), os.path.normpath(pasta))

    def test_arquivo_que_ainda_nao_existe_guarda_a_pasta_dele(self):
        # o "Salvar como" devolve o caminho da planilha antes de ela ser criada
        configModel.salvar_ultimo_diretorio(os.path.join(self.temp_dir.name, "amostras_Ag.xlsx"))

        self.assertEqual(configModel.carregar_ultimo_diretorio(), os.path.normpath(self.temp_dir.name))

    def test_pasta_que_deixou_de_existir_nao_e_devolvida(self):
        pasta = os.path.join(self.temp_dir.name, "pendrive")
        os.makedirs(pasta)
        configModel.salvar_ultimo_diretorio(pasta)
        os.rmdir(pasta)

        self.assertIsNone(configModel.carregar_ultimo_diretorio())

    def test_configuracao_antiga_com_caminho_de_arquivo_e_ignorada(self):
        # como ficava gravado antes da correção
        configModel._gravar_config(ultimo_diretorio=os.path.join(self.temp_dir.name, "amostras.xlsx"))

        self.assertIsNone(configModel.carregar_ultimo_diretorio())

    def test_tempo_de_contagem_fica_como_foi_digitado(self):
        self.assertEqual(configModel.carregar_tempo_contagem(), "")
        configModel.salvar_tempo_contagem("100,5")
        self.assertEqual(configModel.carregar_tempo_contagem(), "100,5")

    def test_certificado_lembrado_por_alvo_e_arquivo(self):
        configModel.salvar_certificado("Ag", "290426ab.txt", "Mexilhão")
        configModel.salvar_certificado("Au", "290426ab.txt", "Ipê")
        self.assertEqual(configModel.carregar_certificados("Ag"), {"arquivos": {"290426ab.txt": "Mexilhão"}, "ultimo": "Mexilhão"})
        self.assertEqual(configModel.carregar_certificados("Au")["arquivos"]["290426ab.txt"], "Ipê")
        self.assertEqual(configModel.carregar_certificados("Rh"), {"arquivos": {}, "ultimo": None})

    def test_menor_ld_desligado_por_padrao(self):
        self.assertFalse(configModel.carregar_mostrar_menor_ld())
        configModel.salvar_mostrar_menor_ld(True)
        self.assertTrue(configModel.carregar_mostrar_menor_ld())

    def test_formato_de_imagem(self):
        self.assertEqual(configModel.carregar_formato_imagem(), "png")
        configModel.salvar_formato_imagem("svg")
        configModel.salvar_formato_imagem("bmp")  # inválido: ignorado
        self.assertEqual(configModel.carregar_formato_imagem(), "svg")


if __name__ == "__main__":
    unittest.main()
