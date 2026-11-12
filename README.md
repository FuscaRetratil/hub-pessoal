# Hub pessoal

Painel pessoal com ferramentas que automatizam partes chatas da vida. Cada ferramenta é uma pasta própria.

| Ferramenta | Pasta | Estado |
|---|---|---|
| Radar de vagas | `radar/` | coletor da Gupy escrito, falta validar rodando |

A página do hub fica em `docs/` (publicada pelo GitHub Pages). Os dados de cada ferramenta ficam em `docs/data/<ferramenta>/`.

## Radar de vagas

Busca vagas nas fontes, normaliza e grava em `docs/data/radar/jobs.json`. A página lê esse arquivo e faz o resto no navegador: filtros (nível, local, área), match com as competências do seu currículo e controle de candidaturas.

Decisão de projeto: o Radar não se candidata por você. Ele prepara, você decide e envia no site da empresa.

### Como funciona

```
GitHub Actions (06:00 e 18:00)  ->  python -m radar.main  ->  docs/data/radar/jobs.json
                                                                       |
                                                         docs/index.html (GitHub Pages)
```

- O coletor **não filtra**. Ele guarda tudo que acha e a página aplica os filtros, assim você muda nível, cidade e área sem rodar nada.
- Se uma fonte falhar, o coletor mantém as vagas anteriores dela e registra o erro em `sources` dentro do `jobs.json`.
- Nível e área são deduzidos do título (`radar/normalize.py`). Os requisitos são as competências de `radar/config/skills.json` que aparecem no texto da vaga.

### Rodar na sua máquina

Precisa de Python 3.11 ou mais novo.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest                 # testes, funcionam sem internet
python -m radar.main --dry-run   # busca de verdade, mostra 5 vagas e não grava nada
python -m radar.main             # busca e grava docs/data/radar/jobs.json
```

Para ver a página com os dados: `python -m http.server -d docs 8000` e abrir http://localhost:8000.

### Fontes

- **Gupy** (`radar/sources/gupy.py`): usa o endpoint que o portal de vagas da Gupy consome. Não é API documentada e pode mudar sem aviso. Respeite a pausa entre requisições (`delay` em `radar/config/queries.json`) e confira os termos de uso da Gupy.
- **Sólides** e **Google Vagas**: ainda não escritas. Para adicionar uma fonte, veja o passo a passo em `radar/sources/__init__.py`.

### Agendamento

O workflow `.github/workflows/radar-collect.yml` roda duas vezes por dia, executa os testes e grava o resultado com um commit. Também dá para rodar na hora pela aba Actions, em "Run workflow".

O GitHub desativa agendamentos de repositórios públicos sem atividade por 60 dias. Se isso acontecer, reative na aba Actions.

### Publicar a página

No GitHub: Settings > Pages > Build and deployment > Deploy from a branch > `main` e pasta `/docs`.

## Próximos passos

1. Rodar `--dry-run` e ajustar a Gupy se o formato da resposta for diferente do esperado.
2. Ajustar `radar/config/queries.json` e `radar/config/skills.json` para o seu perfil.
3. Segunda fonte (Sólides ou Google Vagas).
4. Leitura do currículo em PDF no coletor, preenchendo as competências automaticamente.
5. Motor de match com IA, no lugar das palavras-chave (o contrato está em `docs/index.html`, objeto `ENGINES`).
6. Sincronizar candidaturas entre dispositivos. Hoje elas ficam no navegador onde você marcou.
