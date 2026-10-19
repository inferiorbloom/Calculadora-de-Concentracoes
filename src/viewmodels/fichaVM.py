import os
from tkinter import filedialog, messagebox

from models.configModel import carregar_ultimo_diretorio, salvar_ultimo_diretorio
from models.fichaInformacaoModel import FichaInvalidaError, codigo_amostra, ler_ficha
from views.fichaView import NomesAmostrasDialog


class FichaVM:
    """
    Ficha de informação de UM alvo: lê o .docx, abre a revisão dos nomes e guarda o resultado
    em variaveis.nomes_amostras ({código: nome}).
    obter_arquivos(): caminhos da lista de arquivos; ao_alterar(): chamado quando os nomes mudam.
    """

    def __init__(self, master, variaveis, obter_arquivos, ao_alterar):
        self.master = master
        self.variaveis = variaveis
        self.obter_arquivos = obter_arquivos
        self.ao_alterar = ao_alterar
        self.ficha = {}  # última ficha lida: {código: {nome, descricao, obs, grupo, texto}}
        self.arquivo_ficha = None

    def ler_ficha(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar ficha de informação",
            filetypes=[("Documentos do Word", "*.docx"), ("Todos os arquivos", "*.*")],
            initialdir=carregar_ultimo_diretorio() or "",
        )
        if not caminho:
            return
        salvar_ultimo_diretorio(caminho)

        try:
            ficha = ler_ficha(caminho)
        except FichaInvalidaError as erro:
            messagebox.showerror("Ficha de informação", str(erro))
            return
        if not ficha:
            messagebox.showwarning(
                "Ficha de informação",
                f"Nenhuma medida encontrada em {os.path.basename(caminho)}.\n\n"
                "As linhas precisam começar pelo código da medida, ex.: \"041125ad – S2 (Solo)\".",
            )
            return

        self.ficha, self.arquivo_ficha = ficha, caminho
        # a ficha nova manda; nomes digitados para códigos que não estão nela continuam
        nomes = dict(self.variaveis.nomes_amostras)
        nomes.update({codigo: info["nome"] for codigo, info in ficha.items()})
        self._abrir_revisao(nomes)

    def editar_nomes(self):
        self._abrir_revisao(self.variaveis.nomes_amostras)

    def _abrir_revisao(self, nomes):
        codigos_arquivos = list(dict.fromkeys(codigo_amostra(os.path.basename(c)) for c in self.obter_arquivos()))

        def texto_ficha(codigo):
            if not self.ficha:
                return ""  # nenhuma ficha lida: nada a avisar
            info = self.ficha.get(codigo)
            return info["texto"] if info else None

        linhas = [(c, nomes.get(c, ""), texto_ficha(c)) for c in codigos_arquivos]
        extras = [
            (c, nomes.get(c, ""), texto_ficha(c))
            for c in dict.fromkeys([*self.ficha, *nomes])
            if c not in codigos_arquivos
        ]

        titulo = f"Ficha: {os.path.basename(self.arquivo_ficha)}" if self.arquivo_ficha else "Nenhuma ficha lida"
        NomesAmostrasDialog(self.master, titulo, linhas, extras, self._salvar)

    def _salvar(self, nomes):
        self.variaveis.nomes_amostras = nomes
        self.ao_alterar()
