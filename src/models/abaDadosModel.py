import pandas as pd

from models.leitorArquivoModel import ler_picos, nome_amostra as _nome_amostra


class AbaDadosModel:
    """Monta o DataFrame usado na aba 'Dados' (dados brutos de cada amostra)."""

    def montar(self, arquivos, areas_normalizadas, erros_normalizados, fatores_normalizacao):
        """
        Recebe os arquivos de amostra + os dicionários já calculados em
        ConcentracaoModel e devolve o DataFrame pronto para a aba 'Dados'
        (sem cabeçalho, pois o cabeçalho já vai embutido nas linhas).
        """
        todos_dados = []

        for arquivo in arquivos:
            nome_amostra = _nome_amostra(arquivo)
            fator = fatores_normalizacao.get(nome_amostra, "")
            fator_formatado = ""
            if isinstance(fator, (int, float)):
                fator_formatado = round(fator, 2)
            else:
                try:
                    fator_formatado = round(float(fator), 2)
                except Exception:
                    fator_formatado = fator

            todos_dados.append([nome_amostra, "", "", "", "", "", "", "Normalização:", fator_formatado])
            todos_dados.append([
                "Elemento",
                "Z",
                "Energia (keV)",
                "Área (CPS)",
                "Erro (CPS)",
                "Erro (%)",
                "Área Normalizada (CPS)",
                "Erro Normalizado (CPS)"
            ])

            for pico in ler_picos(arquivo):
                erro_percent = (pico.erro / pico.area) * 100 if pico.area != 0 else 0

                area_norm = areas_normalizadas.get(nome_amostra, {}).get(pico.chave, "")
                erro_norm = erros_normalizados.get(nome_amostra, {}).get(pico.chave, "")

                if area_norm != "":
                    area_norm = round(float(area_norm), 0)
                if erro_norm != "":
                    erro_norm = round(float(erro_norm), 0)

                todos_dados.append([
                    pico.elemento or "",
                    pico.z,
                    pico.energia,
                    pico.area,
                    pico.erro,
                    round(erro_percent, 2),
                    area_norm,
                    erro_norm,
                ])

            todos_dados.append(["", "", "", "", "", "", "", ""])

        return pd.DataFrame(todos_dados)
