from matplotlib.figure import Figure

from models.elementosQuimicos import z_do_elemento
from models.graficosModel import FONTE, TEMAS

# Lei de Moseley (aproximada): Kα ≈ 10,2 eV × (Z − 1)². Uma linha bem abaixo disso é da série L.
_KALFA_KEV_POR_Z2 = 0.0102


def familia_da_linha(z, energia):
    """"K" ou "L", pela energia da linha comparada à Kα estimada do elemento (as linhas L ficam bem abaixo)."""
    kalfa = _KALFA_KEV_POR_Z2 * (z - 1) ** 2
    return "K" if energia >= 0.5 * kalfa else "L"


class SensibilidadeModel:
    """Calcula a sensibilidade por elemento e por amostra."""

    @staticmethod
    def _converter_para_g_por_kg(valor, unidade):
        """Converte uma concentração para g/kg."""
        unidade_normalizada = str(unidade or "").strip().lower().replace(" ", "")
        valor = float(valor)

        if unidade_normalizada == "g/kg":
            return valor
        if unidade_normalizada == "mg/kg":
            return valor / 1000

        raise ValueError(f"Unidade de concentração não suportada: {unidade}")

    def calcular(self, concentracoes, areas_normalizadas, c_padrao, tempo_contagem):
        """Retorna amostra -> (elemento, energia) -> sensibilidade."""
        try:
            tempo = float(str(tempo_contagem).strip().replace(",", "."))  # aceita "100,5"
        except (TypeError, ValueError):
            raise ValueError(f"O tempo de contagem \"{tempo_contagem}\" não é um número (ex.: 100 ou 100,5).")

        if tempo <= 0:
            raise ValueError("O tempo de contagem deve ser maior que zero.")

        elementos_padrao = (c_padrao or {}).get("elementos", {})
        resultado = {}
        for bloco in concentracoes.values():
            if not isinstance(bloco, dict):
                continue

            for nome_amostra, elementos in bloco.items():
                areas_amostra = areas_normalizadas.get(nome_amostra, {})
                resultado[nome_amostra] = {}

                if not isinstance(elementos, dict):
                    continue

                for chave in elementos:
                    area = areas_amostra.get(chave)
                    elemento = chave[0] if isinstance(chave, tuple) else chave
                    dados_padrao = elementos_padrao.get(elemento, {})
                    concentracao_padrao = dados_padrao.get("valor")
                    unidade_padrao = dados_padrao.get("unidade", "mg/kg")
                    try:
                        area = float(area)
                        concentracao_padrao = self._converter_para_g_por_kg(
                            concentracao_padrao,
                            unidade_padrao,
                        )
                    except (TypeError, ValueError):
                        continue

                    if area == 0 or concentracao_padrao == 0:
                        continue

                    resultado[nome_amostra][chave] = (area / tempo) / concentracao_padrao
        return resultado

    def pontos_do_padrao(self, resultado_padrao, tempo_contagem):
        """
        Sensibilidade de cada linha do PRÓPRIO padrão: (área / tempo) / concentração certificada (g/kg).
        Devolve [(Z, elemento, energia, família "K"/"L", sensibilidade)], em ordem de Z.
        """
        tempo = float(str(tempo_contagem).strip().replace(",", "."))
        elementos_padrao = (resultado_padrao.c_padrao or {}).get("elementos", {})
        pontos = []
        for (elemento, energia), area in (resultado_padrao.area_padrao or {}).items():
            dados = elementos_padrao.get(elemento)
            if not dados or elemento == "Ar":
                continue
            try:
                concentracao = self._converter_para_g_por_kg(dados.get("valor"), dados.get("unidade", "mg/kg"))
                area = float(area)
            except (TypeError, ValueError):
                continue
            if area <= 0 or concentracao <= 0:
                continue
            z = z_do_elemento(elemento)
            pontos.append((z, elemento, energia, familia_da_linha(z, energia), (area / tempo) / concentracao))
        return sorted(pontos)

    def figura_por_z(self, pontos, titulo, tema="claro"):
        """Sensibilidade × Z (eixo log), uma série para as linhas K e outra para as L, cada ponto com o símbolo."""
        t = TEMAS[tema]
        figura = Figure(figsize=(9, 5.2))
        figura.set_facecolor(t["fundo"])
        ax = figura.add_axes([0.09, 0.12, 0.88, 0.76])
        ax.set_facecolor(t["fundo"])
        estilos = {"K": ("o", "#3987e5", "Linhas K"), "L": ("s", "#e08a2e", "Linhas L")}
        for familia, (marcador, cor, rotulo) in estilos.items():
            serie = [p for p in pontos if p[3] == familia]
            if not serie:
                continue
            ax.scatter([p[0] for p in serie], [p[4] for p in serie], marker=marcador, s=46, color=cor,
                       edgecolor=t["fundo"], linewidth=0.8, label=rotulo, zorder=3)
            for z, elemento, energia, _, valor in serie:
                ax.annotate(elemento, (z, valor), textcoords="offset points", xytext=(0, 7), ha="center",
                            fontsize=8, color=t["tinta2"], fontfamily=FONTE)
        ax.set_yscale("log")
        ax.set_xlabel("Número atômico (Z)", color=t["tinta2"], fontfamily=FONTE)
        ax.set_ylabel("Sensibilidade (cps / (g/kg))", color=t["tinta2"], fontfamily=FONTE)
        ax.grid(True, which="major", color=t["linha"], linewidth=0.8)
        ax.tick_params(colors=t["tinta2"])
        for lado in ax.spines.values():
            lado.set_color(t["linha"])
        if pontos:
            ax.legend(frameon=False, labelcolor=t["tinta2"], prop={"family": FONTE, "size": 9})
        else:
            ax.text(0.5, 0.5, "Nenhuma linha do padrão com valor certificado.", ha="center", va="center",
                    transform=ax.transAxes, color=t["apagado"])
        figura.text(0.09, 0.95, titulo, ha="left", va="top", fontsize=13, fontweight="bold", color=t["tinta"],
                    fontfamily=FONTE)
        return figura
