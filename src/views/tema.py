"""
Aparência do programa em um lugar só: cores (tiradas do ícone CX Rays), fonte e estilos de botão.
aplicar() troca os padrões do customtkinter; o que as telas pintam à mão vem das constantes daqui.
"""

import customtkinter as ctk
from PIL import Image

from resource_utils import resource_path

FONTE = "Segoe UI"

# --- cores do ícone ---
DESTAQUE = "#5BA8EB"  # azul do ícone: ação principal, seleção, foco
DESTAQUE_HOVER = "#7BB8F0"
SOBRE_DESTAQUE = "#0D1330"  # texto em cima do azul (contraste alto)
MARINHO = "#22264E"  # fundo do ícone: cabeçalhos de tabela

# --- superfícies (do mais escuro ao mais claro) ---
LATERAL = "#0F111C"  # abas laterais
FUNDO = "#121420"  # janela
MENU = "#161829"  # menu do alvo
SUPERFICIE = "#1A1D30"  # cartões, listas, tabelas
SUPERFICIE_2 = "#1E2136"  # linha zebrada
CONTROLE = "#22263D"  # botões secundários, campos
CONTROLE_HOVER = "#2A2F4D"
SELECIONADA = "#1F2440"  # aba / item selecionado
HOVER_LATERAL = "#1B1E33"
BORDA = "#2E3352"
BORDA_SUAVE = "#262A44"

# --- texto ---
TEXTO = "#EEF0F7"
TEXTO_2 = "#A9AEC8"
APAGADO = "#8A90B0"
DESABILITADO = "#6D7394"

# --- sinais (só para estado e destaques da tabela) ---
OK = "#6FCF97"
OK_FUNDO = "#17261F"
OK_TEXTO = "#9FD8A6"
OK_HOVER = "#1E3328"
ATENCAO = "#F2A65A"
ATENCAO_FUNDO = "#4A3216"
ERRO_TEXTO = "#F08A8A"
ERRO_FUNDO = "#4A1F24"
ERRO_HOVER = "#5C262C"
LD_FUNDO = "#1A2338"
LD_TEXTO = "#9ECBFF"
AMBOS_TEXTO = "#FFE135"  # ≤ 3×LD e incerteza alta


def fonte(tamanho=13, peso="normal"):
    return (FONTE, tamanho, peso)


BOTAO_PRINCIPAL = {
    "fg_color": DESTAQUE, "hover_color": DESTAQUE_HOVER, "text_color": SOBRE_DESTAQUE,
    "text_color_disabled": "#3B4466", "border_width": 0, "corner_radius": 9, "font": fonte(14, "bold"),
}
BOTAO_SECUNDARIO = {
    "fg_color": CONTROLE, "hover_color": CONTROLE_HOVER, "text_color": TEXTO, "text_color_disabled": DESABILITADO,
    "border_width": 1, "border_color": BORDA, "corner_radius": 8, "font": fonte(13),
}
BOTAO_DISCRETO = {
    "fg_color": "transparent", "hover_color": CONTROLE, "text_color": DESTAQUE, "border_width": 1,
    "border_color": BORDA, "corner_radius": 6, "font": fonte(11, "bold"),
}
BOTAO_PERIGO = {
    "fg_color": ERRO_FUNDO, "hover_color": ERRO_HOVER, "text_color": ERRO_TEXTO, "border_width": 0,
    "corner_radius": 8, "font": fonte(13),
}


def rotulo_secao(master, texto, **pack):
    """Título pequeno de seção (ENTRADA, CÁLCULO, SAÍDAS...), em maiúsculas e cinza."""
    rotulo = ctk.CTkLabel(master, text=texto.upper(), font=fonte(10, "bold"), text_color=APAGADO, anchor="w")
    if pack:
        rotulo.pack(**pack)
    return rotulo


CAMINHO_ICONE = ("imagens", "icones", "cx_rays.ico")


def imagem_logo(tamanho):
    """O ícone do programa como CTkImage (o mesmo .ico do executável: trocando o arquivo, troca aqui)."""
    imagem = Image.open(resource_path(*CAMINHO_ICONE))
    imagem.size = max(imagem.info.get("sizes", {imagem.size}))  # a maior resolução guardada no .ico
    imagem = imagem.convert("RGBA")
    return ctk.CTkImage(light_image=imagem, dark_image=imagem, size=(tamanho, tamanho))


def aplicar_icone(janela):
    """Ícone na barra de título e na barra de tarefas (o customtkinter troca o ícone ~200 ms depois de criar)."""
    try:
        caminho = resource_path(*CAMINHO_ICONE)
        janela.iconbitmap(caminho)
        janela.after(250, lambda: janela.winfo_exists() and janela.iconbitmap(caminho))
    except Exception:
        pass  # sem o ícone (ou fora do Windows) a janela só fica com o ícone padrão


def _par(cor):
    return [cor, cor]  # [tema claro, tema escuro]: o programa só usa o escuro


def aplicar():
    """Troca os padrões do customtkinter pela paleta acima. Chamar antes de criar a janela principal."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")  # a base; o resto é trocado abaixo
    t = ctk.ThemeManager.theme
    fonte_padrao = t["CTkFont"].get("Windows", t["CTkFont"])  # já resolvido para o sistema ao carregar o tema
    fonte_padrao.update(family=FONTE, size=13)
    t["CTk"]["fg_color"] = _par(FUNDO)
    t["CTkToplevel"]["fg_color"] = _par(FUNDO)
    t["CTkFrame"].update(fg_color=_par(SUPERFICIE), top_fg_color=_par(SUPERFICIE_2), border_color=_par(BORDA))
    t["CTkButton"].update(
        fg_color=_par(CONTROLE), hover_color=_par(CONTROLE_HOVER), border_color=_par(BORDA),
        text_color=_par(TEXTO), text_color_disabled=_par(DESABILITADO), corner_radius=8,
    )
    t["CTkLabel"]["text_color"] = _par(TEXTO)
    t["CTkEntry"].update(
        fg_color=_par(CONTROLE), border_color=_par(BORDA), text_color=_par(TEXTO),
        placeholder_text_color=_par(APAGADO), corner_radius=6,
    )
    t["CTkCheckBox"].update(
        fg_color=_par(DESTAQUE), hover_color=_par(DESTAQUE_HOVER), border_color=_par("#5A6080"),
        checkmark_color=_par(SOBRE_DESTAQUE), text_color=_par(TEXTO), text_color_disabled=_par(DESABILITADO),
        corner_radius=4,
    )
    for nome in ("CTkComboBox", "CTkOptionMenu"):
        t[nome].update(fg_color=_par(CONTROLE), button_color=_par(BORDA), button_hover_color=_par(CONTROLE_HOVER),
                       text_color=_par(TEXTO))
        if "border_color" in t[nome]:
            t[nome]["border_color"] = _par(BORDA)
    t["DropdownMenu"].update(fg_color=_par(SUPERFICIE), hover_color=_par(CONTROLE_HOVER), text_color=_par(TEXTO))
    t["CTkSegmentedButton"].update(
        fg_color=_par(FUNDO), selected_color=_par(CONTROLE_HOVER), selected_hover_color=_par("#343a5e"),
        unselected_color=_par(FUNDO), unselected_hover_color=_par(CONTROLE), text_color=_par(TEXTO),
        text_color_disabled=_par(DESABILITADO),
    )
    t["CTkScrollbar"].update(button_color=_par(BORDA), button_hover_color=_par(CONTROLE_HOVER))
    t["CTkScrollableFrame"]["label_fg_color"] = _par(SUPERFICIE_2)
    t["CTkTextbox"].update(
        fg_color=_par(SUPERFICIE), border_color=_par(BORDA), text_color=_par(TEXTO),
        scrollbar_button_color=_par(BORDA), scrollbar_button_hover_color=_par(CONTROLE_HOVER),
    )
    t["CTkSlider"].update(
        fg_color=_par(BORDA), progress_color=_par(DESTAQUE), button_color=_par(DESTAQUE),
        button_hover_color=_par(DESTAQUE_HOVER),
    )
    t["CTkSwitch"].update(progress_color=_par(DESTAQUE), button_color=_par(TEXTO), fg_color=_par(BORDA))
    t["CTkRadioButton"].update(fg_color=_par(DESTAQUE), hover_color=_par(DESTAQUE_HOVER), border_color=_par("#5A6080"))
