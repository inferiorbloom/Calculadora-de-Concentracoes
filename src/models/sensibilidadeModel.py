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