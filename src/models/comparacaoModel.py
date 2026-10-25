import os
import re
from dataclasses import dataclass, field

from matplotlib.figure import Figure

from models.elementosQuimicos import z_do_elemento
from models.fichaInformacaoModel import codigo_amostra, nome_da_amostra
from models.graficosModel import FATOR_PARA_MG_KG, FONTE, TEMAS
from models.leitorArquivoModel import nome_amostra

# Gráficos comparativos, por elemento: as amostras no eixo X e, em cada amostra, uma barra (ou um ponto)
# por padrão (1ª situação, dentro de um alvo) ou por alvo (2ª situação). Barra de erro = erro propagado (1σ).
ESTILOS = {"barras": "Barras", "linhas": "Linhas"}
CORES_PADROES = ("#2a78d6", "#eb6834", "#8f6fe0", "#1baf7a", "#d4a017")  # na ordem dos padrões
CORES_ALVOS = {"Ag": "#8b95a1", "Au": "#d4a017", "Rh": "#1baf7a"}  # cor fixa de cada alvo em todos os gráficos
COR_SEM_ALVO = "#9a988f"
CODIGO_DATA = re.compile(r"\d{6}[a-z]{1,3}")  # código da medida (data + letras), sem nome
LIMITE_G_KG = 10000  # mg/kg: a partir daqui o eixo do elemento passa para g/kg
MAX_AMOSTRAS_LADO_A_LADO = 20  # somando os painéis; com mais, os painéis (um por padrão) ficam um embaixo do outro


@dataclass
class Serie:
    """Um padrão (ou um alvo): {chave da amostra: {elemento: (concentração, erro), em mg/kg}}."""

    rotulo: str
    cor: str
    valores: dict = field(default_factory=dict)


@dataclass
class Painel:
    titulo: str  # "" quando há um painel só
    series: list = field(default_factory=list)


@dataclass
class Comparacao:
    titulo: str  # "alvo Ag" / "entre alvos"
    tipo: str  # "padroes" ou "alvos" (vai no nome das imagens exportadas)
    amostras: list = field(default_factory=list)  # [(chave, rótulo no eixo X)], na ordem da tabela
    paineis: list = field(default_factory=list)
    avisos: list = field(default_factory=list)


class ComparacaoModel:
    """Monta e desenha os gráficos comparativos. As janelas ficam em views/comparacaoView.py."""

    @staticmethod
    def valores_com_erro(resultado_padrao, amostra, excluidos=()):
        """
        {elemento: (concentração, erro)} em mg/kg de uma amostra.
        Um elemento medido em mais de uma linha (ex.: Kα e Kβ) entra com a linha mais intensa (maior área),
        com o erro propagado dessa mesma linha. O Ar e os `excluidos` (alvo do tubo) ficam de fora.
        """
        concs = next((bloco[amostra] for bloco in resultado_padrao.concentracoes.values() if amostra in bloco), {})
        erros = next((bloco[amostra] for bloco in resultado_padrao.erros_concentracao.values() if amostra in bloco), {})
        areas = resultado_padrao.areas_normalizadas.get(amostra, {})
        unidades = resultado_padrao.unidade_padrao or {}

        melhor = {}  # elemento -> (área, concentração, erro)
        for chave, valor in concs.items():
            elemento = chave[0] if isinstance(chave, tuple) else chave
            if elemento in (None, "Ar") or elemento in excluidos:
                continue
            fator = FATOR_PARA_MG_KG.get(str(unidades.get(elemento, "mg/kg")).strip().lower(), 1)
            area = float(areas.get(chave, 0) or 0)
            if elemento not in melhor or area > melhor[elemento][0]:
                melhor[elemento] = (area, float(valor) * fator, abs(float(erros.get(chave, 0) or 0)) * fator)
        return {elemento: (valor, erro) for elemento, (_, valor, erro) in melhor.items() if valor > 0}

    @staticmethod
    def _amostras(resultado_padrao, padroes=()):
        """Amostras na ordem da tabela, sem as medidas dos padrões (`padroes`: códigos dos arquivos padrão)."""
        return [nome for bloco in resultado_padrao.concentracoes.values() for nome in bloco
                if codigo_amostra(nome) not in padroes]

    @staticmethod
    def _padroes(resultados):
        """Códigos dos arquivos padrão: ficam fora dos gráficos comparativos (só poluiriam o eixo X)."""
        return {codigo_amostra(nome_amostra(r.arquivo_padrao)) for r in resultados}

    def entre_padroes(self, resultados_por_padrao, alvo=None, nomes=None):
        """1ª situação: os padrões de UM alvo, cada um uma série. As amostras são as mesmas (mesmo código)."""
        excluidos = {alvo} if alvo else set()
        comparacao = Comparacao(f"alvo {alvo}" if alvo else "entre padrões", "padroes")
        painel = Painel("")
        vistas = {}
        padroes = self._padroes(resultados_por_padrao)
        for i, r in enumerate(resultados_por_padrao):
            serie = Serie(r.rotulo, CORES_PADROES[i % len(CORES_PADROES)])
            for amostra in self._amostras(r, padroes):
                if amostra not in vistas:
                    vistas[amostra] = nome_da_amostra(nomes, amostra) or amostra
                serie.valores[amostra] = self.valores_com_erro(r, amostra, excluidos)
            painel.series.append(serie)
        comparacao.amostras = list(vistas.items())
        comparacao.paineis = [painel]
        return comparacao

    @staticmethod
    def _sufixo(amostra):
        """Letras depois da data no código ("251026ab" -> "ab"); "" se o nome não tiver esse formato."""
        m = re.fullmatch(r"\d{6}([a-z]{1,3})", codigo_amostra(amostra))
        return m.group(1) if m else ""

    def _ligar_amostras(self, amostras_por_alvo, nomes_por_alvo):
        """
        Como reconhecer a mesma amostra em alvos diferentes (os arquivos de cada alvo são medidas diferentes).
        Tenta, nesta ordem: o nome da ficha de informação, as letras depois da data no código ("ab" de 251026ab)
        e, por último, a posição na lista. Uma forma vale se servir para todas as amostras (todas com nome, por
        exemplo), não repetir chave dentro de um alvo e ligar pelo menos metade das amostras que poderiam ser ligadas.
        Devolve ({alvo: {amostra: chave}}, {chave: rótulo}, texto de como foram ligadas).
        """
        def por_nome(alvo, i, amostra):
            nome = nome_da_amostra(nomes_por_alvo.get(alvo), amostra).strip().lower()
            return ("nome", nome) if nome else ("sem nome", alvo, amostra)

        def por_sufixo(alvo, i, amostra):
            sufixo = self._sufixo(amostra)
            return ("sufixo", sufixo) if sufixo else ("sem sufixo", alvo, amostra)

        formas = (
            (por_nome, "pelo nome da ficha de informação"),
            (por_sufixo, "pelas letras depois da data no código (ex.: ab de 251026ab)"),
            (lambda alvo, i, amostra: ("ordem", i), "pela ordem da lista (confira se as amostras correspondem)"),
        )
        total = sum(len(a) for a in amostras_por_alvo.values())
        maior = max((len(a) for a in amostras_por_alvo.values()), default=0)
        for chave_de, texto in formas:
            chaves = {alvo: {a: chave_de(alvo, i, a) for i, a in enumerate(lista)}
                      for alvo, lista in amostras_por_alvo.items()}
            if any(k[0].startswith("sem ") for c in chaves.values() for k in c.values()):
                continue  # alguma amostra sem nome (ou sem as letras no código)
            if any(len(set(c.values())) < len(c) for c in chaves.values()):
                continue  # duas amostras do mesmo alvo com a mesma chave
            unicas = len({k for c in chaves.values() for k in c.values()})
            possiveis = total - maior
            if possiveis <= 0 or (total - unicas) / possiveis >= 0.5:
                break

        rotulos = {}
        for alvo, lista in amostras_por_alvo.items():
            for amostra in lista:
                rotulos.setdefault(chaves[alvo][amostra], [])
                rotulos[chaves[alvo][amostra]].append(nome_da_amostra(nomes_por_alvo.get(alvo), amostra) or amostra)
        # rótulo no eixo X: o nome da ficha, se algum alvo tiver; senão o código do primeiro alvo
        rotulos = {k: next((r for r in lista if not CODIGO_DATA.fullmatch(r.lower())), lista[0])
                   for k, lista in rotulos.items()}
        return chaves, rotulos, texto

    def entre_alvos(self, resultados_por_alvo, nomes_por_alvo=None):
        """
        2ª situação: cada alvo é uma série, no mesmo gráfico. A amostra é reconhecida entre os alvos como
        _ligar_amostras() explica. Os padrões são pareados pelo nome do padrão certificado: um painel por padrão.
        """
        nomes_por_alvo = nomes_por_alvo or {}
        comparacao = Comparacao("entre alvos", "alvos")
        amostras_por_alvo = {}
        for alvo, resultados in resultados_por_alvo.items():
            lista = amostras_por_alvo.setdefault(alvo, [])
            for r in resultados:
                lista += [a for a in self._amostras(r, self._padroes(resultados)) if a not in lista]
        chaves, rotulos, como = self._ligar_amostras(amostras_por_alvo, nomes_por_alvo)

        paineis = {}  # padrão certificado -> Painel
        vistas = {}  # chave -> rótulo, na ordem em que aparecem
        for alvo, resultados in resultados_por_alvo.items():
            for r in resultados:
                certificado = r.nome_certificado or r.nome
                painel = paineis.setdefault(certificado, Painel(f"Padrão {certificado}"))
                if any(s.rotulo == alvo for s in painel.series):
                    continue  # o mesmo padrão certificado duas vezes no alvo: fica o primeiro
                serie = Serie(alvo, CORES_ALVOS.get(alvo, COR_SEM_ALVO))
                for amostra in self._amostras(r, self._padroes(resultados)):
                    chave = chaves[alvo][amostra]
                    vistas.setdefault(chave, rotulos[chave])
                    serie.valores[chave] = self.valores_com_erro(r, amostra, {alvo})
                painel.series.append(serie)
        comparacao.amostras = list(vistas.items())
        comparacao.paineis = list(paineis.values())
        comparacao.avisos.append(f"Amostras ligadas entre os alvos {como}.")
        return comparacao

    @staticmethod
    def elementos(comparacao):
        """Elementos com concentração em alguma série, em ordem de Z."""
        todos = {
            elemento
            for painel in comparacao.paineis
            for serie in painel.series
            for valores in serie.valores.values()
            for elemento in valores
        }
        return sorted(todos, key=lambda e: (z_do_elemento(e), e))

    @staticmethod
    def _unidade(comparacao, elemento):
        """("mg/kg", 1) ou, para valores grandes, ("g/kg", 1000)."""
        maior = max(
            (v[elemento][0] for p in comparacao.paineis for s in p.series for v in s.valores.values() if elemento in v),
            default=0,
        )
        return ("g/kg", 1000) if maior >= LIMITE_G_KG else ("mg/kg", 1)

    @staticmethod
    def _amostras_do_elemento(comparacao, painel, elemento):
        return [
            (chave, rotulo) for chave, rotulo in comparacao.amostras
            if any(elemento in s.valores.get(chave, {}) for s in painel.series)
        ]

    def _desenhar_painel(self, ax, painel, amostras, elemento, divisor, estilo, t):
        n = len(painel.series)
        largura = 0.8 / max(n, 1)
        erro_kw = {"elinewidth": 1, "capsize": 3, "capthick": 1}
        for i, serie in enumerate(painel.series):
            xs, ys, es = [], [], []
            for x, (chave, _) in enumerate(amostras):
                valor = serie.valores.get(chave, {}).get(elemento)
                if valor:
                    # barras lado a lado; nas linhas, todos os pontos na vertical da amostra
                    xs.append(x + (i - (n - 1) / 2) * largura if estilo == "barras" else x)
                    ys.append(valor[0] / divisor)
                    es.append(valor[1] / divisor)
            if not xs:
                continue
            if estilo == "barras":
                ax.bar(xs, ys, largura * 0.9, yerr=es, color=serie.cor, label=serie.rotulo, edgecolor=t["fundo"],
                       linewidth=0.6, error_kw={**erro_kw, "ecolor": t["tinta"]})
            else:
                ax.errorbar(xs, ys, yerr=es, color=serie.cor, label=serie.rotulo, linewidth=2, marker="o",
                            markersize=6, markeredgecolor=t["fundo"], markeredgewidth=1.2, **erro_kw)

        ax.set_facecolor(t["fundo"])
        ax.set_xlim(-0.6, len(amostras) - 0.4)
        rotulos = [rotulo for _, rotulo in amostras]
        inclinar = len(amostras) > 6 or max((len(r) for r in rotulos), default=0) > 12
        ax.set_xticks(range(len(amostras)), rotulos, rotation=30 if inclinar else 0, ha="right" if inclinar else "center",
                      fontsize=9, color=t["tinta2"], fontfamily=FONTE)
        ax.tick_params(colors=t["tinta2"], length=0, labelsize=9)
        ax.yaxis.grid(True, color=t["linha"], linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.spines["left"].set_color(t["linha"])
        ax.spines["bottom"].set_color(t["apagado"])
        if painel.titulo:
            ax.set_title(painel.titulo, loc="left", fontsize=11, fontweight="bold", color=t["tinta"], fontfamily=FONTE)

    def tamanho(self, comparacao, elemento):
        """(largura, altura) em polegadas para a imagem exportada: cresce com o número de amostras e séries."""
        paineis = [p for p in comparacao.paineis if self._amostras_do_elemento(comparacao, p, elemento)] or [None]
        n_amostras = max((len(self._amostras_do_elemento(comparacao, p, elemento)) for p in paineis if p), default=1)
        n_series = max((len(p.series) for p in paineis if p), default=1)
        largura = min(max(7.0, 1.5 + n_amostras * (0.5 + 0.22 * n_series)), 18.0)
        if len(paineis) > 1 and n_amostras * len(paineis) <= MAX_AMOSTRAS_LADO_A_LADO:
            return min(largura * len(paineis), 20.0), 5.0
        return largura, 1.4 + 3.8 * len(paineis)

    def criar_figura(self, comparacao, elemento, estilo="barras", tema="claro", figsize=None):
        """Um elemento: um painel por padrão (só na 2ª situação com mais de um padrão), na mesma escala."""
        t = TEMAS[tema]
        figura = Figure(figsize=figsize or self.tamanho(comparacao, elemento))
        figura.set_facecolor(t["fundo"])
        unidade, divisor = self._unidade(comparacao, elemento)
        paineis = [(p, self._amostras_do_elemento(comparacao, p, elemento)) for p in comparacao.paineis]
        paineis = [(p, a) for p, a in paineis if a]

        figura.text(0.015, 0.985, f"{elemento} · {comparacao.titulo}", ha="left", va="top", fontsize=14,
                    fontweight="bold", color=t["tinta"], fontfamily=FONTE)
        figura.text(0.015, 0.985 - 0.36 / figura.get_figheight(), f"Concentração em {unidade} · barras de erro = "
                    "erro propagado (1σ)", ha="left", va="top", fontsize=9, color=t["apagado"], fontfamily=FONTE)
        if not paineis:
            figura.text(0.5, 0.45, "Nenhuma amostra com este elemento.", ha="center", va="center", fontsize=10,
                        color=t["apagado"], fontfamily=FONTE)
            return figura

        lado_a_lado = len(paineis) > 1 and max(len(a) for _, a in paineis) * len(paineis) <= MAX_AMOSTRAS_LADO_A_LADO
        linhas, colunas = (1, len(paineis)) if lado_a_lado else (len(paineis), 1)
        altura = figura.get_figheight()
        inclinado = any(len(a) > 6 or max(len(r) for _, r in a) > 12 for _, a in paineis)
        topo = 1 - (1.25 if any(p.titulo for p, _ in paineis) else 0.95) / altura
        base = (1.0 if inclinado else 0.45) / altura
        grade = figura.add_gridspec(linhas, colunas, left=0.07, right=0.985, top=topo, bottom=base, wspace=0.08,
                                    hspace=0.55 if inclinado else 0.35)
        eixos = []
        for k, (painel, amostras) in enumerate(paineis):
            ax = figura.add_subplot(grade[k // colunas, k % colunas], sharey=eixos[0] if eixos else None)
            self._desenhar_painel(ax, painel, amostras, elemento, divisor, estilo, t)
            eixos.append(ax)
        # mesma escala em todos os painéis, do zero até o maior valor + erro
        maior = max(
            ((v[elemento][0] + v[elemento][1]) / divisor for p, _ in paineis for s in p.series
             for v in s.valores.values() if elemento in v),
            default=1,
        )
        for k, ax in enumerate(eixos):
            ax.set_ylim(0, maior * 1.08 or 1)
            if k % colunas == 0:
                ax.set_ylabel(f"{elemento}, {unidade}", color=t["tinta2"], fontsize=10, fontfamily=FONTE)
            else:
                ax.tick_params(labelleft=False)

        # uma legenda só, com cada série uma vez (os alvos se repetem entre os painéis)
        legenda = {}
        for ax in eixos:
            for handle, rotulo in zip(*ax.get_legend_handles_labels()):
                legenda.setdefault(rotulo, handle)
        figura.legend(list(legenda.values()), list(legenda), loc="upper right", bbox_to_anchor=(0.985, 0.995),
                      ncol=min(len(legenda), 4), frameon=False, fontsize=9, labelcolor=t["tinta"])
        return figura

    @staticmethod
    def _nome_arquivo(texto):
        return re.sub(r'[\\/:*?"<>|]+', "_", str(texto)).strip() or "grafico"

    def exportar(self, pasta, comparacao, estilo="barras"):
        """Uma imagem por elemento (tema claro): "<Z> <elemento> - <padroes|alvos>.png". Devolve os caminhos."""
        os.makedirs(pasta, exist_ok=True)
        gravados = []
        for elemento in self.elementos(comparacao):
            figura = self.criar_figura(comparacao, elemento, estilo, "claro")
            z = z_do_elemento(elemento)
            nome = f"{z:02d} {elemento}" if z < 9999 else elemento
            caminho = os.path.join(pasta, self._nome_arquivo(f"{nome} - {comparacao.tipo}") + ".png")
            figura.savefig(caminho, dpi=200, facecolor=figura.get_facecolor())
            gravados.append(caminho)
        return gravados
