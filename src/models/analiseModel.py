"""
Arquivo de análise (.cxa): guarda o que o usuário escolheu em cada aba de alvo (arquivos, padrões, PDFs, nomes,
cálculos extras e ajustes dos gráficos), não os números. Ao abrir, o programa lê os .txt de novo e recalcula.
É um JSON; os caminhos são guardados absolutos e também relativos ao .cxa, para a análise continuar abrindo
quando a pasta inteira (com o .cxa dentro) for copiada para outro lugar ou outro computador.
"""

import json
import os

EXTENSAO = ".cxa"
VERSAO = 1


class AnaliseInvalidaError(Exception):
    """O arquivo não é uma análise salva por este programa (ou está corrompido)."""


def _relativo(caminho, pasta):
    try:
        return os.path.relpath(caminho, pasta)
    except ValueError:  # outro disco no Windows: não há caminho relativo
        return None


def resolver_caminho(guardado, pasta_analise):
    """Caminho que existe para um arquivo guardado ({"absoluto", "relativo"}), ou None."""
    if not guardado:
        return None
    absoluto = guardado.get("absoluto")
    if absoluto and os.path.exists(absoluto):
        return absoluto
    relativo = guardado.get("relativo")
    if relativo:
        candidato = os.path.normpath(os.path.join(pasta_analise, relativo))
        if os.path.exists(candidato):
            return candidato
    return None


def _guardar_caminho(caminho, pasta):
    if not caminho:
        return None
    caminho = os.path.abspath(caminho)
    return {"absoluto": caminho, "relativo": _relativo(caminho, pasta)}


def _chave_para_texto(chave):
    """Chave do slider: a amostra (concentração) ou (base, amostra). JSON só aceita texto como chave."""
    return f"{chave[0]}|{chave[1]}" if isinstance(chave, tuple) else chave


def _texto_para_chave(texto):
    base, separador, amostra = texto.partition("|")
    return (base, amostra) if separador else texto


def escolhas_graficos_para_json(graficos_traco, graficos_excluidos):
    return {
        "traco": {_chave_para_texto(chave): n for chave, n in graficos_traco.items()},
        "excluidos": {
            _chave_para_texto(chave): {grafico: sorted(elementos) for grafico, elementos in por_grafico.items()}
            for chave, por_grafico in graficos_excluidos.items()
        },
    }


def escolhas_graficos_de_json(dados):
    """Devolve (graficos_traco, graficos_excluidos), como o ResultadoPadrao guarda."""
    dados = dados or {}
    traco = {_texto_para_chave(chave): int(n) for chave, n in (dados.get("traco") or {}).items()}
    excluidos = {
        _texto_para_chave(chave): {grafico: set(elementos) for grafico, elementos in por_grafico.items()}
        for chave, por_grafico in (dados.get("excluidos") or {}).items()
    }
    return traco, excluidos


def salvar_analise(caminho, abas, aba_aberta=None):
    """
    abas: {alvo: estado da aba} (ver ConcentracaoVM.estado_analise); os caminhos de arquivo vão como texto
    e são convertidos aqui para {"absoluto", "relativo"}.
    """
    pasta = os.path.dirname(os.path.abspath(caminho))
    dados = {"programa": "CX Calculator", "versao": VERSAO, "aba_aberta": aba_aberta, "abas": {}}
    for alvo, estado in abas.items():
        estado = dict(estado)
        estado["linhas"] = [
            {**linha, "arquivo": _guardar_caminho(linha["arquivo"], pasta), "pdf": _guardar_caminho(linha.get("pdf"), pasta)}
            for linha in estado.get("linhas", [])
        ]
        dados["abas"][alvo] = estado
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def abrir_analise(caminho):
    """
    Lê a análise e resolve os caminhos. Devolve (dados, faltando): nos dados, "arquivo" e "pdf" de cada linha
    voltam a ser texto; linhas cujo .txt não foi encontrado saem da lista e entram em `faltando`.
    Lança AnaliseInvalidaError.
    """
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise AnaliseInvalidaError(f"Não foi possível ler {os.path.basename(caminho)}:\n{erro}") from erro
    if not isinstance(dados, dict) or dados.get("programa") != "CX Calculator" or not isinstance(dados.get("abas"), dict):
        raise AnaliseInvalidaError(f"{os.path.basename(caminho)} não é uma análise salva pela calculadora.")
    if int(dados.get("versao") or 0) > VERSAO:
        raise AnaliseInvalidaError(
            f"{os.path.basename(caminho)} foi salva por uma versão mais nova da calculadora. Atualize o programa."
        )

    pasta = os.path.dirname(os.path.abspath(caminho))
    faltando = []
    for alvo, estado in dados["abas"].items():
        linhas = []
        for linha in estado.get("linhas", []):
            arquivo = resolver_caminho(linha.get("arquivo"), pasta)
            if not arquivo:
                guardado = (linha.get("arquivo") or {}).get("absoluto") or "?"
                faltando.append(f"{alvo}: {guardado}")
                continue
            pdf = resolver_caminho(linha.get("pdf"), pasta)
            if linha.get("pdf") and not pdf:
                faltando.append(f"{alvo}: {(linha['pdf'] or {}).get('absoluto')} (FullReport)")
            linhas.append({**linha, "arquivo": arquivo, "pdf": pdf})
        estado["linhas"] = linhas
    return dados, faltando
