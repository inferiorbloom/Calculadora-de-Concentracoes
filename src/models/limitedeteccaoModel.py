import math

from models.leitorArquivoModel import nome_amostra as _nome_arquivo


class LimiteDeteccaoModel:

    def _buscar_valor_por_elemento(self, dados, nome_amostra, elemento):
        if not isinstance(dados, dict):
            return None

        amostra_dados = dados.get(nome_amostra)
        if not isinstance(amostra_dados, dict):
            return None

        if elemento in amostra_dados:
            return amostra_dados[elemento]

        for chave, valor in amostra_dados.items():
            if isinstance(chave, tuple) and chave and chave[0] == elemento:
                return valor

        return None

    def _buscar_valor_em_mapeamento(self, dados, elemento):
        if not isinstance(dados, dict):
            return None

        if elemento in dados:
            return dados[elemento]

        for chave, valor in dados.items():
            if isinstance(chave, tuple) and chave and chave[0] == elemento:
                return valor

        return None

    def _buscar_concentracao_padrao(self, c_padrao, elemento):
        if not isinstance(c_padrao, dict):
            return None

        elementos = c_padrao.get("elementos")
        if isinstance(elementos, dict):
            info = elementos.get(elemento)
            if isinstance(info, dict):
                return info.get("valor")

        return c_padrao.get(elemento)

    def calcular_limite_deteccao(self, arquivos_fullReport, arquivo_padrao, c_padrao, areas_normalizadas, concentracoes, area_padrao=None):

        # reorganiza as concentrações
        concentracoes = self.reorganizar_concentracoes(concentracoes)

        limites = {}

        for arquivo, backgrounds in arquivos_fullReport.items():

            limites_area = {}

            for elemento, bg in backgrounds.items():

                limites_area[elemento] = 3 * math.sqrt(bg)

            limites[arquivo] = limites_area

        nome_padrao = _nome_arquivo(arquivo_padrao or "")

        ld_resultado = {}
        for arquivo, elementos in limites.items():
            # a chave é o .txt vinculado na lista de arquivos (ou o próprio .pdf)
            nome = _nome_arquivo(arquivo)
            ld_resultado[nome] = {}

            for elemento, limite_area in elementos.items():
                eh_padrao = (nome == nome_padrao)

                if eh_padrao:
                    area_padrao_valor = self._buscar_valor_em_mapeamento(area_padrao or {}, elemento)
                    conc_padrao_valor = self._buscar_concentracao_padrao(c_padrao, elemento)

                    if area_padrao_valor not in [None, "", 0] and conc_padrao_valor not in [None, "", 0]:
                        try:
                            conc_valor = float(conc_padrao_valor)
                            area_padrao_valor = float(area_padrao_valor)
                        except (TypeError, ValueError):
                            pass
                        else:
                            ld = (conc_valor * limite_area) / area_padrao_valor
                            ld_resultado[nome][elemento] = ld
                            continue

                area_norm = self._buscar_valor_por_elemento(areas_normalizadas, nome, elemento)
                conc = self._buscar_valor_por_elemento(concentracoes, nome, elemento)

                if area_norm not in [None, "", 0] and conc not in [None, "", 0]:
                    try:
                        conc_valor = float(conc)
                        area_norm_valor = float(area_norm)
                    except (TypeError, ValueError):
                        continue

                    ld = (conc_valor * limite_area) / area_norm_valor
                    ld_resultado[nome][elemento] = ld
    
        return ld_resultado

    def reorganizar_concentracoes(self, concentracoes):

        concentracoes_novas = {}

        for bloco in concentracoes.values():

            for arquivo, elementos in bloco.items():

                concentracoes_novas[arquivo] = {}

                for elemento, valor in elementos.items():

                    concentracoes_novas[arquivo][elemento] = float(valor)

        return concentracoes_novas