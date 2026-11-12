"""Fonte Gupy.

ATENÇÃO: usa o endpoint que o próprio portal de vagas da Gupy (portal.gupy.io) consome.
Ele NÃO é uma API documentada (a API oficial em developers.gupy.io exige token de empresa),
então pode mudar sem aviso. O antigo portal.api.gupy.io foi desligado em 2026.
Formato confirmado por scripts/probe_gupy.py em 2026-11-12:

    GET /api/job-search/jobs?jobName=QA&limit=5&offset=0
    {"data": [{id, name, description, careerPageName, careerPageUrl, careerPageLogo, type,
               publishedDate, applicationDeadline, workplaceType, city, state, jobUrl,
               badges, disabilities}],
     "pagination": {total, limit, offset}}

Tudo que depende desse formato fica neste arquivo. Se a Gupy mudar algo, o conserto fica aqui.
"""

import logging
import re
import time
import unicodedata
from urllib.parse import urlparse

import requests

from ..models import Job
from ..normalize import extract_reqs, infer_area, infer_level, norm, strip_html

log = logging.getLogger(__name__)

ENDPOINT = "https://portal.gupy.io/api/job-search/jobs"
HEADERS = {
    "User-Agent": "hub-pessoal-radar/0.2 (projeto pessoal, sem fins comerciais; "
    "+https://github.com/FuscaRetratil/hub-pessoal)",
    "Accept": "application/json",
}
MIN_DELAY = 1.5  # segundos entre requisições, nunca menos que isso
TIMEOUT = 20

MODES = {"remote": "Remoto", "hybrid": "Híbrido", "on-site": "Presencial"}

# --- Empresa -----------------------------------------------------------------------------
# A Gupy não manda o nome da empresa, só o nome da página de carreiras (careerPageName),
# que às vezes é slogan ("VENHA SER #SANGUELARANJA 🧡🚀"). Regra:
#   1. tira prefixos tipo "Carreiras X", "Trabalhe na X"  ->  "X";
#   2. se o que sobrou parece slogan (emoji, #, !, "venha", "faça parte"...), usa o
#      subdomínio do jobUrl (fcamara.gupy.io -> "Fcamara");
#   3. sem subdomínio, fica com o nome da página mesmo.
_PREFIX = re.compile(
    r"^(?:carreiras?|careers?|vagas|oportunidades|trabalhe\s+(?:conosco\s+)?(?:na|no|em)|"
    r"trabalhe\s+conosco|junte-se\s+(?:à|a|ao)|"
    r"est[aá]gio\s+(?:em\s+[\w\s]+\s+)?(?:do|da|de|na|no))\s+(?:na\s+|no\s+|da\s+|do\s+|at\s+)?(?P<rest>\S.*)$",
    re.I,
)
_SUFFIX = re.compile(
    r"\s+(?:programa\s+de\s+est[aá]gio.*)$",
    re.I,
)
_SLOGAN = re.compile(
    r"[#!?]|\b(?:venha|vem|seja|somos|faca parte|junte-se|trabalhe|carreiras?|careers?|"
    r"vagas?|oportunidades?|talentos?|jobs?|nosso time|nossa equipe|programa\s+de\s+estagio)\b"
)


def _has_emoji(text: str) -> bool:
    return any(unicodedata.category(c) == "So" for c in text)


def _subdomain_name(job_url: str) -> str:
    host = urlparse(job_url or "").hostname or ""
    if not host.endswith(".gupy.io"):
        return ""
    slug = host.split(".")[0]
    return slug.replace("-", " ").title()


def company_name(raw: dict) -> str:
    page = " ".join((raw.get("careerPageName") or "").split())
    # "Montreal | Tecnologia e Inovação", "Grupo X – Carreiras": fica a parte antes do separador.
    # Só separador com espaço dos dois lados, para não cortar "Coca-Cola".
    page = re.split(r"\s+[|–—-]\s+", page)[0]
    m = _PREFIX.match(page)
    if m:
        page = m.group("rest").strip()
    if _SUFFIX.search(page) and not _SUFFIX.match(page.strip()):
        page = _SUFFIX.sub("", page).strip()
    if page and not _has_emoji(page) and not _SLOGAN.search(norm(page)):
        return page
    return _subdomain_name(raw.get("jobUrl")) or page or "Não informada"


# --- Descrição ---------------------------------------------------------------------------
# A Gupy tira o HTML e cola os blocos: "Requisitos e qualificaçõesPython". Isso esconde a
# competência da busca por palavra inteira. Separa quando há 4+ minúsculas seguidas de uma
# maiúscula e 2+ minúsculas. Exigir 4 minúsculas antes protege JavaScript/TypeScript ("ava",
# "ype" têm 3) e GitHub; o custo é separar coisas inofensivas como "SonarQube" -> "Sonar Qube".
_GLUE = re.compile(r"(?<=[a-zà-ÿ]{4})(?=[A-ZÀ-Ý][a-zà-ÿ]{2})")


def unglue(text: str) -> str:
    return _GLUE.sub("\n", text or "")


# --- Parse -------------------------------------------------------------------------------

def extract_items(payload) -> list:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
    raise ValueError(f"formato inesperado da Gupy, esperava {{data: [...]}}; recebido: {keys}")


def parse_job(raw: dict, vocab: list) -> Job | None:
    job_id = raw.get("id")
    title = " ".join((raw.get("name") or "").split())
    if not job_id or not title:
        return None
    description = unglue(strip_html(raw.get("description") or ""))
    # workplaceType desconhecido vira Presencial: é o caso mais comum e o mais restritivo.
    mode = MODES.get((raw.get("workplaceType") or "").lower(), "Presencial")
    city = "Remoto" if mode == "Remoto" else (raw.get("city") or raw.get("state") or "Não informada").strip()
    return Job(
        id=str(job_id),
        source="gupy",
        title=title,
        company=company_name(raw),
        city=city,
        mode=mode,
        level=infer_level(title, raw.get("type") or ""),
        area=infer_area(title),
        url=raw.get("jobUrl") or "",
        published_at=(raw.get("publishedDate") or "")[:10],
        reqs=extract_reqs(f"{title}\n{description}", vocab),
    )


# --- Fonte -------------------------------------------------------------------------------

class GupySource:
    name = "gupy"

    def __init__(self, vocab, terms, per_page=50, max_pages=3, delay=MIN_DELAY, session=None):
        self.vocab = vocab
        self.terms = terms
        self.per_page = per_page
        self.max_pages = max_pages
        self.delay = max(float(delay), MIN_DELAY)
        self.session = session or requests.Session()
        self._requests = 0

    def _get_page(self, term: str, offset: int) -> tuple[list, int | None]:
        if self._requests:
            time.sleep(self.delay)
        self._requests += 1
        resp = self.session.get(
            ENDPOINT,
            params={"jobName": term, "limit": self.per_page, "offset": offset},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        if resp.status_code in (403, 429):
            # Não tenta de novo nem disfarça: a falha sobe e main.py mantém as vagas anteriores.
            raise RuntimeError(f"Gupy bloqueou ou limitou o acesso (HTTP {resp.status_code})")
        resp.raise_for_status()
        payload = resp.json()
        total = (payload.get("pagination") or {}).get("total") if isinstance(payload, dict) else None
        return extract_items(payload), total if isinstance(total, int) else None

    def fetch(self) -> list[Job]:
        # Qualquer erro sobe de propósito: um resultado parcial seria gravado como se fosse
        # completo. Com a exceção, main.py marca a fonte como falha e mantém as vagas antigas.
        jobs: dict[str, Job] = {}
        for term in self.terms:
            for page in range(self.max_pages):
                offset = page * self.per_page
                items, total = self._get_page(term, offset)
                log.info("gupy: termo=%r página=%d itens=%d total=%s", term, page + 1, len(items), total)
                for raw in items:
                    job = parse_job(raw, self.vocab)
                    if job:
                        jobs.setdefault(job.id, job)
                if len(items) < self.per_page or (total is not None and offset + self.per_page >= total):
                    break
        return list(jobs.values())
