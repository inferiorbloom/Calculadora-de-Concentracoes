import math


class PropagacaoErrosModel:

    def calcular(self, concentracoes, areas_normalizadas, erros_normalizados, c_padrao, area_padrao, erro_padrao):

        erros_propagados = {}
        #variaveis relacionadas aos padrões
        c_p = {el: info['valor'] for el, info in c_padrao['elementos'].items()}
        e_p = {el: info['erro'] for el, info in c_padrao['elementos'].items()}
        unidade_padrao = {el: info['unidade'] for el, info in c_padrao['elementos'].items()}
   
        for conc, amostra_dict in concentracoes.items():

            erros_propagados[conc] = {}

            for amostra, elementos in amostra_dict.items():

                erros_propagados[conc][amostra] = {}

                for el, valor_conc in elementos.items():

                    valor_conc = float(valor_conc)

                    A = areas_normalizadas[amostra][el]
                    eA = erros_normalizados[amostra][el]

                    Ap = area_padrao[el]
                    eAp = erro_padrao[el]

                    elemento = el[0]  # pega só "Ag"

                    Cp = c_p[elemento]
                    eCp = e_p[elemento]

                    termos = []

                    if A and eA:
                        termos.append((eA/A)**2)

                    if Ap and eAp:
                        termos.append((eAp/Ap)**2)

                    if Cp and eCp:
                        termos.append((eCp/Cp)**2)

                    raiz = math.sqrt(sum(termos)) if termos else 0
                    erro = valor_conc * raiz

                    erros_propagados[conc][amostra][el] = erro
        return erros_propagados, unidade_padrao
