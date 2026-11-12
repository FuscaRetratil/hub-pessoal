from dataclasses import asdict, dataclass, field


@dataclass
class Job:
    """Uma vaga já normalizada, no formato que a página lê em jobs.json."""

    id: str
    source: str          # gupy | solides | google
    title: str
    company: str
    city: str            # "Remoto" quando a vaga é remota
    mode: str            # Presencial | Híbrido | Remoto
    level: str           # Estágio | Trainee | Júnior | Pleno | Sênior | Não informado
    area: str            # QA/Testes | Desenvolvimento | Dados | ... | Outras
    url: str
    published_at: str    # AAAA-MM-DD, vazio se a fonte não informar
    reqs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
