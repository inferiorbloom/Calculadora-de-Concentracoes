from dataclasses import dataclass, field


@dataclass
class ResultadoPadrao:
    """Tudo o que foi calculado com UM padrão. Cada padrão tem a sua instância, para não misturar resultados."""

    nome: str  # identificador único do padrão (nome do arquivo, sem extensão)
    arquivo_padrao: str
    c_padrao: dict  # padrão certificado escolhido ({"nome": ..., "elementos": {...}})
    concentracoes: dict
    areas_normalizadas: dict
    fatores_normalizacao: dict
    erros_normalizados: dict
    area_padrao: dict
    erro_padrao: dict
    erros_concentracao: dict = field(default_factory=dict)
    unidade_padrao: dict = field(default_factory=dict)
    resultado_limite: dict = field(default_factory=dict)
    z_score_resultado: dict = field(default_factory=dict)
    sensibilidade_resultado: dict = field(default_factory=dict)
    tempo_contagem: str = ""  # usado na Sensibilidade (e no gráfico sensibilidade × Z)
    graficos_traco: dict = field(default_factory=dict)  # amostra -> elementos no traço escolhidos no slider
    # amostra -> {"majoritario": set, "traco": set}: elementos desmarcados na tabela avançada de cada gráfico
    graficos_excluidos: dict = field(default_factory=dict)

    @property
    def nome_certificado(self):
        return (self.c_padrao or {}).get("nome", "")

    @property
    def rotulo(self):
        """Texto usado na tela para identificar o padrão."""
        return f"{self.nome} · {self.nome_certificado}" if self.nome_certificado else self.nome

    @property
    def resultados(self):
        """Mesma lista devolvida por ConcentracaoModel.calcular_concentracoes."""
        return [
            self.concentracoes,
            self.areas_normalizadas,
            self.fatores_normalizacao,
            self.erros_normalizados,
            self.area_padrao,
            self.erro_padrao,
        ]
