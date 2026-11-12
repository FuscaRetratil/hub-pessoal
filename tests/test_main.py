from radar.main import collect
from radar.models import Job


def make_job(job_id, source="gupy", published="2026-11-10"):
    return Job(
        id=job_id, source=source, title=f"Vaga {job_id}", company="Empresa", city="Recife",
        mode="Presencial", level="Júnior", area="QA/Testes", url="", published_at=published,
    )


class OkSource:
    name = "gupy"

    def fetch(self):
        return [make_job("a", published="2026-11-01"), make_job("b", published="2026-11-09")]


class BrokenSource:
    name = "solides"

    def fetch(self):
        raise RuntimeError("site mudou")


def test_collect_ordena_por_data_mais_recente():
    jobs, status = collect([OkSource()], {})
    assert [j["id"] for j in jobs] == ["b", "a"]
    assert status["gupy"] == {"ok": True, "count": 2}


def test_fonte_quebrada_mantem_vagas_anteriores_e_nao_derruba_as_outras():
    previous = {"jobs": [make_job("old", source="solides").to_dict()]}
    jobs, status = collect([OkSource(), BrokenSource()], previous)
    assert {j["id"] for j in jobs} == {"a", "b", "old"}
    assert status["solides"]["ok"] is False
    assert status["solides"]["kept_previous"] is True
    assert "site mudou" in status["solides"]["error"]
