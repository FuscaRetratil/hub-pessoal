"""Fonte Gupy.

ATENÇÃO: usa o endpoint que o próprio portal de vagas da Gupy consome. Ele NÃO é uma API
documentada (a API oficial em developers.gupy.io exige token de empresa), então pode mudar
sem aviso. Tudo que depende do formato da resposta está em `extract_items` e `parse_job`.
Se a Gupy mudar algo, o conserto deve ficar só neste arquivo.
"""

import logging
import time

import requests

from ..models import Job
from ..normalize import extract_reqs, infer_area, infer_level, strip_html

log = logging.getLogger(__name__)

ENDPOINT = "https://portal.api.gupy.io/api/job"
HEADERS = {"User-Agent": "hub-pessoal-radar/0.1 (projeto pessoal, sem fins comerciais)"}


def extract_items(payload) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "jobs", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
        raise ValueError(f"formato inesperado, chaves recebidas: {sorted(payload)}")
    raise ValueError(f"formato inesperado: {type(payload).__name__}")


def _mode(raw: dict) -> str:
    workplace = (raw.get("workplaceType") or "").lower()
    if raw.get("isRemoteWork") or workplace == "remote":
        return "Remoto"
    if workplace == "hybrid":
        return "Híbrido"
    return "Presencial"


def parse_job(raw: dict, vocab: list) -> Job | None:
    job_id = raw.get("id") or raw.get("code")
    title = (raw.get("name") or "").strip()
    if not job_id or not title:
        return None
    description = raw.get("descriptionPlainText") or strip_html(raw.get("description") or "")
    mode = _mode(raw)
    city = "Remoto" if mode == "Remoto" else (raw.get("city") or raw.get("state") or "Não informada")
    published = raw.get("publishedAt") or raw.get("publishedDate") or ""
    return Job(
        id=str(job_id),
        source="gupy",
        title=title,
        company=(raw.get("careerPageName") or raw.get("careerPageDisplayName") or "").strip(),
        city=city,
        mode=mode,
        level=infer_level(title, raw.get("type") or ""),
        area=infer_area(title),
        url=raw.get("jobUrl") or "",
        published_at=published[:10],
        reqs=extract_reqs(f"{title}\n{description}", vocab),
    )


class GupySource:
    name = "gupy"

    def __init__(self, vocab, terms, per_page=50, max_pages=3, delay=1.5, session=None):
        self.vocab = vocab
        self.terms = terms
        self.per_page = per_page
        self.max_pages = max_pages
        self.delay = delay
        self.session = session or requests.Session()

    def _get_page(self, term: str, page: int) -> list:
        resp = self.session.get(
            ENDPOINT,
            params={"name": term, "limit": self.per_page, "offset": page * self.per_page},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        return extract_items(resp.json())

    def fetch(self) -> list[Job]:
        jobs: dict[str, Job] = {}
        for term in self.terms:
            for page in range(self.max_pages):
                items = self._get_page(term, page)
                log.info("gupy: termo=%r página=%d itens=%d", term, page + 1, len(items))
                for raw in items:
                    job = parse_job(raw, self.vocab)
                    if job:
                        jobs.setdefault(job.id, job)
                if len(items) < self.per_page:
                    break
                time.sleep(self.delay)
            time.sleep(self.delay)
        return list(jobs.values())
