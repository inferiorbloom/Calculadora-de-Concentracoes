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


if __name__ == "__main__":
    unittest.main()
