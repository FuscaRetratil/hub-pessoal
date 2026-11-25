from playwright.sync_api import sync_playwright
import time

def run_playwright_probe():
    print("Iniciando Playwright...")
    with sync_playwright() as p:
        # headless=False para você ver o navegador abrindo no Windows
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        url = "https://www.catho.com.br/vagas/qa/"
        print(f"Acessando: {url}")
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            print("Página carregada! Esperando 3 segundos para renderização do JS...")
            time.sleep(3)
            
            title = page.title()
            print(f"Título da página: {title}")
            
            links_vagas = page.locator("a[href*='/vagas/']").all()
            
            print(f"Links de vagas encontrados: {len(links_vagas)}")
            if len(links_vagas) > 0:
                print("\nExemplo do primeiro link encontrado:")
                print(links_vagas[0].inner_text().strip())
                print(links_vagas[0].get_attribute("href"))
            
            print("\n[SUCESSO] Passamos pelo bloqueio inicial da Catho usando Playwright!")

        except Exception as e:
            print(f"\n[ERRO] Aconteceu algo no caminho: {e}")
        finally:
            print("\nFechando navegador em 2 segundos...")
            time.sleep(2)
            browser.close()

if __name__ == "__main__":
    run_playwright_probe()