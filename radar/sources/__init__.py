"""Registro de fontes.

Para adicionar uma fonte nova (Sólides, Google Vagas...):
1. Crie `radar/sources/<nome>.py` com uma classe que tenha `name` e `fetch() -> list[Job]`.
2. Registre a classe em FACTORIES abaixo.
3. Adicione um bloco com o mesmo nome em `radar/config/queries.json`.
"""

from .gupy import GupySource

FACTORIES = {"gupy": GupySource}


def build_sources(config: dict, vocab: list, only: list[str] | None = None) -> list:
    sources = []
    for name, cfg in config.items():
        if only and name not in only:
            continue
        if name not in FACTORIES:
            raise ValueError(f"fonte desconhecida em queries.json: {name}")
        sources.append(FACTORIES[name](vocab=vocab, **cfg))
    return sources
