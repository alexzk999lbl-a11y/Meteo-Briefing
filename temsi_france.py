import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "temsi_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_PAGE_TEMSI = "https://aviation.meteo.fr/temsi.php" 

def recuperer_carte_visuelle():
    print("--- 1. Démarrage Selenium (Mode 'Plus grande image') ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. LOGIN
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        time.sleep(3)
        
        # 2. ACCES PAGE TEMSI
        print(f"--- 2. Navigation vers {URL_PAGE_TEMSI}")
        driver.get(URL_PAGE_TEMSI)
        time.sleep(3) # Pause pour chargement complet

        # 3. ANALYSE DE TOUTES LES IMAGES
        print("--- 3. Analyse dimensionnelle des images...")
        images = driver.find_elements(By.TAG_NAME, "img")
        
        url_carte = None
        surface_max = 0
        
        for img in images:
            try:
                # On récupère les dimensions réelles à l'écran
                w = img.size['width']
                h = img.size['height']
                surface = w * h
                src = img.get_attribute("src")
                
                # On ignore les images minuscules (logos, puces, icones)
                if surface > 20000 and src: 
                    print(f"   > Candidat trouvé : {w}x{h} px | {src[-30:]}")
                    if surface > surface_max:
                        surface_max = surface
                        url_carte = src
            except:
                continue

        if not url_carte:
            print("[FATAL] Aucune grande image trouvée sur la page.")
            # Debug : on affiche le titre de la page pour voir si on est bien connecté
            print(f"Titre page actuelle : {driver.title}")
            exit(1)

        print(f"--- 4. Vainqueur identifié (La plus grande) : {url_carte}")

        # 4. TELECHARGEMENT (Avec transfert de session)
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        # Transfert des cookies Selenium vers Requests
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        resp = session.get(url_carte)
        if resp.status_code == 200:
            with open(NOM_FICHIER, 'wb') as f:
                f.write(resp.content)
            print(f"[SUCCES] TEMSI France téléchargée ({len(resp.content)} octets).")
        else:
            print(f"[ECHEC] Erreur download : {resp.status_code}")
            exit(1)

    except Exception as e:
        print(f"[ERREUR CRITIQUE] : {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_carte_visuelle()
