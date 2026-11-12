"""Sonda: a `description` da listagem da Gupy vem completa?

Para algumas vagas de tests/fixtures/gupy_job_search_real.json (gerado por probe_gupy.py):
  1. lê o robots.txt do portal e do subdomínio da empresa e diz se a página da vaga é permitida;
  2. baixa a página da vaga (só se o robots permitir), acha os campos de texto da vaga no
     JSON embutido (__NEXT_DATA__) e compara com a description da listagem.

Pausa de 1,5 s entre requisições, User-Agent identificado, para se houver bloqueio.
Nada é salvo no repositório.

Uso:  python scripts/probe_gupy_detail.py
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from radar.normalize import norm, strip_html  # noqa: E402

UA = "hub-pessoal-radar-probe/0.1 (projeto pessoal, sem fins comerciais; +https://github.com/FuscaRetratil/hub-pessoal)"
HEADERS = {"User-Agent": UA}
DELAY = 1.5
TIMEOUT = 15
SAMPLE_IDS = (12871194, 12866870)  # FCamara (fim suspeito) e SoftExpert

_last = 0.0


class Blocked(Exception):
    pass


def get(url: str) -> requests.Response:
    global _last
    wait = DELAY - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    print(f"  GET {url[:110]} -> {resp.status_code} ({len(resp.content)} bytes)")
    head = resp.text[:3000].lower() if "html" in resp.headers.get("content-type", "") else ""
    if resp.status_code in (401, 403, 429, 503) or resp.headers.get("cf-mitigated") or any(
        m in head for m in ("captcha", "cf-chl", "just a moment", "attention required")
    ):
        raise Blocked(f"{url} -> HTTP {resp.status_code}")
    return resp


_robots: dict[str, RobotFileParser] = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = RobotFileParser()
        resp = get(base + "/robots.txt")
        if resp.status_code == 404:
            rp.parse([])  # sem robots.txt = tudo permitido
            print("    (sem robots.txt)")
        else:
            lines = resp.text.splitlines()
            rp.parse(lines)
            print("    robots.txt:", " | ".join(l.strip() for l in lines if l.strip())[:400])
        _robots[base] = rp
    return _robots[base].can_fetch("hub-pessoal-radar", url)


def find_job(node):
    """Procura no JSON do Next.js o dicionário que tem os textos da vaga."""
    if isinstance(node, dict):
        if isinstance(node.get("description"), str) and any(
            k in node for k in ("responsibilities", "prerequisites", "additionalInformation")
        ):
            return node
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            found = find_job(v)
            if found:
                return found
    return None


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(text))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raw_path = ROOT / "tests" / "fixtures" / "gupy_job_search_real.json"
    items = {j["id"]: j for j in json.loads(raw_path.read_text(encoding="utf-8"))["data"]}

    try:
        print("portal.gupy.io (a API que o coletor usa):")
        print("  /api/job-search/jobs permitido?", allowed("https://portal.gupy.io/api/job-search/jobs?jobName=QA"))

        for job_id in SAMPLE_IDS:
            item = items[job_id]
            url = item["jobUrl"]
            print(f"\n== {item['name'].strip()} (id {job_id})")
            if not allowed(url):
                print("  robots.txt NÃO permite a página da vaga. Não vou baixar.")
                continue
            html = get(url).text
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
            job = find_job(json.loads(m.group(1))) if m else None
            if job:
                fields = {k: v for k, v in job.items() if isinstance(v, str) and len(v) > 40}
                print("  campos de texto na página:", {k: len(v) for k, v in fields.items()})
                order = ("description", "responsibilities", "prerequisites", "relevantExperiences",
                         "additionalInformation")
                page_text = "\n".join(strip_html(job[k]) for k in order if isinstance(job.get(k), str))
            else:
                print("  [aviso] __NEXT_DATA__ não encontrado; comparando com o texto da página inteira")
                page_text = strip_html(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S))

            listing, page = compact(item["description"]), compact(page_text)
            ratio = difflib.SequenceMatcher(None, listing, page, autojunk=False).ratio()
            print(f"  listagem: {len(listing)} chars úteis | página: {len(page)} chars úteis | semelhança {ratio:.2f}")
            print("  listagem contida na página?", listing in page)
            tail = listing[-60:]
            pos = page.find(tail)
            if pos >= 0:
                print(f"  texto da página depois do fim da listagem: {len(page) - pos - len(tail)} chars")
            print("  fim da página:", page_text.strip()[-150:].replace("\n", " "))
    except Blocked as exc:
        print(f"\n[PARE] Bloqueio/limitação: {exc}. Não vou insistir.")
        return 3
    except requests.RequestException as exc:
        print(f"\n[ERRO] rede: {exc!r}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
