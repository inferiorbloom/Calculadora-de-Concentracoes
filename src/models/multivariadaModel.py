"""
Análise multivariada das amostras de UM alvo com UM padrão: PCA (biplot), correlação (ρp) e agrupamento (HCA).

Decisões (referências completas em REFERENCIAS, que também vão para a tela e para o Excel):

1. Concentrações são dados composicionais: só as razões entre os elementos carregam informação e
   correlações calculadas direto nas concentrações podem ser espúrias. Por isso tudo é feito depois da
   transformação clr (log-razão centrada): clr(x)_j = ln(x_j / g(x)), g = média geométrica da amostra
   [Aitchison 1982].
2. PCA: decomposição em valores singulares do clr centrado (sem padronizar), o biplot composicional de
   Aitchison & Greenacre (2002); revisão de PCA em Jolliffe & Cadima (2016).
3. Correlação: coeficiente de proporcionalidade ρp nos valores clr, ρp = 1 − var(clr_i − clr_j) /
   (var(clr_i) + var(clr_j)) [Lovell et al. 2015; Erb & Notredame 2016], no lugar de Pearson nas
   concentrações.
4. HCA: distância euclidiana entre os clr (= distância de Aitchison [Aitchison et al. 2000]) e ligação de
   Ward [Ward 1963]; o uso de transformações log-razão antes de agrupar dados geoquímicos é discutido em
   Templ, Filzmoser & Reimann (2008).
5. Valores medidos abaixo do LD: por padrão entram com o valor medido. A recomendação do Analytical
   Methods Committee (2001) é guardar o resultado como medido e usar os dados não editados no trabalho
   estatístico; Helsel (2006) mostra como trocar valores por uma fração do LD distorce estatísticas e
   correlações. Como opção, podem ser trocados por 0,65 × LD (a substituição multiplicativa de
   Martín-Fernández et al. 2003; 0,65 é o padrão do zCompositions [Palarea-Albaladejo & Martín-Fernández
   2015]). Em dados não fechados (mg/kg de parte dos elementos), a substituição multiplicativa deixa os
   valores observados como estão: equivale a pôr 0,65 × LD só nas células censuradas.
6. Elemento sem valor numa amostra (pico não encontrado), mas com LD: é um "não detectado" de verdade (não
   há valor medido para usar) e recebe 0,65 × LD [Martín-Fernández et al. 2003].
7. Elemento sem valor e sem LD em alguma amostra: não há como estimar o valor sem um método de imputação
   (ex.: k-vizinhos na geometria de Aitchison [Hron, Templ & Filzmoser 2010]), que não está implementado;
   o elemento sai da análise e aparece na lista de excluídos.
"""

from dataclasses import dataclass, field

import numpy as np
from matplotlib.figure import Figure

from models.comparacaoModel import ComparacaoModel
from models.elementosQuimicos import z_do_elemento
from models.fichaInformacaoModel import nome_da_amostra
from models.graficosModel import FATOR_PARA_MG_KG, FONTE, TEMAS
from models.leitorArquivoModel import nome_amostra
from models.qualidadeModel import ld_de_referencia

FRACAO_LD = 0.65
MODOS_ABAIXO_LD = {"medido": "Valor medido", "substituir": "0,65 × LD"}
MIN_AMOSTRAS = 3
MIN_ELEMENTOS = 3  # o clr de D elementos tem D − 1 dimensões: com 3, já há duas componentes para o biplot

REFERENCIAS = [
    "Aitchison, J. (1982). The statistical analysis of compositional data. Journal of the Royal Statistical "
    "Society, Series B, 44(2), 139–177.",
    "Aitchison, J., Barceló-Vidal, C., Martín-Fernández, J. A., Pawlowsky-Glahn, V. (2000). Logratio analysis "
    "and compositional distance. Mathematical Geology, 32(3), 271–275.",
    "Aitchison, J., Greenacre, M. (2002). Biplots of compositional data. Journal of the Royal Statistical "
    "Society, Series C (Applied Statistics), 51(4), 375–392. doi:10.1111/1467-9876.00275",
    "Analytical Methods Committee (2001). Measurement of near zero concentration: recording and reporting results "
    "that fall close to or below the detection limit. Analyst, 126, 256–259.",
    "Erb, I., Notredame, C. (2016). How should we measure proportionality on relative gene expression data? "
    "Theory in Biosciences, 135(1), 21–36. doi:10.1007/s12064-015-0220-8",
    "Helsel, D. R. (2006). Fabricating data: how substituting values for nondetects can ruin results, and what "
    "can be done about it. Chemosphere, 65(11), 2434–2439. doi:10.1016/j.chemosphere.2006.04.051",
    "Hron, K., Templ, M., Filzmoser, P. (2010). Imputation of missing values for compositional data using "
    "classical and robust methods. Computational Statistics & Data Analysis, 54(12), 3095–3107.",
    "Jolliffe, I. T., Cadima, J. (2016). Principal component analysis: a review and recent developments. "
    "Philosophical Transactions of the Royal Society A, 374(2065), 20150202.",
    "Lovell, D., Pawlowsky-Glahn, V., Egozcue, J. J., Marguerat, S., Bähler, J. (2015). Proportionality: a valid "
    "alternative to correlation for relative data. PLoS Computational Biology, 11(3), e1004075. "
    "doi:10.1371/journal.pcbi.1004075",
    "Martín-Fernández, J. A., Barceló-Vidal, C., Pawlowsky-Glahn, V. (2003). Dealing with zeros and missing "
    "values in compositional data sets using nonparametric imputation. Mathematical Geology, 35(3), 253–278.",
    "Palarea-Albaladejo, J., Martín-Fernández, J. A. (2015). zCompositions — R package for multivariate "
    "imputation of left-censored data under a compositional approach. Chemometrics and Intelligent Laboratory "
    "Systems, 143, 85–96. doi:10.1016/j.chemolab.2015.02.019",
    "Templ, M., Filzmoser, P., Reimann, C. (2008). Cluster analysis applied to regional geochemical data: "
    "problems and possibilities. Applied Geochemistry, 23(8), 2198–2213.",
    "Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. Journal of the American "
    "Statistical Association, 58(301), 236–244. doi:10.1080/01621459.1963.10500845",
]


class DadosInsuficientesError(Exception):
    """Depois do tratamento, sobraram poucas amostras ou elementos para a análise."""


@dataclass
class DadosMultivariados:
    amostras: list  # códigos das amostras (linhas)
    rotulos: list  # o que aparece nos gráficos: o nome da ficha ou o código
    elementos: list  # colunas, em ordem de Z
    matriz: np.ndarray  # mg/kg, já com as substituições
    modo_abaixo_ld: str = "medido"
    # (amostra, elemento) -> o que aconteceu com a célula: "abaixo do LD (medido)", "0,65 × LD (abaixo do LD)",
    # "0,65 × LD (não detectado)"
    tratamentos: dict = field(default_factory=dict)
    excluidos: list = field(default_factory=list)  # [(elemento, motivo)]
    sem_ld: bool = False  # nenhuma amostra tinha LD (sem FullReport): os valores entram como medidos

    def contagem(self, prefixo):
        return sum(1 for texto in self.tratamentos.values() if texto.startswith(prefixo))


@dataclass
class ResultadoMultivariado:
    dados: DadosMultivariados
    clr: np.ndarray
    scores: np.ndarray  # amostras × componentes (U·S)
    cargas: np.ndarray  # elementos × componentes (V)
    variancia: np.ndarray  # fração da variância de cada componente
    correlacao: np.ndarray  # ρp entre os elementos
    ligacao: np.ndarray  # matriz de ligação de Ward (scipy)


class MultivariadaModel:

    def montar_dados(self, resultado_padrao, resultados_do_alvo, alvo=None, nomes=None, modo_abaixo_ld="medido"):
        """
        Matriz amostras × elementos (mg/kg) de UM padrão, com o tratamento descrito no topo do arquivo.
        resultados_do_alvo: todos os ResultadoPadrao do alvo (os arquivos padrão de todos ficam fora).
        """
        r = resultado_padrao
        excluir = {alvo} if alvo else set()
        padroes = ComparacaoModel._padroes(resultados_do_alvo)
        amostras = ComparacaoModel._amostras(r, padroes)
        valores = {a: ComparacaoModel.valores_com_erro(r, a, excluir) for a in amostras}
        elementos = sorted({e for v in valores.values() for e in v}, key=z_do_elemento)

        unidades = r.unidade_padrao or {}
        nome_padrao = nome_amostra(r.arquivo_padrao or "")
        sem_ld = not r.resultado_limite

        def ld_mg_kg(amostra, elemento):
            ld = ld_de_referencia(r.resultado_limite, amostra, elemento, nome_padrao)
            if ld is None:
                return None
            return ld * FATOR_PARA_MG_KG.get(str(unidades.get(elemento, "mg/kg")).strip().lower(), 1)

        colunas, excluidos, tratamentos = [], [], {}
        for elemento in elementos:
            coluna, tratamento_coluna, sem_valor = [], {}, []
            for amostra in amostras:
                medido = valores[amostra].get(elemento, (None, None))[0]
                ld = ld_mg_kg(amostra, elemento)
                if medido is not None:
                    if ld is not None and medido < ld:
                        if modo_abaixo_ld == "substituir":
                            coluna.append(FRACAO_LD * ld)
                            tratamento_coluna[amostra] = "0,65 × LD (abaixo do LD)"
                        else:
                            coluna.append(medido)
                            tratamento_coluna[amostra] = "abaixo do LD (medido)"
                    else:
                        coluna.append(medido)
                elif ld is not None:
                    coluna.append(FRACAO_LD * ld)
                    tratamento_coluna[amostra] = "0,65 × LD (não detectado)"
                else:
                    coluna.append(None)
                    sem_valor.append(amostra)

            medidos = sum(1 for a in amostras if valores[a].get(elemento))
            if sem_valor:
                lista = ", ".join(nome_da_amostra(nomes, a) or a for a in sem_valor[:6])
                mais = f" e mais {len(sem_valor) - 6}" if len(sem_valor) > 6 else ""
                excluidos.append((elemento, f"sem valor e sem LD em {len(sem_valor)} amostra(s): {lista}{mais}"))
            elif medidos == 0:
                excluidos.append((elemento, "nenhum valor medido (só não detectados)"))
            else:
                colunas.append((elemento, coluna))
                tratamentos.update({(a, elemento): t for a, t in tratamento_coluna.items()})

        dados = DadosMultivariados(
            amostras=amostras,
            rotulos=[nome_da_amostra(nomes, a) or a for a in amostras],
            elementos=[e for e, _ in colunas],
            matriz=np.array([c for _, c in colunas], dtype=float).T if colunas else np.empty((len(amostras), 0)),
            modo_abaixo_ld=modo_abaixo_ld,
            tratamentos=tratamentos,
            excluidos=excluidos,
            sem_ld=sem_ld,
        )
        if len(dados.amostras) < MIN_AMOSTRAS or len(dados.elementos) < MIN_ELEMENTOS:
            raise DadosInsuficientesError(
                f"A análise precisa de pelo menos {MIN_AMOSTRAS} amostras e {MIN_ELEMENTOS} elementos; "
                f"sobraram {len(dados.amostras)} amostra(s) e {len(dados.elementos)} elemento(s)."
                + (f"\n\nElementos excluídos:\n" + "\n".join(f"• {e}: {m}" for e, m in excluidos) if excluidos else "")
            )
        return dados

    @staticmethod
    def clr(matriz):
        """Log-razão centrada de cada linha [Aitchison 1982]. Os valores precisam ser positivos."""
        logs = np.log(matriz)
        return logs - logs.mean(axis=1, keepdims=True)

    @staticmethod
    def proporcionalidade(clr):
        """ρp entre as colunas [Lovell et al. 2015; Erb & Notredame 2016]: 1 − var(xi − xj) / (var xi + var xj)."""
        variancias = clr.var(axis=0, ddof=1)
        d = clr.shape[1]
        rho = np.ones((d, d))
        for i in range(d):
            for j in range(i + 1, d):
                soma = variancias[i] + variancias[j]
                valor = 1 - np.var(clr[:, i] - clr[:, j], ddof=1) / soma if soma > 0 else np.nan
                rho[i, j] = rho[j, i] = valor
        return rho

    def analisar(self, dados):
        from scipy.cluster.hierarchy import linkage  # só aqui: o resto do programa não precisa do scipy

        clr = self.clr(dados.matriz)
        centrado = clr - clr.mean(axis=0)
        u, s, vt = np.linalg.svd(centrado, full_matrices=False)
        # o clr de D partes tem posto D − 1: a última componente não carrega variância
        k = max(min(len(s), dados.matriz.shape[1] - 1, dados.matriz.shape[0] - 1), 1)
        u, s, vt = u[:, :k], s[:k], vt[:k]
        total = float((s ** 2).sum())
        variancia = (s ** 2) / total if total > 0 else np.zeros_like(s)
        return ResultadoMultivariado(
            dados=dados,
            clr=clr,
            scores=u * s,
            cargas=vt.T,
            variancia=variancia,
            correlacao=self.proporcionalidade(clr),
            ligacao=linkage(clr, method="ward", metric="euclidean"),
        )

    # --- figuras -----------------------------------------------------------------------------------------
    @staticmethod
    def _eixos(figura, t, retangulo=(0.1, 0.1, 0.85, 0.78)):
        ax = figura.add_axes(retangulo)
        ax.set_facecolor(t["fundo"])
        ax.tick_params(colors=t["tinta2"], labelsize=9)
        for lado in ax.spines.values():
            lado.set_color(t["linha"])
        return ax

    @staticmethod
    def _titulo(figura, titulo, subtitulo, t):
        figura.set_facecolor(t["fundo"])
        figura.text(0.03, 0.97, titulo, ha="left", va="top", fontsize=13, fontweight="bold", color=t["tinta"],
                    fontfamily=FONTE)
        figura.text(0.03, 0.925, subtitulo, ha="left", va="top", fontsize=9, color=t["apagado"], fontfamily=FONTE)

    def figura_biplot(self, resultado, titulo, tema="claro"):
        """Biplot PC1 × PC2: amostras como pontos, elementos como setas (escaladas para caber no gráfico)."""
        t = TEMAS[tema]
        figura = Figure(figsize=(9, 6.6))
        self._titulo(figura, titulo, "PCA do clr centrado (biplot composicional) · setas fora de escala, só a "
                                     "direção e o tamanho relativo entre elas contam", t)
        ax = self._eixos(figura, t)
        scores, cargas, var = resultado.scores, resultado.cargas, resultado.variancia
        pc2 = scores.shape[1] > 1
        xs = scores[:, 0]
        ys = scores[:, 1] if pc2 else np.zeros_like(xs)
        ax.axhline(0, color=t["linha"], linewidth=0.8, zorder=1)
        ax.axvline(0, color=t["linha"], linewidth=0.8, zorder=1)
        ax.scatter(xs, ys, s=38, color="#3987e5", edgecolor=t["fundo"], linewidth=0.8, zorder=3)
        for x, y, rotulo in zip(xs, ys, resultado.dados.rotulos):
            ax.annotate(rotulo, (x, y), textcoords="offset points", xytext=(5, 4), fontsize=8, color=t["tinta2"],
                        fontfamily=FONTE)

        alcance = max(np.abs(xs).max(), np.abs(ys).max(), 1e-12)
        cx = cargas[:, 0]
        cy = cargas[:, 1] if pc2 else np.zeros_like(cx)
        escala = 0.85 * alcance / max(np.hypot(cx, cy).max(), 1e-12)
        for x, y, elemento in zip(cx * escala, cy * escala, resultado.dados.elementos):
            ax.annotate("", xy=(x, y), xytext=(0, 0),
                        arrowprops={"arrowstyle": "-|>", "color": "#e08a2e", "lw": 1.3, "shrinkA": 0, "shrinkB": 0})
            ax.text(x * 1.07, y * 1.07, elemento, color="#e08a2e", fontsize=9, fontweight="bold", ha="center",
                    va="center", fontfamily=FONTE)
        ax.set_xlabel(f"PC1 ({100 * var[0]:.1f}% da variância)", color=t["tinta2"], fontfamily=FONTE)
        ax.set_ylabel(f"PC2 ({100 * var[1]:.1f}% da variância)" if pc2 else "PC2", color=t["tinta2"],
                      fontfamily=FONTE)
        limite = alcance * 1.25
        ax.set_xlim(-limite, limite)
        ax.set_ylim(-limite, limite)
        return figura

    def figura_correlacao(self, resultado, titulo, tema="claro"):
        """Mapa de calor do ρp entre os elementos (de −1 a 1), com o valor em cada célula."""
        t = TEMAS[tema]
        elementos = resultado.dados.elementos
        d = len(elementos)
        lado = min(max(5.5, 0.42 * d + 2.5), 12)
        figura = Figure(figsize=(lado + 1.2, lado))
        self._titulo(figura, titulo, "Coeficiente de proporcionalidade ρp nos valores clr", t)
        ax = self._eixos(figura, t, (0.12, 0.08, 0.72, 0.78))
        imagem = ax.imshow(resultado.correlacao, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(d), elementos, rotation=90, fontfamily=FONTE)
        ax.set_yticks(range(d), elementos, fontfamily=FONTE)
        if d <= 20:
            for i in range(d):
                for j in range(d):
                    valor = resultado.correlacao[i, j]
                    if np.isfinite(valor):
                        ax.text(j, i, f"{valor:.2f}", ha="center", va="center", fontsize=7,
                                color="#ffffff" if abs(valor) > 0.6 else "#1a1a19")
        barra = figura.colorbar(imagem, ax=ax, fraction=0.046, pad=0.03)
        barra.ax.tick_params(colors=t["tinta2"], labelsize=8)
        barra.outline.set_edgecolor(t["linha"])
        return figura

    def figura_dendrograma(self, resultado, titulo, tema="claro"):
        """Dendrograma das amostras (Ward, distância de Aitchison)."""
        from scipy.cluster.hierarchy import dendrogram

        t = TEMAS[tema]
        n = len(resultado.dados.amostras)
        figura = Figure(figsize=(min(max(8, 0.35 * n + 3), 18), 6))
        self._titulo(figura, titulo, "HCA: ligação de Ward sobre a distância de Aitchison (euclidiana no clr)", t)
        ax = self._eixos(figura, t, (0.08, 0.22, 0.9, 0.64))
        dendrogram(
            resultado.ligacao, labels=resultado.dados.rotulos, ax=ax, leaf_rotation=90, leaf_font_size=8,
            color_threshold=None, above_threshold_color=t["tinta2"],
        )
        ax.set_ylabel("Distância (Ward)", color=t["tinta2"], fontfamily=FONTE)
        for rotulo in ax.get_xticklabels():
            rotulo.set_color(t["tinta2"])
            rotulo.set_fontfamily(FONTE)
        return figura

    # --- resumo e exportação -----------------------------------------------------------------------------
    @staticmethod
    def resumo(resultado):
        """Texto do que entrou na análise e de como cada valor foi tratado."""
        d = resultado.dados
        linhas = [
            f"Amostras: {len(d.amostras)} (os arquivos padrão ficam de fora)",
            f"Elementos: {len(d.elementos)} — {', '.join(d.elementos)}",
            f"Abaixo do LD: {MODOS_ABAIXO_LD[d.modo_abaixo_ld]}",
            "",
            f"Valores abaixo do LD mantidos como medidos: {d.contagem('abaixo do LD (medido)')}",
            f"Valores abaixo do LD trocados por 0,65 × LD: {d.contagem('0,65 × LD (abaixo')}",
            f"Não detectados (sem valor, com LD) com 0,65 × LD: {d.contagem('0,65 × LD (não detectado')}",
        ]
        if d.sem_ld:
            linhas += ["", "Sem LD (nenhum FullReport vinculado): não há como saber quais valores estão abaixo do "
                           "LD, e elementos sem valor em alguma amostra saem da análise."]
        if d.excluidos:
            linhas += ["", "Elementos excluídos:"] + [f"  • {e}: {motivo}" for e, motivo in d.excluidos]
        linhas += ["", "Variância explicada (PCA):"] + [
            f"  PC{i + 1}: {100 * v:.1f}%  (acumulada {100 * resultado.variancia[: i + 1].sum():.1f}%)"
            for i, v in enumerate(resultado.variancia[:6])
        ]
        return "\n".join(linhas)

    def exportar_excel(self, caminho, resultado, titulo):
        """Planilha com os dados usados, o clr, a PCA, o ρp, o tratamento de cada valor e as referências."""
        import pandas as pd

        d = resultado.dados
        componentes = [f"PC{i + 1}" for i in range(resultado.scores.shape[1])]
        indice = pd.Index(d.rotulos, name="Amostra")
        rotulo = dict(zip(d.amostras, d.rotulos))
        tratamento = pd.DataFrame(
            [(rotulo[a], e, texto) for (a, e), texto in sorted(d.tratamentos.items())],
            columns=["Amostra", "Elemento", "Tratamento"],
        )
        with pd.ExcelWriter(caminho, engine="xlsxwriter") as writer:
            pd.DataFrame({"": [titulo, "", *self.resumo(resultado).split("\n")]}).to_excel(
                writer, sheet_name="Resumo", index=False, header=False
            )
            pd.DataFrame(d.matriz, index=indice, columns=d.elementos).to_excel(writer, sheet_name="Dados (mg kg-1)")
            pd.DataFrame(resultado.clr, index=indice, columns=d.elementos).to_excel(writer, sheet_name="clr")
            pd.DataFrame(resultado.scores, index=indice, columns=componentes).to_excel(writer, sheet_name="PCA scores")
            pd.DataFrame(resultado.cargas, index=pd.Index(d.elementos, name="Elemento"), columns=componentes).to_excel(
                writer, sheet_name="PCA cargas"
            )
            pd.DataFrame(
                {"Variância (%)": 100 * resultado.variancia, "Acumulada (%)": 100 * np.cumsum(resultado.variancia)},
                index=pd.Index(componentes, name="Componente"),
            ).to_excel(writer, sheet_name="PCA variância")
            pd.DataFrame(resultado.correlacao, index=d.elementos, columns=d.elementos).to_excel(
                writer, sheet_name="Correlação (rho p)"
            )
            tratamento.to_excel(writer, sheet_name="Tratamento", index=False)
            pd.DataFrame({"Referências": REFERENCIAS}).to_excel(writer, sheet_name="Referências", index=False)
        return caminho
