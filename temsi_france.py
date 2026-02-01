import os
import time
import requests
from datetime import datetime, timezone, timedelta

# Outils Selenium
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
URL_GENERATION_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

def recuperer_cookie():
    print("--- Connexion TEMSI (Selenium) ---")
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
        
        time.sleep(5)
        
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'PHPSESSID':
                print("   [OK] Cookie récupéré.")
                return cookie['value']
        return None
    except Exception as e:
        print(f"   [ERREUR] Login: {e}")
        return None
    finally:
        driver.quit()

def tenter_telechargement(session, date_obj):
    """Essaie de télécharger la carte pour une date donnée"""
    date_str = date_obj.strftime("%Y%m%d%H0000")
    heure_lisible = date_obj.strftime("%Hh00 UTC")
    
    print(f"   > Tentative pour {heure_lisible}...")
    
    params = {
        'time': str(int(time.time())), 
        'type': 'temsi/france',
        'date': date_str,
        'mode': 'img'
    }
    
    try:
        resp = session.get(URL_GENERATION_IMAGE, params=params, timeout=15)
        
        # On vérifie si c'est bien une image (et pas une page HTML d'erreur)
        if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
            # Vérification de la taille (une image erreur fait souvent < 1ko)
            if len(resp.content) > 1000:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print(f"   [SUCCES] Image trouvée et téléchargée ({len(resp.content)} octets).")
                return True
            else:
                print("   [INFO] Fichier trop petit (probablement une erreur vide).")
    except Exception as e:
        print(f"   [ERREUR] Téléchargement: {e}")
        
    return False

def logique_intelligente(cookie_val):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie_val)
    
    # 1. On calcule le créneau actuel (arrondi à 3h)
    now_utc = datetime.now(timezone.utc)
    # On arrondit l'heure au multiple de 3 inférieur
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # 2. BOUCLE DE RECHERCHE (On essaie T, puis T-3h, puis T-6h)
    # Exemple : on essaie 15h, si vide -> 12h, si vide -> 09h
    for i in range(3): 
        date_test = heure_base - timedelta(hours=3 * i)
        
        reussite = tenter_telechargement(session, date_test)
        if reussite:
            return # On a trouvé, on s'arrête !
        
        print("   [INFO] Carte introuvable, on tente le créneau précédent...")

    print("[ECHEC FINAL] Aucune carte TEMSI trouvée sur les 9 dernières heures.")
    # On force une erreur pour que GitHub passe au ROUGE si vraiment rien ne marche
    exit(1)

if __name__ == "__main__":
    cookie = recuperer_cookie()
    if cookie:
        logique_intelligente(cookie)
    else:
        print("[FATAL] Impossible de se connecter.")
        exit(1)
