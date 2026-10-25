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

    def normalizar(self, lista_arquivos, lista_arquivo_padrao, sem_normalizacao="calculada SEM normalização"):
        """
        Só a normalização pelo Ar do arquivo padrão (não precisa do padrão certificado).
        Retorna [areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao];
        areas_normalizadas tem uma entrada por amostra, na ordem de lista_arquivos.
        sem_normalizacao: o fim do aviso para uma amostra sem pico de Ar.
        Lança ArquivoInvalidoError se algum .txt não puder ser lido.
        """
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

        area_ar_padrao = self._area_ar(picos_padrao)
        if not area_ar_padrao:
            self._avisar(
                f"O padrão {nome_padrao} não tem pico de Ar (ou a área é zero): as áreas ficaram SEM normalização."
            )

        fatores_normalizacao = {}
        areas_normalizadas = {}
        erros_normalizados = {}

        for arquivo in lista_arquivos:
            nome = nome_amostra(arquivo)
            picos = ler_picos(arquivo)

            # fator de normalização da amostra (baseado no Ar)
            area_ar_amostra = self._area_ar(picos)
            if area_ar_amostra and area_ar_padrao:
                fatores_normalizacao[nome] = area_ar_padrao / area_ar_amostra
            elif area_ar_padrao:
                self._avisar(f"{nome} não tem pico de Ar (ou a área é zero): {sem_normalizacao}.")
            fator = fatores_normalizacao.get(nome, 1)  # usa 1 se não houver fator (sem normalização)

            areas_normalizadas[nome] = {}
            erros_normalizados[nome] = {}
            for pico in picos:
                if pico.elemento is None:
                    self._avisar(f"{nome}: elemento com Z = {pico.z} não reconhecido; o pico foi ignorado.")
                    continue
                areas_normalizadas[nome][pico.chave] = pico.area * fator
                erros_normalizados[nome][pico.chave] = pico.erro * fator

        return [areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao]

    def normalizar_sem_calcular(self, lista_arquivos, lista_arquivo_padrao):
        """normalizar() para quem ainda não calculou (os gráficos pela área normalizada)."""
        self.avisos = []
        return self.normalizar(lista_arquivos, lista_arquivo_padrao, "ficou SEM normalização")

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
        areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao = self.normalizar(
            lista_arquivos, lista_arquivo_padrao
        )

        concentracoes = {}  # {"concentracao1": {amostra: {(elemento, energia): concentração}}}
        for i, (nome, areas) in enumerate(areas_normalizadas.items(), start=1):
            concentracoes[f"concentracao{i}"] = {nome: {}}
            for chave, area_net_normalizada in areas.items():
                elemento, energia = chave

                # Calcula concentração apenas se o elemento estiver nos padrões
                if elemento not in c_padrao or chave not in area_padrao:
                    continue

                valor_padrao = c_padrao[elemento].get("valor")
                if valor_padrao in (None, ""):
                    continue
                if not area_padrao[chave] or area_padrao[chave] <= 0:
                    self._avisar(
                        f"No padrão {nome_padrao}, {elemento} ({energia:.3f} keV) tem área "
                        f"{area_padrao[chave]:g}: esse elemento ficou sem concentração."
                    )
                    continue

                conc = (area_net_normalizada * float(valor_padrao)) / area_padrao[chave]
                concentracoes[f"concentracao{i}"][nome][chave] = conc

        return [concentracoes, areas_normalizadas, fatores_normalizacao, erros_normalizados, area_padrao, erro_padrao]
