import pytest

from radar.normalize import (
    compile_vocab,
    dedupe_key,
    extract_reqs,
    infer_area,
    infer_level,
    norm,
    strip_html,
)

VOCAB = compile_vocab(
    [
        {"name": "Java", "aliases": []},
        {"name": "JavaScript", "aliases": ["js"]},
        {"name": "CI/CD", "aliases": ["jenkins", "github actions"]},
        {"name": "Inglês", "aliases": ["english"]},
        {"name": "C#", "aliases": []},
    ]
)


def test_norm_remove_acento_e_espacos():
    assert norm("  Analista   de QA Júnior ") == "analista de qa junior"


def test_dedupe_key_ignora_acento_e_caixa():
    assert dedupe_key("Vértice Logística", "Analista de QA Júnior") == dedupe_key(
        "vertice logistica", "analista de qa junior"
    )


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Estagiário de QA", "Estágio"),
        ("Estágio em Desenvolvimento Web", "Estágio"),
        ("Analista de QA Jr", "Júnior"),
        ("Analista de Testes Júnior", "Júnior"),
        ("Analista de QA Jr/Pl", "Júnior"),
        ("Desenvolvedor Pleno", "Pleno"),
        ("Engenheiro de Software Sênior", "Sênior"),
        ("Trainee em Tecnologia", "Trainee"),
        ("Analista de Dados", "Não informado"),
    ],
)
def test_infer_level(title, expected):
    assert infer_level(title) == expected


def test_infer_level_usa_tipo_da_vaga_quando_titulo_nao_diz():
    assert infer_level("Auxiliar de TI", "vacancy_type_internship") == "Estágio"


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Analista de QA Júnior", "QA/Testes"),
        ("Estagiário de Testes", "QA/Testes"),
        ("Desenvolvedor Frontend", "Desenvolvimento"),
        ("Analista de Dados Júnior", "Dados"),
        ("Analista de Suporte", "Suporte"),
        ("Designer de Produto", "Design"),
        ("Cozinheiro", "Outras"),
    ],
)
def test_infer_area(title, expected):
    assert infer_area(title) == expected


def test_extract_reqs_nao_confunde_java_com_javascript():
    assert extract_reqs("Conhecimento em JavaScript", VOCAB) == ["JavaScript"]
    assert extract_reqs("Java e JS", VOCAB) == ["Java", "JavaScript"]


def test_extract_reqs_aliases_e_acentos():
    found = extract_reqs("Pipelines com Jenkins. INGLES avançado. C# desejável.", VOCAB)
    assert found == ["CI/CD", "Inglês", "C#"]


def test_extract_reqs_respeita_limite():
    assert len(extract_reqs("java js jenkins english c#", VOCAB, limit=2)) == 2


def test_strip_html():
    assert strip_html("<p>Olá&nbsp;<b>mundo</b></p><ul><li>a</li><li>b</li></ul>").split() == ["Olá", "mundo", "a", "b"]
