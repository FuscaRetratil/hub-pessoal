import json
from pathlib import Path

import pytest

from radar.normalize import compile_vocab, extract_reqs
from radar.sources import gupy
from radar.sources.gupy import GupySource, extract_items, parse_job


def company_name(raw):
    return gupy.company_name(raw)


def unglue(text):
    return gupy.unglue(text)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "gupy_sample.json").read_text(encoding="utf-8"))
ROOT = Path(__file__).resolve().parent.parent
VOCAB = compile_vocab(json.loads((ROOT / "radar" / "config" / "skills.json").read_text(encoding="utf-8")))


def parsed():
    return {j.id: j for j in (parse_job(raw, VOCAB) for raw in FIXTURE["data"]) if j}


# --- parse_job com o formato real -------------------------------------------------------

def test_ignora_vaga_sem_id():
    assert set(parsed()) == {"12871194", "12866870", "12864155", "12861486"}


def test_remota_com_slogan_no_lugar_da_empresa():
    job = parsed()["12871194"]
    assert job.title == "Analista de QA Pleno"  # espaços sobrando removidos
    assert job.company == "Fcamara"  # "VENHA SER #SANGUELARANJA 🧡🚀" -> subdomínio
    assert (job.mode, job.city, job.level, job.area) == ("Remoto", "Remoto", "Pleno", "QA/Testes")
    assert job.published_at == "2026-11-11"
    assert job.url.startswith("https://fcamara.gupy.io/job/")
    assert {"Java", "Testes de performance", "Testes de API", "CI/CD", "Git", "BDD", "SQL", "Scrum", "Kanban", "API REST"} <= set(job.reqs)
    assert "JavaScript" not in job.reqs


def test_prefixo_carreiras_vira_nome_da_empresa():
    job = parsed()["12866870"]
    assert job.company == "SoftExpert"
    assert (job.mode, job.city, job.level, job.area) == ("Remoto", "Remoto", "Pleno", "QA/Testes")
    assert "Testes automatizados" in job.reqs
    # "requisitos funcionais e de performance" não é pedir teste de performance
    assert "Testes de performance" not in job.reqs


def test_hibrida_junior_com_cidade():
    job = parsed()["12864155"]
    assert job.company == "Stefanini Latam"
    assert (job.mode, job.city, job.level) == ("Híbrido", "San Salvador", "Júnior")
    assert {"Scrum", "SQL", "Java"} <= set(job.reqs)


def test_presencial_sem_nivel_no_titulo():
    job = parsed()["12861486"]
    assert (job.mode, job.city, job.level, job.area) == ("Presencial", "Bogotá, D.c.", "Não informado", "QA/Testes")
    assert "CI/CD" in job.reqs


def test_estagio_pelo_tipo_da_vaga():
    raw = dict(FIXTURE["data"][3], id=1, name="Analista de testes", type="vacancy_type_internship")
    assert parse_job(raw, VOCAB).level == "Estágio"


# --- empresa (regra c) -------------------------------------------------------------------

@pytest.mark.parametrize(
    "page_name, url, expected",
    [
        ("Stefanini Latam", "https://stefaninilatam.gupy.io/job/x", "Stefanini Latam"),
        ("Carreiras SoftExpert", "https://softexpert.gupy.io/job/x", "SoftExpert"),
        ("Trabalhe na Orbita Pagamentos", "https://orbita.gupy.io/job/x", "Orbita Pagamentos"),
        ("Montreal | Tecnologia e Inovação", "https://montreal.gupy.io/job/x", "Montreal"),
        ("Grupo Exemplo – Carreiras", "https://grupoexemplo.gupy.io/job/x", "Grupo Exemplo"),
        ("Coca-Cola FEMSA", "https://cocacola.gupy.io/job/x", "Coca-Cola FEMSA"),
        ("Cimento Nacional Programa de Estágio 2027", "https://estagiocn.gupy.io/job/x", "Cimento Nacional"),
        ("Estágio em Tecnologia do Instituto Infnet", "https://estagio-tech-infnet.gupy.io/job/x", "Instituto Infnet"),
        ("Programa de Estágio 2027", "https://programaestagiosolvi.gupy.io/job/x", "Programaestagiosolvi"),
        ("VENHA SER #SANGUELARANJA 🧡🚀", "https://fcamara.gupy.io/job/x", "Fcamara"),
        ("Faça parte do nosso time!", "https://casa-digital.gupy.io/job/x", "Casa Digital"),
        ("", "https://nuvemsul.gupy.io/job/x", "Nuvemsul"),
        ("Venha ser Feliz", "https://exemplo.com/vaga", "Venha ser Feliz"),  # sem subdomínio: fica o que tem
        ("", "", "Não informada"),
    ],
)
def test_company_name(page_name, url, expected):
    assert company_name({"careerPageName": page_name, "jobUrl": url}) == expected


# --- palavras grudadas na descrição ----------------------------------------------------

def test_unglue_separa_titulos_grudados():
    assert unglue("Requisitos e qualificaçõesPython e SQL") == "Requisitos e qualificações\nPython e SQL"


def test_unglue_nao_quebra_nomes_de_tecnologia():
    text = "JavaScript, TypeScript, GitHub, NoSQL, JUnit e iOS"
    assert unglue(text) == text


def test_reqs_encontram_competencia_grudada():
    raw = dict(FIXTURE["data"][3], id=2, description="Requisitos e qualificaçõesPython e Cypress")
    assert {"Python", "Cypress"} <= set(parse_job(raw, VOCAB).reqs)
    assert "Python" not in extract_reqs("Requisitos e qualificaçõesPython", VOCAB)  # o problema que unglue resolve


# --- extract_items -----------------------------------------------------------------------

def test_extract_items_formato_real():
    assert extract_items({"data": [{"id": 1}], "pagination": {}}) == [{"id": 1}]


@pytest.mark.parametrize("payload", [{"outra_coisa": 1}, [{"id": 1}], {"data": None}])
def test_extract_items_formato_inesperado(payload):
    with pytest.raises(ValueError, match="formato inesperado"):
        extract_items(payload)


# --- fetch (rede simulada) ---------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    """Devolve a mesma página para qualquer termo; registra as chamadas."""

    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return FakeResponse(self.payload, self.status_code)


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(gupy.time, "sleep", calls.append)
    return calls


def test_fetch_usa_endpoint_novo_e_junta_termos(sleeps):
    session = FakeSession(FIXTURE)
    jobs = GupySource(VOCAB, terms=["qa", "teste"], per_page=50, session=session).fetch()
    assert {j.id for j in jobs} == {"12871194", "12866870", "12864155", "12861486"}
    assert all(c["url"] == "https://portal.gupy.io/api/job-search/jobs" for c in session.calls)
    assert [c["params"] for c in session.calls] == [
        {"jobName": "qa", "limit": 50, "offset": 0},
        {"jobName": "teste", "limit": 50, "offset": 0},
    ]
    assert "hub-pessoal-radar" in session.calls[0]["headers"]["User-Agent"]
    assert session.calls[0]["timeout"]


def test_fetch_pausa_entre_requisicoes_e_respeita_minimo(sleeps):
    session = FakeSession(FIXTURE)
    GupySource(VOCAB, terms=["qa", "teste", "dev"], delay=0, session=session).fetch()
    assert len(session.calls) == 3
    assert sleeps == [1.5, 1.5]  # uma pausa entre cada requisição, nunca abaixo de 1,5 s


def test_fetch_pagina_ate_max_pages(sleeps):
    full_page = {"data": [{"id": i, "name": f"Vaga {i}"} for i in range(2)], "pagination": {"total": 100}}
    session = FakeSession(full_page)
    GupySource(VOCAB, terms=["qa"], per_page=2, max_pages=3, session=session).fetch()
    assert [c["params"]["offset"] for c in session.calls] == [0, 2, 4]


def test_fetch_para_quando_chega_no_total(sleeps):
    full_page = {"data": [{"id": i, "name": f"Vaga {i}"} for i in range(2)], "pagination": {"total": 4}}
    session = FakeSession(full_page)
    GupySource(VOCAB, terms=["qa"], per_page=2, max_pages=5, session=session).fetch()
    assert [c["params"]["offset"] for c in session.calls] == [0, 2]  # não pede a página 3, que viria vazia


@pytest.mark.parametrize("status", [403, 429])
def test_fetch_bloqueio_vira_erro_claro(sleeps, status):
    session = FakeSession({}, status_code=status)
    with pytest.raises(RuntimeError, match="bloque"):
        GupySource(VOCAB, terms=["qa"], session=session).fetch()
    assert len(session.calls) == 1  # não insiste


def test_fetch_erro_de_rede_propaga_para_main_manter_vagas_antigas(sleeps):
    session = FakeSession({}, status_code=500)
    with pytest.raises(RuntimeError):
        GupySource(VOCAB, terms=["qa"], session=session).fetch()
