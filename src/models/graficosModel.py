import os
import re

from matplotlib.colors import to_rgb
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

from models.coresElementosModel import carregar_cores, cor_do_elemento
from models.elementosQuimicos import z_do_elemento
from models.fichaInformacaoModel import nome_da_amostra

FATOR_PARA_MG_KG = {"mg/kg": 1, "g/kg": 1000}
FORMATOS = ("png", "svg", "pdf")  # PNG (200 dpi) ou vetorial (SVG, PDF), para artigo


def salvar_figura(figura, caminho_sem_extensao, formato="png"):
    """Grava a figura no formato escolhido (fundo da própria figura). Devolve o caminho com a extensão."""
    formato = formato if formato in FORMATOS else "png"
    caminho = f"{caminho_sem_extensao}.{formato}"
    figura.savefig(caminho, dpi=200, facecolor=figura.get_facecolor(), format=formato)
    return caminho


ALVO_TRACO_AUTOMATICO = 0.05  # "Distribuir automaticamente": traço com cerca de 5% do total
LIMITE_ERRO_AREA = 30  # %: na tabela avançada, a linha fica vermelha com erro da área a partir daqui
GRAFICOS = ("majoritario", "traco")  # cada um tem a sua seleção de elementos na tabela avançada

FONTE = ["Segoe UI", "DejaVu Sans"]
MAX_FATIAS = 10  # nas pizzas, o excedente (os menores) vira "Outros"; nas barras aparecem todos

TIPOS = {"anel": "Anel", "pizza": "Pizza", "pizza3d": "Pizza 3D", "barras": "Barras"}
# o que os gráficos dividem: a concentração ou a área normalizada (para quem não tem concentração)
BASES = {"concentracao": "Concentração", "area": "Área normalizada"}
UNIDADE_DA_BASE = {"concentracao": "mg/kg", "area": "CPS"}

# Cada elemento tem cor fixa (models/coresElementosModel.py). "neutro" = (Traço, Outros): agrupamentos
# ficam em cinza, nunca numa cor de elemento.
TEMAS = {
    "claro": {
        "fundo": "#ffffff", "tinta": "#0b0b0b", "tinta2": "#52514e", "apagado": "#898781", "linha": "#e1e0d9",
        "neutro": ("#898781", "#c3c2b7"),
    },
    "escuro": {
        "fundo": "#1a1a19", "tinta": "#f0efec", "tinta2": "#c3c2b7", "apagado": "#898781", "linha": "#2c2c2a",
        "neutro": ("#898781", "#62615c"),
    },
}


def _escurecer(cor, fator=0.62):
    """Lateral da pizza 3D: a mesma cor, mais escura."""
    return tuple(c * fator for c in to_rgb(cor))


class GraficosModel:
    """Lógica dos gráficos (majoritário / traço). A janela fica em views/graficosView.py."""

    def __init__(self, excluidos=()):
        """excluidos: elementos que não entram nos gráficos (o alvo do tubo de raios X, ex.: {"Ag"})."""
        self.cores = carregar_cores()
        self.excluidos = set(excluidos)

    @staticmethod
    def valores_em_mg_kg(concs, unidades):
        """
        {(elemento, energia): concentração} -> {elemento: concentração em mg/kg}.
        Tudo na mesma unidade, senão a soma (e a fração de traço) mistura g/kg com mg/kg.
        Um elemento medido em mais de uma linha (ex.: Ag K e Ag L) entra uma vez, com a média.
        Valores <= 0 ficam de fora (não cabem numa pizza).
        """
        por_elemento = {}
        for chave, valor in concs.items():
            elemento = chave[0] if isinstance(chave, tuple) else chave
            fator = FATOR_PARA_MG_KG.get(str((unidades or {}).get(elemento, "mg/kg")).strip().lower(), 1)
            por_elemento.setdefault(elemento, []).append(float(valor) * fator)
        medias = {elemento: sum(v) / len(v) for elemento, v in por_elemento.items()}
        return {elemento: v for elemento, v in medias.items() if v > 0}

    @staticmethod
    def amostras(resultado_padrao):
        """Nomes das amostras de um ResultadoPadrao, na ordem da tabela (sem cálculo, as normalizadas)."""
        if not resultado_padrao.concentracoes:
            return list(resultado_padrao.areas_normalizadas)
        return [nome for bloco in resultado_padrao.concentracoes.values() for nome in bloco]

    @staticmethod
    def areas_por_elemento(areas):
        """
        {(elemento, energia): área normalizada} -> {elemento: área}, para quem não tem concentração.
        Fica a linha mais intensa de cada elemento (média de áreas de linhas diferentes não tem sentido físico).
        O Ar fica de fora: é a referência da normalização e vem do ar, não da amostra.
        """
        por_elemento = {}
        for chave, area in areas.items():
            elemento = chave[0] if isinstance(chave, tuple) else chave
            if elemento in (None, "Ar"):
                continue
            por_elemento[elemento] = max(por_elemento.get(elemento, float("-inf")), float(area))
        return {elemento: v for elemento, v in por_elemento.items() if v > 0}

    @staticmethod
    def erros_area_percentuais(resultado_padrao, amostra):
        """
        {elemento: erro da área em %}, da linha mais intensa de cada elemento (a mesma de areas_por_elemento).
        A normalização multiplica área e erro pelo mesmo fator, então a razão é a mesma do .txt.
        """
        areas = resultado_padrao.areas_normalizadas.get(amostra, {})
        erros = resultado_padrao.erros_normalizados.get(amostra, {})
        melhor = {}  # elemento -> (área, erro %)
        for chave, area in areas.items():
            elemento = chave[0] if isinstance(chave, tuple) else chave
            area = float(area)
            if elemento is None or chave not in erros or area <= 0:
                continue
            if area > melhor.get(elemento, (0, None))[0]:
                melhor[elemento] = (area, 100 * abs(float(erros[chave])) / area)
        return {elemento: erro for elemento, (_, erro) in melhor.items()}

    def excluidos_da_amostra(self, resultado_padrao, amostra, base="concentracao"):
        """
        {"majoritario": set, "traco": set} com os elementos desmarcados na tabela avançada de cada gráfico.
        É o próprio dicionário guardado no ResultadoPadrao: a janela altera e a exportação lê o mesmo.
        """
        excluidos = resultado_padrao.graficos_excluidos.setdefault(self.chave_traco(amostra, base), {})
        for grafico in GRAFICOS:
            excluidos.setdefault(grafico, set())
        return excluidos

    def linhas_tabela(self, valores, n_traco, erros=None):
        """
        Linhas da tabela avançada, do maior para o menor valor:
        [{"z", "elemento", "valor", "fracao" (do total), "grupo" ("majoritario"/"traco"), "erro" (% ou None)}].
        """
        majoritarios, traco = self.dividir(valores, n_traco)
        total = sum(valores.values())
        return [
            {"z": z_do_elemento(elemento), "elemento": elemento, "valor": valor,
             "fracao": valor / total if total else 0.0, "grupo": grupo, "erro": (erros or {}).get(elemento)}
            for grupo, itens in (("majoritario", majoritarios), ("traco", traco))
            for elemento, valor in itens
        ]

    def valores_da_amostra(self, resultado_padrao, amostra, base="concentracao"):
        """
        base: "concentracao" (mg/kg) ou "area" (área normalizada, CPS).
        Os elementos de self.excluidos (o alvo do tubo) ficam de fora: vêm do tubo, não da amostra.
        """
        if base == "area":
            valores = self.areas_por_elemento(resultado_padrao.areas_normalizadas.get(amostra, {}))
        else:
            valores = next(
                (self.valores_em_mg_kg(bloco[amostra], resultado_padrao.unidade_padrao)
                 for bloco in resultado_padrao.concentracoes.values() if amostra in bloco),
                {},
            )
        return {elemento: v for elemento, v in valores.items() if elemento not in self.excluidos}

    @staticmethod
    def chave_traco(amostra, base="concentracao"):
        """Onde fica a escolha do slider: cada base tem a sua (o número de elementos é diferente)."""
        return amostra if base == "concentracao" else (base, amostra)

    @staticmethod
    def max_traco(valores):
        """O majoritário fica sempre com pelo menos um elemento."""
        return max(len(valores) - 1, 0)

    def dividir(self, valores, n_traco):
        """
        Os n_traco elementos de menor concentração vão para o traço; o resto é majoritário.
        Devolve (majoritarios, traco), cada um como [(elemento, valor)] do maior para o menor.
        """
        n_traco = min(max(int(n_traco), 0), self.max_traco(valores))
        crescente = sorted(valores.items(), key=lambda item: item[1])
        traco = crescente[:n_traco]
        majoritarios = crescente[n_traco:]
        return majoritarios[::-1], traco[::-1]

    def n_traco_automatico(self, valores, alvo=ALVO_TRACO_AUTOMATICO):
        """Quantidade de elementos no traço que deixa a soma do traço mais perto de `alvo` (fração do total)."""
        total = sum(valores.values())
        if not total:
            return 0
        crescente = sorted(valores.values())
        melhor, menor_distancia, soma = 0, alvo, 0.0
        for n in range(1, self.max_traco(valores) + 1):
            soma += crescente[n - 1]
            distancia = abs(soma / total - alvo)
            if distancia < menor_distancia:
                melhor, menor_distancia = n, distancia
        return melhor

    def n_traco_da_amostra(self, resultado_padrao, amostra, valores, automatico, base="concentracao"):
        """
        Quantos elementos vão para o traço nessa amostra: o automático (~5%) se a caixinha estiver marcada;
        senão o que foi escolhido no slider (ou o automático, se o slider ainda não foi mexido).
        """
        chave = self.chave_traco(amostra, base)
        if automatico or chave not in resultado_padrao.graficos_traco:
            return self.n_traco_automatico(valores)
        return min(resultado_padrao.graficos_traco[chave], self.max_traco(valores))

    @staticmethod
    def fracao_traco(valores, traco):
        total = sum(valores.values())
        return sum(v for _, v in traco) / total if total else 0.0

    @staticmethod
    def formatar_percentual(fracao):
        """1 casa normalmente; 2 casas abaixo de 1%, para o traço não aparecer como "0.0%"."""
        return f"{fracao:.2%}" if 0 < fracao < 0.01 else f"{fracao:.1%}"

    @staticmethod
    def formatar_concentracao(valor):
        if valor >= 1000:
            return f"{valor:,.0f}".replace(",", " ")
        if valor >= 10:
            return f"{valor:.1f}"
        if valor >= 1:
            return f"{valor:.2f}"
        return f"{valor:.3g}"

    def montar_fatias(self, itens, neutra, tema, limite=MAX_FATIAS):
        """
        itens: [(elemento, valor)] do maior para o menor; neutra: ("Traço", valor) ou None.
        Devolve ([(rótulo, valor, cor)], elementos agrupados em "Outros"). Cada elemento usa a sua cor fixa;
        acima de `limite` fatias, os menores viram "Outros (n)", em cinza.
        """
        neutro_traco, neutro_outros = TEMAS[tema]["neutro"]
        limite = (limite or len(itens) + 2) - (1 if neutra else 0)
        outros = []
        if len(itens) > limite:
            itens, outros = itens[: limite - 1], itens[limite - 1:]

        fatias = [(elemento, valor, cor_do_elemento(elemento, self.cores)) for elemento, valor in itens]
        if outros:
            fatias.append((f"Outros ({len(outros)})", sum(v for _, v in outros), neutro_outros))
        if neutra:
            fatias.append((neutra[0], neutra[1], neutro_traco))
        return fatias, [e for e, _ in outros]

    def _cabecalho(self, figura, titulo, subtitulo, t):
        figura.set_facecolor(t["fundo"])
        figura.text(0.04, 0.95, titulo, ha="left", va="top", fontsize=13, fontweight="bold",
                    color=t["tinta"], fontfamily=FONTE)
        figura.text(0.04, 0.875, subtitulo, ha="left", va="top", fontsize=9, color=t["apagado"], fontfamily=FONTE)

    @staticmethod
    def _pizza_3d(ax, valores, cores, fundo):
        """Pizza inclinada: o disco achatado e, embaixo, a lateral feita de cópias mais escuras."""
        profundidade, camadas = 0.18, 16
        laterais = [_escurecer(c) for c in cores]
        for k in range(camadas, 0, -1):
            ax.pie(valores, colors=laterais, startangle=90, counterclock=False,
                   center=(0, -profundidade * k / camadas), wedgeprops={"edgecolor": "none"})
        ax.pie(valores, colors=cores, startangle=90, counterclock=False,
               wedgeprops={"edgecolor": fundo, "linewidth": 1.5})
        ax.set_xlim(-1.08, 1.08)
        ax.set_ylim(-1.08 - profundidade, 1.08)
        ax.set_aspect(0.55)  # inclinação

    def _barras(self, figura, fatias, legenda_nota, t, unidade="mg/kg"):
        """Barras horizontais, do maior para o menor, com % e o valor (mg/kg ou CPS) na ponta de cada barra."""
        ax = figura.add_axes([0.16, 0.06, 0.8, 0.72])
        ax.set_facecolor(t["fundo"])
        total = sum(v for _, v, _ in fatias)
        posicoes = list(range(len(fatias)))[::-1]  # o maior em cima
        percentuais = [100 * v / total for _, v, _ in fatias]
        ax.barh(posicoes, percentuais, height=0.62, color=[c for _, _, c in fatias])
        maior = max(percentuais)
        for y, p, (_, valor, _) in zip(posicoes, percentuais, fatias):
            ax.text(p + maior * 0.015, y, f"{self.formatar_percentual(p / 100)}   {self.formatar_concentracao(valor)} {unidade}",
                    va="center", ha="left", fontsize=9, color=t["tinta2"], fontfamily=FONTE)
        ax.set_yticks(posicoes, [r for r, _, _ in fatias], fontsize=10, color=t["tinta"], fontfamily=FONTE)
        ax.tick_params(axis="y", length=0, pad=8)
        ax.set_xlim(0, maior * 1.45)
        ax.set_ylim(-0.6, len(fatias) - 0.4)
        ax.xaxis.set_visible(False)
        for lado in ("top", "right", "bottom"):
            ax.spines[lado].set_visible(False)
        ax.spines["left"].set_color(t["linha"])
        if legenda_nota:
            figura.text(0.96, 0.02, legenda_nota, ha="right", va="bottom", fontsize=8, color=t["apagado"],
                        fontfamily=FONTE)

    def _desenhar(self, figura, fatias, titulo, subtitulo, centro, legenda_nota, tema, tipo="anel", unidade="mg/kg"):
        t = TEMAS[tema]
        self._cabecalho(figura, titulo, subtitulo, t)
        if tipo == "barras":
            self._barras(figura, fatias, legenda_nota, t, unidade)
            return

        grade = figura.add_gridspec(1, 2, width_ratios=[1, 1.05], left=0.03, right=0.97, top=0.8, bottom=0.04,
                                    wspace=0.08)
        ax = figura.add_subplot(grade[0])
        ax.set_facecolor(t["fundo"])
        valores, cores = [v for _, v, _ in fatias], [c for _, _, c in fatias]
        if tipo == "pizza3d":
            self._pizza_3d(ax, valores, cores, t["fundo"])
        else:
            anel = tipo == "anel"
            ax.pie(
                valores,
                colors=cores,
                startangle=90,
                counterclock=False,
                # vão de 2px entre fatias; no anel, só a borda
                wedgeprops={"width": 0.34 if anel else 1, "edgecolor": t["fundo"], "linewidth": 2},
            )
            if anel:
                grande, legenda_centro = centro
                ax.text(0, 0.08, grande, ha="center", va="center", fontsize=20, fontweight="bold",
                        color=t["tinta"], fontfamily=FONTE)
                ax.text(0, -0.2, legenda_centro, ha="center", va="center", fontsize=9, color=t["apagado"],
                        fontfamily=FONTE)
            ax.set_aspect("equal")

        # legenda em forma de tabela: elemento | % | valor (texto na cor da tinta, a cor fica só no quadrado)
        leg = figura.add_subplot(grade[1])
        leg.axis("off")
        leg.set_xlim(0, 1)
        leg.set_ylim(0, 1)
        total = sum(v for _, v, _ in fatias)
        passo = min(0.1, 0.86 / (len(fatias) + 1))
        y = 0.5 + passo * (len(fatias) + 1) / 2 - passo / 2
        for x, texto, alinhamento in ((0.1, "Elemento", "left"), (0.66, "%", "right"), (1.0, unidade, "right")):
            leg.text(x, y, texto, ha=alinhamento, va="center", fontsize=8, color=t["apagado"], fontfamily=FONTE)
        leg.plot([0, 1], [y - passo / 2] * 2, color=t["linha"], linewidth=0.8)
        for rotulo, valor, cor in fatias:
            y -= passo
            leg.add_patch(FancyBboxPatch((0.0, y - 0.022), 0.05, 0.044, boxstyle="round,pad=0,rounding_size=0.008",
                                         facecolor=cor, edgecolor="none", transform=leg.transData))
            leg.text(0.1, y, rotulo, ha="left", va="center", fontsize=10, color=t["tinta"], fontfamily=FONTE)
            leg.text(0.66, y, self.formatar_percentual(valor / total), ha="right", va="center", fontsize=10,
                     color=t["tinta"], fontfamily=FONTE)
            leg.text(1.0, y, self.formatar_concentracao(valor), ha="right", va="center", fontsize=9,
                     color=t["tinta2"], fontfamily=FONTE)
        if legenda_nota:
            leg.text(0.1, y - passo * 0.85, legenda_nota, ha="left", va="center", fontsize=8,
                     color=t["apagado"], fontfamily=FONTE, wrap=True)

    def _vazio(self, figura, titulo, texto, tema):
        t = TEMAS[tema]
        self._cabecalho(figura, titulo, "", t)
        figura.text(0.5, 0.45, texto, ha="center", va="center", fontsize=10, color=t["apagado"], fontfamily=FONTE)

    def separar(self, valores, n_traco, excluidos=None):
        """
        Como dividir(), mas tirando os elementos desmarcados na tabela avançada de cada gráfico.
        Devolve (majoritários, traço que entra na fatia "Traço" do majoritário, traço do gráfico de traço),
        cada um como [(elemento, valor)] do maior para o menor.
        """
        excluidos = excluidos or {}
        fora_maj, fora_traco = set(excluidos.get("majoritario", ())), set(excluidos.get("traco", ()))
        majoritarios, traco = self.dividir(valores, n_traco)
        return (
            [(e, v) for e, v in majoritarios if e not in fora_maj],
            [(e, v) for e, v in traco if e not in fora_maj],
            [(e, v) for e, v in traco if e not in fora_traco],
        )

    def criar_figuras(self, amostra, valores, n_traco, tema="claro", padrao=None, tipo="anel", base="concentracao",
                      nomes=None, excluidos=None):
        """
        Figuras do majoritário e do traço (as mesmas da tela e da exportação).
        tema: "escuro" na janela do programa, "claro" (fundo branco) nas imagens exportadas.
        tipo: uma das chaves de TIPOS; base: uma das chaves de BASES.
        nomes: {código: nome} da ficha de informação; no título, o nome entra no lugar do código.
        excluidos: {"majoritario": set, "traco": set} desmarcados na tabela avançada (ficam fora daquele gráfico).
        """
        amostra = nome_da_amostra(nomes, amostra) or amostra
        padrao = (nome_da_amostra(nomes, padrao) or padrao) if padrao else padrao
        tipo = tipo if tipo in TIPOS else "anel"
        unidade = UNIDADE_DA_BASE.get(base, "mg/kg")
        medida = "das áreas normalizadas (CPS)" if base == "area" else "das concentrações (mg/kg)"
        limite = None if tipo == "barras" else MAX_FATIAS  # barras têm espaço para todos os elementos
        excluidos = excluidos or {}
        _, traco_total = self.dividir(valores, n_traco)
        majoritarios, traco_no_maj, traco = self.separar(valores, n_traco, excluidos)
        soma_traco = sum(v for _, v in traco_no_maj)
        total_maj = sum(v for _, v in majoritarios) + soma_traco
        fracao_maj = soma_traco / total_maj if total_maj else 0.0
        fracao = self.fracao_traco(valores, traco_total)
        complemento = f" · padrão {padrao}" if padrao else ""
        if self.excluidos:
            complemento += f" · sem {', '.join(sorted(self.excluidos))} (alvo do tubo)"

        def notas(outros, grafico):
            fora = sorted(set(excluidos.get(grafico, ())) & set(valores))
            return " · ".join(texto for texto in (
                f"Outros: {', '.join(outros)}" if outros else "",
                f"Fora do gráfico: {', '.join(fora)}" if fora else "",
            ) if texto)

        fig_maj = Figure(figsize=(6.4, 3.6))
        titulo_maj = f"{amostra} · Majoritário"
        if majoritarios or traco_no_maj:
            fatias, outros = self.montar_fatias(
                majoritarios, ("Traço", soma_traco) if traco_no_maj else None, tema, limite
            )
            centro = ((self.formatar_percentual(fracao_maj), "no traço") if traco_no_maj
                      else (str(len(majoritarios)), "elementos"))
            self._desenhar(fig_maj, fatias, titulo_maj, f"% da soma {medida}{complemento}", centro,
                           notas(outros, "majoritario"), tema, tipo, unidade)
        else:
            self._vazio(fig_maj, titulo_maj, "Nenhum elemento marcado para este gráfico.", tema)

        fig_traco = Figure(figsize=(6.4, 3.6))
        if traco:
            fatias, outros = self.montar_fatias(traco, None, tema, limite)
            self._desenhar(fig_traco, fatias, f"{amostra} · Traço",
                           f"% dentro do traço, que é {self.formatar_percentual(fracao)} do total{complemento}",
                           (str(len(traco)), "elemento" if len(traco) == 1 else "elementos"),
                           notas(outros, "traco"), tema, tipo, unidade)
        elif traco_total:
            self._vazio(fig_traco, f"{amostra} · Traço", "Nenhum elemento marcado para este gráfico.", tema)
        else:
            self._vazio(fig_traco, f"{amostra} · Traço", "Nenhum elemento no traço.\nUse o slider para mover elementos.",
                        tema)
        return fig_maj, fig_traco

    @staticmethod
    def _nome_arquivo(texto):
        return re.sub(r'[\\/:*?"<>|]+', "_", str(texto)).strip() or "grafico"

    def exportar(self, pasta, itens, tipo="anel", base="concentracao", nomes=None, formato="png"):
        """
        itens: [(subpasta ou None, amostra, valores, n_traco, padrão ou None, excluidos ou None)];
        excluidos como em criar_figuras (os dois últimos são opcionais).
        Grava "<amostra> - majoritario.png" e, se houver traço, "<amostra> - traco.png" (tema claro, fundo branco);
        formato: "png", "svg" ou "pdf" (a extensão acompanha).
        Com nome na ficha, o arquivo vira "<nome> (<código>)", para duas amostras de mesmo nome não se sobrescreverem.
        Com a área normalizada, os nomes ganham " - area" (para não sobrescrever os de concentração).
        Devolve os caminhos.
        """
        sufixo = " - area" if base == "area" else ""
        gravados = []
        for subpasta, amostra, valores, n_traco, *resto in itens:
            padrao = resto[0] if resto else None
            excluidos = resto[1] if len(resto) > 1 else None
            if not valores:
                continue
            destino = os.path.join(pasta, self._nome_arquivo(subpasta)) if subpasta else pasta
            os.makedirs(destino, exist_ok=True)
            fig_maj, fig_traco = self.criar_figuras(
                amostra, valores, n_traco, "claro", padrao, tipo, base, nomes, excluidos
            )
            nome = nome_da_amostra(nomes, amostra)
            arquivo = f"{nome} ({amostra})" if nome else amostra
            prefixo = os.path.join(destino, self._nome_arquivo(arquivo) + sufixo)
            arquivos = [(fig_maj, f"{prefixo} - majoritario")]
            if self.separar(valores, n_traco, excluidos)[2]:
                arquivos.append((fig_traco, f"{prefixo} - traco"))
            for figura, caminho in arquivos:
                gravados.append(salvar_figura(figura, caminho, formato))
        return gravados
