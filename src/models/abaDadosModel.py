from models.leitorArquivoModel import ler_picos, nome_amostra as _nome_amostra


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

    def montar(self, arquivos, areas_normalizadas, erros_normalizados, fatores_normalizacao):
        """
        Recebe os arquivos de amostra + os dicionários já calculados em ConcentracaoModel e devolve
        um bloco por amostra: [(nome da amostra, fator de normalização, linhas de picos)],
        cada linha na ordem de CABECALHO.
        """
        blocos = []

        for arquivo in arquivos:
            nome_amostra = _nome_amostra(arquivo)
            fator = fatores_normalizacao.get(nome_amostra, "")
            try:
                fator = round(float(fator), 2)
            except (TypeError, ValueError):
                pass

            linhas = []
            for pico in ler_picos(arquivo):
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

            blocos.append((nome_amostra, fator, linhas))

        return blocos
