import customtkinter as ctk
from PIL import Image

from resource_utils import resource_path
from views import tema

# chave -> (título, subtítulo, ícone ou None). As três primeiras são os alvos do tubo de raios X;
# as duas últimas trabalham com todos os alvos juntos.
ALVOS = {
    "Ag": ("Ag", "Prata", None),
    "Au": ("Au", "Ouro", None),
    "Rh": ("Rh", "Ródio", None),
}
GERAIS = {
    "estatistica": ("Análise estatística", None, "graficos.png"),
    "exportar": ("Exportar", None, "excel.png"),
}

ATALHOS = (
    "Ctrl+O  arquivos\n"
    "F5  calcular\n"
    "Ctrl+E  Excel   ·   Ctrl+G  gráficos\n"
    "Ctrl+S  salvar análise\n"
    "Ctrl+Shift+O  abrir análise"
)

COR_FUNDO = tema.LATERAL
COR_HOVER = tema.HOVER_LATERAL
COR_SELECIONADA = tema.SELECIONADA
COR_DESTAQUE = tema.DESTAQUE  # barrinha da aba selecionada
COR_TEXTO = tema.TEXTO
COR_TEXTO_2 = tema.TEXTO_2
COR_APAGADA = tema.APAGADO


class _Aba(ctk.CTkFrame):
    """Uma aba da barra: um bloco clicável (não um botão), com a barrinha de destaque à esquerda."""

    def __init__(self, master, chave, titulo, subtitulo, icone, ao_clicar):
        # height pequeno: o CTkFrame tem 200 px por padrão e cresceria até isso em vez de seguir o conteúdo
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=8, cursor="hand2", height=10)
        self.chave = chave
        self.selecionada = False

        self.destaque = ctk.CTkFrame(self, width=4, height=10, fg_color=COR_FUNDO, corner_radius=2)
        self.destaque.pack(side="left", fill="y", padx=(0, 10), pady=8)

        imagem = None
        if icone:
            imagem = ctk.CTkImage(light_image=Image.open(resource_path("imagens", "icones", icone)), size=(18, 18))
        textos = ctk.CTkFrame(self, fg_color="transparent", height=10)
        textos.pack(side="left", fill="x", expand=True, pady=8)

        if subtitulo:  # alvo: símbolo grande + nome
            self.titulo = ctk.CTkLabel(textos, text=titulo, font=tema.fonte(20, "bold"), text_color=COR_TEXTO_2,
                                       anchor="w")
            self.subtitulo = ctk.CTkLabel(textos, text=subtitulo, font=tema.fonte(11), text_color=COR_APAGADA,
                                          anchor="w", height=14)
            self.titulo.pack(fill="x")
            self.subtitulo.pack(fill="x")
        else:  # geral: ícone + texto
            self.titulo = ctk.CTkLabel(textos, text=f"  {titulo}", image=imagem, compound="left",
                                       font=tema.fonte(13), text_color=COR_TEXTO_2, anchor="w")
            self.subtitulo = None
            self.titulo.pack(fill="x")

        # o clique e o hover valem em qualquer ponto da aba, inclusive sobre os textos
        for widget in self._todos(self):
            widget.bind("<Button-1>", lambda _e: ao_clicar(self.chave))
            widget.bind("<Enter>", lambda _e: self._hover(True))
            widget.bind("<Leave>", lambda _e: self._hover(False))

    @classmethod
    def _todos(cls, widget):
        yield widget
        for filho in widget.winfo_children():
            yield from cls._todos(filho)

    def _hover(self, dentro):
        if not self.selecionada:
            self.configure(fg_color=COR_HOVER if dentro else COR_FUNDO)

    def marcar(self, selecionada):
        self.selecionada = selecionada
        self.configure(fg_color=COR_SELECIONADA if selecionada else COR_FUNDO)
        self.destaque.configure(fg_color=COR_DESTAQUE if selecionada else COR_FUNDO)
        self.titulo.configure(text_color=COR_TEXTO if selecionada else COR_TEXTO_2)


class AbasLateraisView(ctk.CTkFrame):
    """
    Barra lateral com as abas dos alvos (Ag, Au, Rh) e das funções que usam todos eles
    (Análise estatística, Exportar). Por enquanto só troca a aba selecionada; ao_trocar(chave)
    é onde cada aba vai ganhar a sua função.
    """

    def __init__(self, master, ao_trocar=None, inicial="Ag", ao_abrir_analise=None, ao_salvar_analise=None):
        super().__init__(master, width=196, fg_color=COR_FUNDO, corner_radius=0)
        self.pack_propagate(False)
        self.ao_trocar = ao_trocar
        self.abas = {}
        self.selecionada = None

        # embaixo: a análise inteira (todos os alvos) em um arquivo, e os atalhos de teclado
        ctk.CTkLabel(
            self, text=ATALHOS, font=tema.fonte(10), text_color=COR_APAGADA, justify="left", anchor="w",
        ).pack(side="bottom", fill="x", padx=16, pady=(6, 14))
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.pack(side="bottom", fill="x", padx=12)
        for texto, comando in (("Salvar análise", ao_salvar_analise), ("Abrir análise", ao_abrir_analise)):
            ctk.CTkButton(
                botoes, text=texto, height=30, anchor="w", command=comando,
                **{**tema.BOTAO_SECUNDARIO, "fg_color": tema.HOVER_LATERAL, "font": tema.fonte(12)},
            ).pack(side="bottom", fill="x", pady=3)
        ctk.CTkLabel(self, text="ANÁLISE", font=tema.fonte(10, "bold"), text_color=COR_APAGADA, anchor="w").pack(
            side="bottom", fill="x", padx=16, pady=(0, 4)
        )

        # logo no topo (o mesmo ícone do executável)
        marca = ctk.CTkFrame(self, fg_color="transparent")
        marca.pack(fill="x", padx=14, pady=(18, 10))
        ctk.CTkLabel(marca, text="", image=tema.imagem_logo(38)).pack(side="left")
        textos = ctk.CTkFrame(marca, fg_color="transparent")
        textos.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(textos, text="CX Rays", font=tema.fonte(17, "bold"), anchor="w", height=22).pack(fill="x")
        ctk.CTkLabel(
            textos, text="Calculadora de\nconcentrações", font=tema.fonte(10), text_color=tema.TEXTO_2, anchor="w",
            justify="left", height=26,
        ).pack(fill="x")

        self._grupo("ALVOS", pady=(8, 6))
        for chave, (titulo, subtitulo, icone) in ALVOS.items():
            self._criar_aba(chave, titulo, subtitulo, icone)

        ctk.CTkFrame(self, height=1, fg_color=tema.BORDA_SUAVE).pack(fill="x", padx=14, pady=(14, 0))
        self._grupo("TODOS OS ALVOS", pady=(12, 6))
        for chave, (titulo, subtitulo, icone) in GERAIS.items():
            self._criar_aba(chave, titulo, subtitulo, icone)

        self.selecionar(inicial, notificar=False)

    def _grupo(self, texto, pady):
        ctk.CTkLabel(self, text=texto, font=tema.fonte(10, "bold"), text_color=COR_APAGADA, anchor="w").pack(
            fill="x", padx=16, pady=pady
        )

    def _criar_aba(self, chave, titulo, subtitulo, icone):
        aba = _Aba(self, chave, titulo, subtitulo, icone, self.selecionar)
        aba.pack(fill="x", padx=8, pady=2)
        self.abas[chave] = aba

    def definir_status(self, chave, texto):
        """Complementa o nome do alvo (ex.: "Prata · 12 amostras"), para ver de longe quais já foram calculados."""
        aba = self.abas.get(chave)
        if aba and aba.subtitulo is not None:
            nome = ALVOS[chave][1]
            aba.subtitulo.configure(text=f"{nome} · {texto}" if texto else nome)

    def selecionar(self, chave, notificar=True):
        if chave not in self.abas or chave == self.selecionada:
            return
        self.selecionada = chave
        for outra, aba in self.abas.items():
            aba.marcar(outra == chave)
        if notificar and self.ao_trocar:
            self.ao_trocar(chave)
