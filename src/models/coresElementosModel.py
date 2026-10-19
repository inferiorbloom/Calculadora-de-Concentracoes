import json
import os

from resource_utils import resource_path, user_data_path

# Cor fixa de cada elemento nos gráficos.
# padroes/cores_elementos.json (junto do programa) traz as cores padrão. Para usar o padrão do laboratório,
# crie %APPDATA%/CXCalculator/padroes/cores_elementos.json no mesmo formato ({"Fe": "#rrggbb", ...}):
# só os elementos que estiverem nele mudam; os outros continuam com a cor padrão.
ARQUIVO_PADRAO = resource_path("padroes", "cores_elementos.json")
ARQUIVO_USUARIO = user_data_path("padroes", "cores_elementos.json")
COR_DESCONHECIDA = "#9a988f"


def _ler(caminho):
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(dados, dict):
        return {}
    # aceita só "#rrggbb"; uma cor digitada errado não pode derrubar o gráfico
    return {
        str(elemento): str(cor).strip()
        for elemento, cor in dados.items()
        if isinstance(cor, str) and len(cor.strip()) == 7 and cor.strip().startswith("#")
    }


def carregar_cores():
    """{elemento: "#rrggbb"}: as cores padrão, com as do usuário (laboratório) por cima."""
    cores = _ler(ARQUIVO_PADRAO)
    cores.update(_ler(ARQUIVO_USUARIO))
    return cores


def cor_do_elemento(elemento, cores):
    return cores.get(elemento, COR_DESCONHECIDA)
