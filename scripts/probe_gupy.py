"""Sonda do endpoint de busca de vagas da Gupy.

Faz UMA requisição, mostra o formato da resposta e salva o corpo bruto em
tests/fixtures/gupy_job_search_real.json (ignorado pelo git; a fixture dos
testes será um recorte limpo dele).

Não tenta contornar bloqueio: se vier 403/429/captcha/Cloudflare, para e avisa.

Uso:  python scripts/probe_gupy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

URL = "https://portal.gupy.io/api/job-search/jobs"
PARAMS = {"jobName": "QA", "limit": 5, "offset": 0}
HEADERS = {
    "User-Agent": "hub-pessoal-radar-probe/0.1 (projeto pessoal, sem fins comerciais; "
    "+https://github.com/FuscaRetratil/hub-pessoal)",
    "Accept": "application/json",
}
TIMEOUT = 15
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "gupy_job_search_real.json"

HEADERS_OF_INTEREST = (
    "content-type", "server", "cf-ray", "cf-mitigated", "x-cache", "via",
    "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "ratelimit-remaining",
    "set-cookie",
)
BLOCK_MARKERS = ("cloudflare", "captcha", "cf-chl", "just a moment", "attention required",
                 "access denied", "datadome", "perimeterx")


def shape(value, indent: int = 2, depth: int = 0, max_depth: int = 4) -> None:
    """Imprime chaves, tipos e um exemplo curto de cada valor (recursivo)."""
    pad = " " * (indent * depth)
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)) and v and depth < max_depth:
                kind = "dict" if isinstance(v, dict) else f"list[{len(v)}]"
                print(f"{pad}{k}: {kind}")
                shape(v if isinstance(v, dict) else v[0], indent, depth + 1, max_depth)
            else:
                sample = json.dumps(v, ensure_ascii=False)
                if len(sample) > 80:
                    sample = sample[:77] + "..."
                print(f"{pad}{k}: {type(v).__name__} = {sample}")
    elif isinstance(value, list):
        print(f"{pad}(lista de {type(value[0]).__name__ if value else '?'})")
        if value:
            shape(value[0], indent, depth + 1, max_depth)
    else:
        print(f"{pad}{type(value).__name__} = {json.dumps(value, ensure_ascii=False)[:80]}")


def looks_blocked(resp: requests.Response) -> bool:
    if resp.status_code in (401, 403, 429, 503):
        return True
    if resp.headers.get("cf-mitigated"):
        return True
    ctype = resp.headers.get("content-type", "")
    if "html" in ctype:
        head = resp.text[:3000].lower()
        return any(m in head for m in BLOCK_MARKERS)
    return False


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # console do Windows
    except Exception:
        pass

    print(f"GET {URL} params={PARAMS}")
    try:
        resp = requests.get(URL, params=PARAMS, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"[ERRO] Falha de conexão: {exc!r}")
        return 2

    print(f"URL final: {resp.url}")
    if resp.history:
        print("Redirecionamentos: " + " -> ".join(str(r.status_code) for r in resp.history))
    print(f"Status: {resp.status_code}  ({resp.elapsed.total_seconds():.2f}s, {len(resp.content)} bytes)")
    print("Headers relevantes:")
    for h in HEADERS_OF_INTEREST:
        if h in resp.headers:
            val = resp.headers[h]
            if h == "set-cookie":  # só os nomes dos cookies, não os valores
                val = ", ".join(sorted({c.split("=", 1)[0].strip() for c in val.split(",") if "=" in c}))
            print(f"  {h}: {val}")

    if looks_blocked(resp):
        print("\n[PARE] Parece bloqueio/limitação (403/429/captcha/Cloudflare). Não vou insistir.")
        print("Início do corpo:\n" + resp.text[:500])
        return 3
    if not resp.ok:
        print(f"\n[PARE] HTTP {resp.status_code}. Início do corpo:\n{resp.text[:500]}")
        return 4

    try:
        payload = resp.json()
    except ValueError:
        print("\n[PARE] Resposta 200 mas não é JSON. Início do corpo:\n" + resp.text[:500])
        return 5

    print("\nChaves de nível superior:", list(payload) if isinstance(payload, dict) else type(payload).__name__)
    if isinstance(payload, dict):
        if "pagination" in payload:
            print("pagination =", json.dumps(payload["pagination"], ensure_ascii=False))
        data = payload.get("data")
        if isinstance(data, list) and data:
            print(f"\ndata: {len(data)} itens. Chaves do primeiro item:", list(data[0]))
            print("\nFormato do primeiro item (tipo = exemplo):")
            shape(data[0])
            desc = data[0].get("description")
            if isinstance(desc, str):
                print(f"\nTamanho de description nos itens: {[len(d.get('description') or '') for d in data]}")
        else:
            print("\n[AVISO] 'data' vazio ou ausente.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResposta bruta salva em {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
