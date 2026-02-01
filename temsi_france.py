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

def force_click(driver, element):
    driver.execute_script("arguments[0].click();", element)

def recuperer_temsi_final():
    print("--- 1. Démarrage Selenium (Mode Sniper) ---")
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
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except:
            pass # Parfois le Enter suffit
        
        time.sleep(5)

        # --- OUVERTURE MENU ---
        print("3. Ouverture du menu 'TEMSI-WINTEM'...")
        try:
            menu = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'TEMSI-WINTEM')]")))
            force_click(driver, menu)
            time.sleep(3) # Important : on laisse le menu s'ouvrir
        except:
            print("[ERREUR] Menu principal introuvable.")
            raise

        # --- RECHERCHE INTELLIGENTE DU LIEN ---
        print("4. Scan des liens du menu...")
        
        # On récupère TOUS les liens de la page maintenant que le menu est ouvert
        liens = driver.find_elements(By.TAG_NAME, "a")
        lien_trouve = None
        
        print(f"   (J'ai trouvé {len(liens)} liens au total sur la page)")
        
        for lien in liens:
            # On nettoie le texte (minuscules, sans espaces inutiles)
            txt = lien.get_attribute("innerText") or ""
            txt = txt.lower().strip()
            href = lien.get_attribute("href") or ""
            
            # On ignore les liens vides
            if not txt and not href: continue
            
            # SI le lien contient "france" (ex: "domaine : france", "france v2"...)
            if "france" in txt or "france" in href.lower():
                # On vérifie qu'il est visible (pour ne pas cliquer sur un lien caché)
                if lien.is_displayed():
                    print(f"   > CIBLE IDENTIFIEE : '{txt}'")
                    lien_trouve = lien
                    break
        
        if lien_trouve:
            print("   Clic sur le lien France...")
            force_click(driver, lien_trouve)
            time.sleep(5)
        else:
            print("[ALERTE] Je ne trouve pas 'France'. Voici les liens visibles du menu :")
            # Mouchard : on affiche les liens pour comprendre
            visibles = [l.get_attribute("innerText") for l in liens if l.is_displayed()]
            print(" | ".join(visibles[:20])) # On affiche les 20 premiers
            raise Exception("Lien France introuvable")

        # --- RECUPERATION IMAGE ---
        print("5. Recherche de l'image finale...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                src = img.get_attribute("src")
                w = img.size['width']
                h = img.size['height']
                if w * h > 50000 and src and "affiche_image" in src:
                    surface_max = w * h
                    url_finale = src
            except: pass

        if url_finale:
            print(f"   [VICTOIRE] URL : {url_finale}")
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            for c in driver.get_cookies(): session.cookies.set(c['name'], c['value'])
            
            resp = session.get(url_finale)
            if resp.status_code == 200:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print("[SUCCES TOTAL] Image enregistrée.")
            else:
                print("[ECHEC DOWNLOAD]")
        else:
            print("[ERREUR] Pas d'image trouvée sur la page finale.")
            # Debug : on affiche le titre pour savoir où on a atterri
            print(f"Page actuelle : {driver.title}")
            raise Exception("Pas d'image")

    except Exception as e:
        print(f"[CRASH] {e}")
        driver.save_screenshot("erreur_finale.png")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_final()
