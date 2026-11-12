"""Coletor do Radar de vagas.

Uso (na raiz do repositório):
    python -m radar.main --dry-run          # só mostra o que coletaria, não grava nada
    python -m radar.main                    # coleta e grava docs/data/radar/jobs.json
    python -m radar.main --only gupy        # roda uma fonte só
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .normalize import compile_vocab
from .sources import build_sources

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT.parent / "docs" / "data" / "radar" / "jobs.json"

log = logging.getLogger("radar")


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def collect(sources: list, previous: dict) -> tuple[list[dict], dict]:
    """Roda cada fonte. Se uma falhar, mantém as vagas anteriores dela em vez de esvaziar o painel."""
    previous_by_source: dict[str, list[dict]] = {}
    for job in previous.get("jobs", []):
        previous_by_source.setdefault(job.get("source"), []).append(job)

    jobs: list[dict] = []
    status: dict[str, dict] = {}
    for source in sources:
        try:
            got = [job.to_dict() for job in source.fetch()]
            status[source.name] = {"ok": True, "count": len(got)}
            jobs.extend(got)
        except Exception as exc:  # uma fonte quebrada não pode derrubar as outras
            kept = previous_by_source.get(source.name, [])
            status[source.name] = {
                "ok": False,
                "count": len(kept),
                "kept_previous": True,
                "error": f"{type(exc).__name__}: {exc}"[:300],
            }
            jobs.extend(kept)
            log.error("fonte %s falhou: %s", source.name, exc)
    jobs.sort(key=lambda j: j.get("published_at") or "", reverse=True)
    return jobs, status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Coletor do Radar de vagas")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--only", nargs="*", help="nomes das fontes a rodar")
    parser.add_argument("--dry-run", action="store_true", help="não grava arquivo, só mostra o resultado")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_json(ROOT / "config" / "queries.json", {})
    vocab = compile_vocab(load_json(ROOT / "config" / "skills.json", []))
    sources = build_sources(config, vocab, args.only)
    if not sources:
        log.error("nenhuma fonte configurada")
        return 1

    previous = load_json(args.out, {}) or {}
    jobs, status = collect(sources, previous)

    for name, info in status.items():
        log.info("%s: %s", name, info)

    if all(not info["ok"] for info in status.values()):
        log.error("todas as fontes falharam, arquivo não foi alterado")
        return 1

    if args.dry_run:
        print(f"\n{len(jobs)} vagas. Primeiras 5:")
        for job in jobs[:5]:
            print(f"- {job['title']} | {job['company']} | {job['city']} | {job['level']} | {job['area']} | {job['reqs']}")
        return 0

    unchanged = previous.get("jobs") == jobs and previous.get("sources") == status
    if unchanged:
        log.info("nada mudou desde a última coleta, arquivo mantido")
        return 0

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": status,
        "jobs": jobs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log.info("gravado %s com %d vagas", args.out, len(jobs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
