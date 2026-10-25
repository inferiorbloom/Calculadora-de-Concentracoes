"""
Fluxo da aba de um alvo com a janela de verdade (escondida): seleciona os arquivos, marca o padrão, calcula,
exporta, muda a seleção (resultados desatualizados) e salva/abre a análise. Os diálogos são respondidos aqui.
Sem tela (Tk não abre), os testes são pulados.
"""

import glob
import os
import shutil
import sys
import tempfile
import tkinter
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import configModel

RAIZ = os.path.join(os.path.dirname(__file__), "..")


class FluxoAbaAlvoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            tkinter.Tk().destroy()
        except tkinter.TclError as erro:
            raise unittest.SkipTest(f"sem tela para o Tk: {erro}") from erro

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        configuracao = mock.patch.object(configModel, "CONFIG_FILE", os.path.join(self.pasta, "config.json"))
        configuracao.start()
        self.addCleanup(configuracao.stop)

        self.mensagens = []
        self.respostas = {"askyesno": True}
        for nome in ("showinfo", "showwarning", "showerror", "askyesno"):
            patch = mock.patch.object(messagebox, nome, side_effect=self._mensagem(nome))
            patch.start()
            self.addCleanup(patch.stop)
        self.dialogos = {}
        for nome, chave in (("asksaveasfilename", "salvar"), ("askopenfilename", "abrir"), ("askdirectory", "pasta")):
            patch = mock.patch.object(filedialog, nome, side_effect=lambda *a, c=chave, **k: self.dialogos.get(c, ""))
            patch.start()
            self.addCleanup(patch.stop)

        from views.mainView import MainView

        self.app = MainView()
        self.app.withdraw()
        self.addCleanup(self._fechar)
        self.vm = self.app.calculo_vm
        self.lista = self.vm.lista_arquivos_view
        self.dados = os.path.join(self.pasta, "dados")
        shutil.copytree(os.path.join(RAIZ, "aquisicoes"), self.dados)
        self.arquivos = sorted(glob.glob(os.path.join(self.dados, "*.txt")))

    def _fechar(self):
        """
        Os "after" pendentes do customtkinter disparam depois do destroy e o Tcl reclama no stderr;
        um bgerror vazio só tira esse ruído da saída dos testes.
        """
        self.app.tk.eval("proc bgerror {args} {}")
        self.app.destroy()

    def _mensagem(self, nome):
        def responder(titulo=None, texto=None, **_):
            self.mensagens.append((nome, titulo, texto))
            return self.respostas.get(nome, "ok")
        return responder

    def _marcar_padrao(self, indice, certificado):
        self.lista.linhas[indice][1].set(True)
        self.lista._marcar_padrao(indice)
        self.lista.combos_padrao[indice].set(certificado)
        self.lista._notificar()

    def _calcular(self):
        self.vm.receber_arquivos(self.arquivos)
        self._marcar_padrao(0, self.vm.padrao_vm.nomes_padroes()[0])
        self.assertEqual(self.vm.view.status.cget("text"), "Pronto para calcular (F5).")
        self.vm.calcular()

    def test_status_guia_o_usuario_ate_calcular(self):
        self.assertIn("Selecione os arquivos", self.vm.view.status.cget("text"))
        self.vm.receber_arquivos(self.arquivos)
        self.assertEqual(self.vm.view.status.cget("text"), "Marque um arquivo como Padrão.")
        self.assertEqual(str(self.vm.view.calcular.cget("state")), "disabled")
        self._calcular()
        self.assertTrue(self.vm.resultados_por_padrao)
        self.assertTrue(self.vm.view.status.cget("text").startswith("Calculado"))

    def test_exporta_e_avisa_quando_a_selecao_muda_depois_do_calcular(self):
        self._calcular()
        self.dialogos["salvar"] = os.path.join(self.pasta, "saida.xlsx")
        self.vm.export.exporta_excel()
        self.assertTrue(os.path.exists(self.dialogos["salvar"]))

        self.lista.linhas[3][2].set(False)  # desmarca uma amostra
        self.lista._notificar()
        self.assertTrue(self.vm.desatualizado())
        self.assertIn("mudou", self.vm.barra_avisos.faixa.cget("text"))
        self.assertIn("desatualizado", self.app.abas_laterais.abas["Ag"].subtitulo.cget("text"))

        self.respostas["askyesno"] = False  # "não exportar"
        os.remove(self.dialogos["salvar"])
        self.vm.export.exporta_excel()
        self.assertFalse(os.path.exists(self.dialogos["salvar"]))

        self.lista.linhas[3][2].set(True)  # voltou ao que foi calculado
        self.lista._notificar()
        self.assertFalse(self.vm.desatualizado())

    def test_lembra_o_certificado_do_arquivo_padrao(self):
        nomes = self.vm.padrao_vm.nomes_padroes()
        self.vm.receber_arquivos(self.arquivos)
        self._marcar_padrao(0, nomes[1])
        self.vm.calcular()
        # lista nova: o mesmo arquivo marcado como padrão volta com o certificado usado da última vez
        self.lista.restaurar([{"arquivo": c, "padrao": False, "amostra": True} for c in self.arquivos])
        self.lista.linhas[0][1].set(True)
        self.lista._marcar_padrao(0)
        self.assertEqual(self.lista.combos_padrao[0].get(), nomes[1])

    def test_arrastar_txt_e_pdf(self):
        self.vm.receber_arquivos(self.arquivos[:3])
        pdf = os.path.join(self.pasta, os.path.basename(self.arquivos[1])[:-4] + ".pdf")
        open(pdf, "wb").close()
        self.vm.receber_arquivos(self.arquivos[2:5] + [pdf])
        self.assertEqual(len(self.lista.linhas), 5)  # o repetido não entra de novo
        self.assertEqual(self.lista.pdfs, {1: pdf})

    def _ordem_da_lista(self):
        return [os.path.basename(caminho) for caminho, _, _ in self.lista.linhas]

    def test_arquivos_soltos_entram_em_ordem_de_nome(self):
        embaralhados = [self.arquivos[i] for i in (4, 0, 7, 2, 9, 1)]
        self.vm.receber_arquivos(embaralhados)
        self.assertEqual(self._ordem_da_lista(), sorted(os.path.basename(c) for c in embaralhados))

    def test_ordenar_pelo_cabecalho_mantem_marcacoes_e_nao_desatualiza(self):
        self.vm.receber_arquivos(self.arquivos)
        self._marcar_padrao(0, self.vm.padrao_vm.nomes_padroes()[0])
        pdf = os.path.join(self.pasta, "qualquer.pdf")
        open(pdf, "wb").close()
        self.lista.definir_pdf(3, pdf)
        self.vm.calcular()
        arquivo_com_pdf = self._ordem_da_lista()[3]

        self.lista.ordenar("arquivo")  # já estava em ordem crescente: inverte
        self.assertEqual(self._ordem_da_lista(), sorted(self._ordem_da_lista(), reverse=True))
        self.assertEqual(self.lista.ordem, ("arquivo", True))
        estado = {os.path.basename(linha["arquivo"]): linha for linha in self.lista.estado()}
        self.assertTrue(estado["290426ab.txt"]["padrao"])
        self.assertEqual(estado[arquivo_com_pdf]["pdf"], pdf)
        self.assertFalse(self.vm.desatualizado())

        # pelo nome da ficha: F10 depois de F2; quem não tem nome vai para o fim
        self.vm.variaveis.nomes_amostras.update({"290426ac": "F10", "290426ad": "F2", "290426ae": "F1"})
        self.vm._nomes_alterados()
        self.lista.ordenar("nome")
        self.assertEqual(self._ordem_da_lista()[:3], ["290426ae.txt", "290426ad.txt", "290426ac.txt"])

    def test_vincular_pdfs_pela_pasta_do_txt(self):
        self.vm.receber_arquivos(self.arquivos)
        pdf = os.path.join(self.dados, os.path.basename(self.arquivos[2])[:-4].upper() + ".PDF")
        open(pdf, "wb").close()
        self.respostas["askyesno"] = False  # não procurar em outra pasta
        self.vm.vincular_pdfs()
        self.assertEqual(self.lista.pdfs, {2: pdf})

    def test_salvar_e_abrir_a_analise_recalcula(self):
        self._calcular()
        self.vm.resultados_por_padrao[0].graficos_traco["290426ad"] = 2
        self.vm.view.tempo_contagem.delete(0, "end")
        self.vm.view.tempo_contagem.insert(0, "120")
        self.dialogos["salvar"] = os.path.join(self.pasta, "analise.cxa")
        self.app.salvar_analise()

        self.lista.restaurar([])  # limpa a aba
        self.vm.resultados_por_padrao = []
        self.dialogos["abrir"] = self.dialogos["salvar"]
        self.app.abrir_analise()
        self.assertEqual(len(self.lista.linhas), len(self.arquivos))
        self.assertTrue(self.vm.resultados_por_padrao)
        self.assertEqual(self.vm.resultados_por_padrao[0].graficos_traco.get("290426ad"), 2)
        self.assertEqual(self.vm.view.tempo_contagem.get(), "120")

    def test_menor_ld_vai_para_o_excel_quando_ligado(self):
        self._calcular()
        r = self.vm.resultados_por_padrao[0]
        r.resultado_limite = {nome: {"K": 1e12} for nome in r.areas_normalizadas}  # tudo abaixo do LD
        configModel.salvar_mostrar_menor_ld(True)
        self.dialogos["salvar"] = os.path.join(self.pasta, "ld.xlsx")
        self.vm.export.exporta_excel()
        with zipfile.ZipFile(self.dialogos["salvar"]) as xlsx:
            self.assertIn("&lt; LD", xlsx.read("xl/sharedStrings.xml").decode("utf-8"))

    def test_atalho_f5_calcula(self):
        self.vm.receber_arquivos(self.arquivos)
        self._marcar_padrao(0, self.vm.padrao_vm.nomes_padroes()[0])
        evento = mock.Mock(widget=self.app, state=0)
        self.app._atalho(evento, self.app._atalho_calcular)
        self.assertTrue(self.vm.resultados_por_padrao)


if __name__ == "__main__":
    unittest.main()
