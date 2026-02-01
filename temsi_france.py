import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "temsi_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"

def debug_screenshot(driver, nom="erreur_page.png"):
    driver.save_screenshot(nom)
    print(f"[DEBUG] Capture d'écran sauvegardée : {nom}")

def recuperer_temsi_via_navigation():
    print("--- 1. Démarrage Selenium (Mode Explorateur) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Taille d'écran HD pour être sûr que les menus s'affichent
    chrome_options.add_argument("--window-size=1920,1080") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # --- LOGIN ---
        print("2. Login...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        # On attend d'être sur la page d'accueil (URL contient 'accueil')
        try:
            WebDriverWait(driver, 10).until(EC.url_contains("accueil"))
            print(f"   [OK] Connecté. Page actuelle : {driver.current_url}")
        except:
            print("   [ATTENTION] Pas de redirection 'accueil' détectée. On continue quand même...")

        # --- RECHERCHE DU LIEN TEMSI ---
        print("3. Recherche du lien 'TEMSI' dans le menu...")
        
        # On cherche tous les liens qui contiennent "TEMSI" dans leur texte ou leur URL
        liens = driver.find_elements(By.TAG_NAME, "a")
        lien_cible = None
        
        for lien in liens:
            txt = lien.text.lower()
            href = lien.get_attribute("href")
            if href and ("temsi" in href.lower() or "temsi" in txt):
                # On privilégie la France si possible
                if "france" in txt or "france" in href.lower():
                    print(f"   > LIEN GAGNANT TROUVÉ : '{lien.text}' -> {href}")
                    lien_cible = href
                    break
                # Sinon on garde le lien TEMSI générique en secours
                elif not lien_cible:
                    print(f"   > Lien potentiel : '{lien.text}' -> {href}")
                    lien_cible = href

        if not lien_cible:
            print("[FATAL] Impossible de trouver un lien 'TEMSI' sur la page d'accueil.")
            # On liste les liens pour comprendre
            print("   Liens vus sur la page : " + ", ".join([l.text for l in liens[:10]]) + "...")
            debug_screenshot(driver)
            exit(1)

        # --- NAVIGATION VERS LA PAGE CIBLE ---
        print(f"4. Navigation vers : {lien_cible}")
        driver.get(lien_cible)
        time.sleep(3)

        # --- RECUPERATION IMAGE (LA PLUS GRANDE) ---
        print("5. Recherche de l'image carte...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                w = img.size['width']
                h = img.size['height']
                src = img.get_attribute("src")
                if w * h > surface_max and src and "affiche_image" in src:
                    surface_max = w * h
                    url_finale = src
            except:
                pass
        
        if not url_finale:
            print("[FATAL] Pas d'image de carte trouvée sur cette page.")
            debug_screenshot(driver)
            exit(1)
            
        print(f"   [VICTOIRE] Image identifiée : {url_finale}")

        # --- TELECHARGEMENT ---
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        resp = session.get(url_finale)
        if resp.status_code == 200:
            with open(NOM_FICHIER, 'wb') as f:
                f.write(resp.content)
            print(f"[SUCCES] Fichier sauvegardé ({len(resp.content)} octets).")
        else:
            print("[ECHEC] Erreur download.")
            exit(1)

    except Exception as e:
        print(f"[ERREUR CRITIQUE] : {e}")
        debug_screenshot(driver)
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_via_navigation()
