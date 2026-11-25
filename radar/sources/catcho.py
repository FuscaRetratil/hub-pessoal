import time
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
from radar.models import Job
from radar.normalize import strip_html, infer_level, infer_area, extract_reqs

class CathoSource:
    name = "catho"

    def __init__(self, vocab: list, queries: list = None, terms: list = None, **kwargs):
        self.vocab = vocab
        self.queries = queries or terms or []
        self.kwargs = kwargs

    def fetch(self) -> List[Job]:
        # Para a Catho, as queries costumam ser a profissão direto (ex: "qa")
        queries = self.queries
        jobs = []

        print("[Catho] Iniciando Playwright...")
        with sync_playwright() as p:
            # headless=True pra rodar quieto no fundo
            browser = p.chromium.launch(headless=True) 
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            for query in queries:
                url = f"https://www.catho.com.br/vagas/{query.lower()}/"
                print(f"[Catho] Buscando: {url}")
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(3) # Pausa pro React/Vue da Catho montar a lista
                    
                    # Na Catho, os cards de vaga geralmente são tags <article> ou <li> dentro de uma lista
                    # Fragilidade: se eles mudarem a tag amanhã, o bot não acha nada.
                    cards = page.locator("article").all()
                    
                    for card in cards:
                        job = self.parse_job(card)
                        if job:
                            jobs.append(job)
                            
                except Exception as e:
                    print(f"[Catho] Erro ao buscar '{query}': {e}")
            
            browser.close()
        return jobs

    def parse_job(self, card) -> Job:
        """Tenta pescar os dados de dentro do card (Locator do Playwright)"""
        try:
            # Puxa o título e o link. Geralmente o título é um <h2> com um <a> dentro
            title_el = card.locator("h2 a").first
            if not title_el.is_visible():
                return None
                
            title = title_el.inner_text().strip()
            url = title_el.get_attribute("href")
            
            # Garante que a URL está completa
            if url and not url.startswith("http"):
                url = "https://www.catho.com.br" + url

            # A descrição costuma vir num parágrafo ou div solta
            desc_el = card.locator("p").last
            description = desc_el.inner_text().strip() if desc_el.is_visible() else ""

            # ID pode ser extraído do link
            job_id = url.split("-")[-1].replace("/", "") if url else str(time.time())

            return Job(
                id=job_id,
                source=self.name,
                title=title,
                company="Empresa na Catho", # Precisa inspecionar pra pegar a certa
                city="Não informado",       # Precisa inspecionar pra pegar a certa
                mode="Não informado",
                level=infer_level(title),
                area=infer_area(title),
                url=url,
                published_at="",
                reqs=extract_reqs(description, self.vocab)
            )
        except Exception:
            return None