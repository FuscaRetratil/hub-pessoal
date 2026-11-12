import json
from pathlib import Path

import pytest

from radar.normalize import compile_vocab
from radar.sources.gupy import GupySource, extract_items, parse_job

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "gupy_sample.json").read_text(encoding="utf-8"))
ROOT = Path(__file__).resolve().parent.parent
VOCAB = compile_vocab(json.loads((ROOT / "radar" / "config" / "skills.json").read_text(encoding="utf-8")))


def parsed():
    return {j.id: j for j in (parse_job(raw, VOCAB) for raw in FIXTURE["data"]) if j}


def test_ignora_vaga_sem_id():
    assert set(parsed()) == {"1001", "1002", "1003"}


def test_estagio_presencial():
    job = parsed()["1001"]
    assert (job.level, job.area, job.mode, job.city) == ("Estágio", "QA/Testes", "Presencial", "Recife")
    assert job.published_at == "2026-11-10"
    assert job.url == "https://orbita.gupy.io/jobs/1001"
    assert {"Testes manuais", "Casos de teste", "Jira", "Python", "SQL"} <= set(job.reqs)


def test_remota_vira_cidade_remoto():
    job = parsed()["1002"]
    assert (job.mode, job.city, job.level) == ("Remoto", "Remoto", "Júnior")
    assert {"Cypress", "JavaScript", "Postman", "CI/CD", "Docker", "Inglês"} <= set(job.reqs)


def test_hibrida_pleno():
    job = parsed()["1003"]
    assert (job.mode, job.level, job.area) == ("Híbrido", "Pleno", "Desenvolvimento")
    assert {"React", "TypeScript", "JavaScript"} <= set(job.reqs)
    assert "Java" not in job.reqs


def test_extract_items_formatos():
    assert extract_items([{"id": 1}]) == [{"id": 1}]
    assert extract_items({"jobs": [{"id": 2}]}) == [{"id": 2}]
    with pytest.raises(ValueError, match="chaves recebidas"):
        extract_items({"outra_coisa": 1})


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    """Devolve a mesma página para qualquer termo; registra as chamadas."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(params)
        return FakeResponse(self.payload)


def test_fetch_junta_termos_sem_duplicar_ids():
    session = FakeSession(FIXTURE)
    source = GupySource(VOCAB, terms=["qa", "teste"], per_page=50, delay=0, session=session)
    jobs = source.fetch()
    assert {j.id for j in jobs} == {"1001", "1002", "1003"}
    assert [c["name"] for c in session.calls] == ["qa", "teste"]  # página curta encerra a paginação


def test_fetch_pagina_ate_vir_pagina_curta():
    full_page = {"data": [{"id": i, "name": f"Vaga {i}", "careerPageName": "X"} for i in range(2)]}
    session = FakeSession(full_page)
    source = GupySource(VOCAB, terms=["qa"], per_page=2, max_pages=3, delay=0, session=session)
    source.fetch()
    assert [c["offset"] for c in session.calls] == [0, 2, 4]
