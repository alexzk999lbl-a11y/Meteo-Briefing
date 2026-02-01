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

def sauver_debug(driver, prefixe="erreur"):
    """Sauvegarde capture d'écran ET code source HTML pour analyse"""
    try:
        driver.save_screenshot(f"{prefixe}_screen.png")
        with open(f"{prefixe}_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"[DEBUG] Preuves sauvegardées : {prefixe}_screen.png et {prefixe}_source.html")
    except:
        print("[DEBUG] Echec sauvegarde preuves")

def force_click(driver, element):
    """Force le clic via JavaScript (contourne les erreurs d'interactivité)"""
    driver.execute_script("arguments[0].click();", element)

def recuperer_temsi_force():
    print("--- 1. Démarrage Selenium (Mode Force Brute JS) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # --- LOGIN ---
        print("2. Login...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        
        # Clic Login
        try:
            btn = driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']")
            force_click(driver, btn)
        except:
            print("[ERREUR] Bouton login introuvable")
            raise

        # Attente redirection
        time.sleep(5)
        if "accueil" not in driver.current_url and "menu" not in driver.current_url:
            print(f"[ALERTE] URL inattendue après login : {driver.current_url}")
            # On continue quand même, parfois l'URL reste bizarre

        # --- RECHERCHE DU MENU ---
        print("3. Recherche Menu 'TEMSI-WINTEM'...")
        # On cherche un lien qui contient le texte, peu importe où
        try:
            menu_temsi = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'TEMSI-WINTEM')]")))
            print("   Menu repéré. Injection Clic JavaScript...")
            force_click(driver, menu_temsi)
            time.sleep(3) # Pause indispensable pour le déroulement
        except Exception as e:
            print(f"[ERREUR] Menu non trouvé : {e}")
            sauver_debug(driver, "debug_menu")
            raise

        # --- RECHERCHE LIEN FRANCE ---
        print("4. Recherche Lien 'FRANCE'...")
        try:
            # On cherche spécifiquement le lien France qui est SOUS le menu (donc visible maintenant)
            # On cherche un lien <a> qui contient "FRANCE"
            lien_france = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(),'FRANCE')]")))
            print(f"   Lien France repéré ({lien_france.get_attribute('href')}). Clic JS...")
            force_click(driver, lien_france)
            time.sleep(5)
        except Exception as e:
            print(f"[ERREUR] Lien France non trouvé : {e}")
            sauver_debug(driver, "debug_france")
            raise

        # --- RECUPERATION IMAGE ---
        print("5. Extraction de l'image...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                src = img.get_attribute("src")
                w = img.size['width']
                h = img.size['height']
                
                # Critères : Surface > 50000px (assez grand) et lien contient "affiche_image"
                if w * h > 50000 and src and "affiche_image" in src:
                    print(f"   > Candidat : {w}x{h} - {src[-20:]}")
                    if w * h > surface_max:
                        surface_max = w * h
                        url_finale = src
            except:
                pass

        if not url_finale:
            print("[FATAL] Pas d'image carte trouvée.")
            sauver_debug(driver, "debug_image")
            exit(1)

        print(f"   [VICTOIRE] URL : {url_finale}")

        # --- TELECHARGEMENT ---
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        cookies = driver.get_cookies()
        for c in cookies:
            session.cookies.set(c['name'], c['value'])
            
        resp = session.get(url_finale)
        if resp.status_code == 200:
            with open(NOM_FICHIER, 'wb') as f:
                f.write(resp.content)
            print("[SUCCES TOTAL] Image enregistrée.")
        else:
            print("[ECHEC DOWNLOAD]")
            exit(1)

    except Exception as e:
        print(f"[CRASH] {e}")
        sauver_debug(driver, "crash_final")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_force()
