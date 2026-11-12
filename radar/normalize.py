"""Funções puras de normalização. Nada aqui usa rede, então tudo é testável offline."""

import html
import re
import unicodedata

LEVEL_RULES = [
    # A ordem importa: "Jr/Pl" vira Júnior porque Júnior vem antes de Pleno.
    ("Estágio", r"\bestagi|\binternship\b|\bintern\b"),
    ("Trainee", r"\btrainee\b"),
    ("Júnior", r"\bjunior\b|\bjr\b"),
    ("Pleno", r"\bpleno\b|\bpl\b"),
    ("Sênior", r"\bsenior\b|\bsr\b|\bespecialista\b|\blead\b|\bstaff\b|\bprincipal\b"),
]

AREA_RULES = [
    ("QA/Testes", r"\bqa\b|\btestes?\b|\btester\b|\bqualidade\b|quality assurance|\bsdet\b"),
    ("Desenvolvimento", r"desenvolvedor|developer|programador|engenheir[oa] de software|front ?end|back ?end|full ?stack|\bdev\b|software engineer"),
    ("Dados", r"\bdados\b|\bdata\b|\bbi\b|analytics|cientista"),
    ("Suporte", r"suporte|help ?desk|service desk"),
    ("Design", r"\bdesigner\b|\bdesign\b|\bux\b|\bui\b"),
    ("Marketing", r"marketing|social media|\bseo\b|conteudo"),
    ("Administrativo", r"administrativ|assistente|secretari|recepcion"),
]


def norm(text: str) -> str:
    """Minúsculas, sem acento e com espaços compactados."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def dedupe_key(company: str, title: str) -> str:
    """Mesma chave que a página usa para achar a mesma vaga em fontes diferentes."""
    return f"{norm(company)}|{norm(title)}"


def strip_html(raw: str) -> str:
    text = re.sub(r"<(br|/p|/li|/div|/h\d)\s*/?>", "\n", raw or "", flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def infer_level(title: str, job_type: str = "") -> str:
    t = norm(title)
    for level, pattern in LEVEL_RULES:
        if re.search(pattern, t):
            return level
    if "internship" in norm(job_type):
        return "Estágio"
    return "Não informado"


def infer_area(title: str) -> str:
    t = norm(title)
    for area, pattern in AREA_RULES:
        if re.search(pattern, t):
            return area
    return "Outras"


def compile_vocab(vocab: list[dict]) -> list[tuple[str, list[re.Pattern]]]:
    """Prepara o vocabulário de competências (config/skills.json) para busca rápida."""
    compiled = []
    for item in vocab:
        terms = [item["name"], *item.get("aliases", [])]
        patterns = [
            re.compile(r"(?<![a-z0-9])" + re.escape(norm(term)) + r"(?![a-z0-9])")
            for term in terms
        ]
        compiled.append((item["name"], patterns))
    return compiled


def extract_reqs(text: str, compiled: list, limit: int = 12) -> list[str]:
    """Competências do vocabulário que aparecem no texto da vaga."""
    t = norm(text)
    found = []
    for name, patterns in compiled:
        if any(p.search(t) for p in patterns):
            found.append(name)
            if len(found) >= limit:
                break
    return found
