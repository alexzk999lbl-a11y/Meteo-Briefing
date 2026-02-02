import os
import time
import requests
from datetime import datetime, timezone, timedelta
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
URL_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

# C'EST LE CODE QUE VOUS AVEZ TROUVÉ :
TYPE_CARTE = "sigwx/fr/france" 

def recuperer_cookie_session():
    """
    Se connecte une seule fois avec Selenium pour récupérer le sésame (PHPSESSID),
    puis ferme le navigateur. C'est la seule étape lente.
    """
    print("--- 1. Authentification (Selenium) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        time.sleep(5) # Attente validation login
        
        # Récupération du cookie
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'PHPSESSID':
                print("   [OK] Session récupérée.")
                return cookie['value']
        return None
    except Exception as e:
        print(f"   [ERREUR LOGIN] {e}")
        return None
    finally:
        driver.quit()

def telecharger_temsi_direct(cookie_val):
    """
    Utilise Requests (rapide) pour télécharger l'image via son URL directe.
    Essaie l'heure pile (ex: 15h), puis recule de 3h en 3h si la carte n'est pas prête.
    """
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie_val)
    
    # Calcul de l'heure de base (Arrondi au créneau de 3h UTC précédent)
    # TEMSI France sort toutes les 3h (00, 03, 06, 09, 12, 15, 18, 21 UTC)
    now_utc = datetime.now(timezone.utc)
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # BOUCLE DE RECHERCHE (Actuel -> -3h -> -6h)
    print("--- 2. Recherche Carte (Méthode Directe) ---")
    
    for i in range(3):
        date_cible = heure_base - timedelta(hours=3 * i)
        date_str = date_cible.strftime("%Y%m%d%H0000") # Format: 20260202090000
        heure_lisible = date_cible.strftime("%Hh00 UTC")
        
        print(f"   > Test validité : {heure_lisible} ...")
        
        # Construction URL (basée sur votre inspection)
        params = {
            'time': str(int(time.time())),
            'type': TYPE_CARTE, # sigwx/fr/france
            'date': date_str,
            'mode': 'img'
        }
        
        try:
            resp = session.get(URL_IMAGE, params=params, timeout=15)
            
            # Analyse : Si le fichier fait > 1ko, c'est une image. Sinon c'est une erreur PHP.
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print(f"   [SUCCES] Carte trouvée ! ({len(resp.content)} octets)")
                return True
            else:
                print(f"   [INFO] Pas de carte pour {heure_lisible} (Fichier trop petit ou vide).")
                
        except Exception as e:
            print(f"   [ERREUR RÉSEAU] {e}")

    print("[ECHEC TOTAL] Aucune carte TEMSI dispo sur les 9 dernières heures.")
    return False

if __name__ == "__main__":
    cookie = recuperer_cookie_session()
    if cookie:
        succes = telecharger_temsi_direct(cookie)
        if not succes:
            exit(1)
    else:
        print("[FATAL] Impossible de se connecter.")
        exit(1)
