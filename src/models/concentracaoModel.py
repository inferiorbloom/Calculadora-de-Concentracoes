from models.leitorArquivoModel import ler_picos, nome_amostra


class ConcentracaoModel:
    def __init__(self):
        # situações que não impedem o cálculo, mas que o usuário precisa saber (mostradas pelo VM)
        self.avisos = []

    def _avisar(self, texto):
        if texto not in self.avisos:
            self.avisos.append(texto)

    @staticmethod
    def _area_ar(picos):
        for pico in picos:
            if pico.elemento == "Ar":
                return pico.area
        return None

    # Função para calcular as concentrações
    def calcular_concentracoes(self, lista_arquivos, lista_arquivo_padrao, c_padrao):
        """
        Retorna [concentracoes, areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao].
        Lança ArquivoInvalidoError se algum .txt não puder ser lido.
        """
        self.avisos = []

        if not lista_arquivo_padrao or not lista_arquivos:
            return {}

        c_padrao = c_padrao["elementos"]
        nome_padrao = nome_amostra(lista_arquivo_padrao)

        # Lê área do padrão
        area_padrao = {}
        erro_padrao = {}
        picos_padrao = ler_picos(lista_arquivo_padrao)
        for pico in picos_padrao:
            if pico.elemento is None:
                continue
            area_padrao[pico.chave] = pico.area
            erro_padrao[pico.chave] = pico.erro

        # _____________________________________________________________________________________________________________
        # Normalização e cálculo
        area_ar_padrao = self._area_ar(picos_padrao)
        if not area_ar_padrao:
            self._avisar(
                f"O padrão {nome_padrao} não tem pico de Ar (ou a área é zero): "
                "as concentrações foram calculadas SEM normalização."
            )

        concentracoes = {}  # {"concentracao1": {amostra: {(elemento, energia): concentração}}}
        fatores_normalizacao = {}
        areas_normalizadas = {}
        erros_normalizados = {}

        for i, arquivo in enumerate(lista_arquivos, start=1):
            nome = nome_amostra(arquivo)
            picos = ler_picos(arquivo)
            concentracoes[f"concentracao{i}"] = {nome: {}}

            # fator de normalização da amostra (baseado no Ar)
            area_ar_amostra = self._area_ar(picos)
            if area_ar_amostra and area_ar_padrao:
                fatores_normalizacao[nome] = area_ar_padrao / area_ar_amostra
            elif area_ar_padrao:
                self._avisar(f"{nome} não tem pico de Ar (ou a área é zero): calculada SEM normalização.")
            fator = fatores_normalizacao.get(nome, 1)  # usa 1 se não houver fator (sem normalização)

            areas_normalizadas[nome] = {}
            erros_normalizados[nome] = {}

            for pico in picos:
                if pico.elemento is None:
                    self._avisar(f"{nome}: elemento com Z = {pico.z} não reconhecido; o pico foi ignorado.")
                    continue
                chave = pico.chave

                # aplica normalização na área antes do cálculo
                area_net_normalizada = pico.area * fator
                areas_normalizadas[nome][chave] = area_net_normalizada
                erros_normalizados[nome][chave] = pico.erro * fator

                # Calcula concentração apenas se o elemento estiver nos padrões
                if pico.elemento not in c_padrao or chave not in area_padrao:
                    continue

                valor_padrao = c_padrao[pico.elemento].get("valor")
                if valor_padrao in (None, ""):
                    continue
                if not area_padrao[chave] or area_padrao[chave] <= 0:
                    self._avisar(
                        f"No padrão {nome_padrao}, {pico.elemento} ({pico.energia:.3f} keV) tem área "
                        f"{area_padrao[chave]:g}: esse elemento ficou sem concentração."
                    )
                    continue

                conc = (area_net_normalizada * float(valor_padrao)) / area_padrao[chave]
                concentracoes[f"concentracao{i}"][nome][chave] = conc

        return [concentracoes, areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao]
