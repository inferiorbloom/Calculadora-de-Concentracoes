import os
import re

from matplotlib.figure import Figure

FATOR_PARA_MG_KG = {"mg/kg": 1, "g/kg": 1000}
ALVO_TRACO_AUTOMATICO = 0.05  # "Distribuir automaticamente": traço com cerca de 5% do total


class GraficosModel:
    """Lógica dos gráficos de pizza (majoritário / traço). A janela fica em views/graficosView.py."""

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
        """Nomes das amostras de um ResultadoPadrao, na ordem da tabela."""
        return [nome for bloco in resultado_padrao.concentracoes.values() for nome in bloco]

    def valores_da_amostra(self, resultado_padrao, amostra):
        for bloco in resultado_padrao.concentracoes.values():
            if amostra in bloco:
                return self.valores_em_mg_kg(bloco[amostra], resultado_padrao.unidade_padrao)
        return {}

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

    def n_traco_da_amostra(self, resultado_padrao, amostra, valores, automatico):
        """
        Quantos elementos vão para o traço nessa amostra: o automático (~5%) se a caixinha estiver marcada;
        senão o que foi escolhido no slider (ou o automático, se o slider ainda não foi mexido).
        """
        if automatico or amostra not in resultado_padrao.graficos_traco:
            return self.n_traco_automatico(valores)
        return min(resultado_padrao.graficos_traco[amostra], self.max_traco(valores))

    @staticmethod
    def fracao_traco(valores, traco):
        total = sum(valores.values())
        return sum(v for _, v in traco) / total if total else 0.0

    @staticmethod
    def formatar_percentual(fracao):
        """1 casa normalmente; 2 casas abaixo de 1%, para o traço não aparecer como "0.0%"."""
        return f"{fracao:.2%}" if 0 < fracao < 0.01 else f"{fracao:.1%}"

    MIN_PERCENTUAL_NA_FATIA = 4  # fatias menores só aparecem na legenda (senão os textos se sobrepõem)

    def _pizza(self, figura, fatias, titulo):
        ax = figura.add_subplot()
        total = sum(v for _, v in fatias)
        cunhas, _, _ = ax.pie(
            [v for _, v in fatias],
            autopct=lambda p: f"{p:.1f}%" if p >= self.MIN_PERCENTUAL_NA_FATIA else "",
            startangle=90,
            counterclock=False,
            pctdistance=0.72,
        )
        ax.legend(
            cunhas,
            [f"{e} ({self.formatar_percentual(v / total)})" for e, v in fatias],
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            fontsize=9,
        )
        ax.set_title(titulo)
        ax.axis("equal")

    def criar_figuras(self, amostra, valores, n_traco):
        """Figuras do majoritário e do traço (as mesmas que aparecem na tela e que são exportadas)."""
        majoritarios, traco = self.dividir(valores, n_traco)
        fracao = self.fracao_traco(valores, traco)

        fig_maj = Figure(figsize=(5.2, 4), layout="constrained")
        fatias = majoritarios + ([("Traço", sum(v for _, v in traco))] if traco else [])
        self._pizza(fig_maj, fatias, f"Majoritário - {amostra}")

        fig_traco = Figure(figsize=(5.2, 4), layout="constrained")
        if traco:
            titulo = f"Traço - {len(traco)} elemento(s), {self.formatar_percentual(fracao)} do total"
            self._pizza(fig_traco, traco, titulo)
        else:
            ax = fig_traco.add_subplot()
            ax.set_title("Traço - nenhum elemento")
            ax.axis("off")
        return fig_maj, fig_traco

    @staticmethod
    def _nome_arquivo(texto):
        return re.sub(r'[\\/:*?"<>|]+', "_", str(texto)).strip() or "grafico"

    def exportar(self, pasta, itens):
        """
        itens: [(subpasta ou None, amostra, valores, n_traco)].
        Grava "<amostra> - majoritario.png" e, se houver traço, "<amostra> - traco.png". Devolve os caminhos.
        """
        gravados = []
        for subpasta, amostra, valores, n_traco in itens:
            if not valores:
                continue
            destino = os.path.join(pasta, self._nome_arquivo(subpasta)) if subpasta else pasta
            os.makedirs(destino, exist_ok=True)
            fig_maj, fig_traco = self.criar_figuras(amostra, valores, n_traco)
            base = os.path.join(destino, self._nome_arquivo(amostra))
            fig_maj.savefig(f"{base} - majoritario.png", dpi=200, bbox_inches="tight")
            gravados.append(f"{base} - majoritario.png")
            if self.dividir(valores, n_traco)[1]:
                fig_traco.savefig(f"{base} - traco.png", dpi=200, bbox_inches="tight")
                gravados.append(f"{base} - traco.png")
        return gravados
