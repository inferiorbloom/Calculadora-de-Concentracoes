from models.leitorArquivoModel import ler_picos, nome_amostra as _nome_amostra


# Razão de linhas mostrada ao lado do nome de cada amostra, por alvo: (numerador, denominador),
# cada linha como (elemento, energia de referência em keV). Vale o pico do elemento mais perto da energia.
RAZOES = {
    "Ag": (("Ag", 2.984), ("Ag", 22.103)),  # Ag L / Ag K
    "Au": (("Au", 9.713), ("Pt", 9.442)),  # Au L / Pt L
    "Rh": (("Rh", 2.696), ("Rh", 20.167)),  # Rh L / Rh K
}
TOLERANCIA_KEV = 1.0  # um pico mais longe que isso da energia de referência não é aquela linha


def _area_da_linha(picos, elemento, energia):
    candidatos = [p for p in picos if p.elemento == elemento and abs(p.energia - energia) <= TOLERANCIA_KEV]
    if not candidatos:
        return None
    return min(candidatos, key=lambda p: abs(p.energia - energia)).area


def razao_do_alvo(picos, alvo):
    """Razão entre as áreas das linhas de RAZOES[alvo] (ex.: Ag L / Ag K), ou "-" sem uma das linhas."""
    if alvo not in RAZOES:
        return "-"
    (el_num, e_num), (el_den, e_den) = RAZOES[alvo]
    numerador = _area_da_linha(picos, el_num, e_num)
    denominador = _area_da_linha(picos, el_den, e_den)
    if numerador is None or not denominador:
        return "-"
    return numerador / denominador


class AbaDadosModel:
    """Monta a aba 'Dados' (dados brutos de cada amostra)."""

    CABECALHO = [
        "Elemento",
        "Z",
        "Energia (keV)",
        "Área (CPS)",
        "Erro (CPS)",
        "Erro (%)",
        "Área Normalizada (CPS)",
        "Erro Normalizado (CPS)",
    ]

    def montar(self, arquivos, areas_normalizadas, erros_normalizados, fatores_normalizacao, alvo=None):
        """
        Recebe os arquivos de amostra + os dicionários já calculados em ConcentracaoModel e devolve
        um bloco por amostra: [(nome da amostra, fator de normalização, razão do alvo, linhas de picos)],
        cada linha na ordem de CABECALHO. A razão (ver RAZOES) usa as áreas brutas: a normalização
        multiplica as duas linhas pelo mesmo fator. Sem alvo, a razão é None.
        """
        blocos = []

        for arquivo in arquivos:
            nome_amostra = _nome_amostra(arquivo)
            fator = fatores_normalizacao.get(nome_amostra, "")
            try:
                fator = round(float(fator), 2)
            except (TypeError, ValueError):
                pass

            picos = ler_picos(arquivo)
            razao = razao_do_alvo(picos, alvo) if alvo else None

            linhas = []
            for pico in picos:
                erro_percent = (pico.erro / pico.area) * 100 if pico.area != 0 else 0

                area_norm = areas_normalizadas.get(nome_amostra, {}).get(pico.chave, "")
                erro_norm = erros_normalizados.get(nome_amostra, {}).get(pico.chave, "")

                if area_norm != "":
                    area_norm = round(float(area_norm), 0)
                if erro_norm != "":
                    erro_norm = round(float(erro_norm), 0)

                linhas.append([
                    pico.elemento or "",
                    pico.z,
                    pico.energia,
                    pico.area,
                    pico.erro,
                    round(erro_percent, 2),
                    area_norm,
                    erro_norm,
                ])

            blocos.append((nome_amostra, fator, razao, linhas))

        return blocos
