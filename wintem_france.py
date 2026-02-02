import os
import time
import requests
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- CONFIGURATION STRICTE ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "wintem_france.png"

# URLS
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

# LE CODE EXACT EXTRAIT DE VOTRE HTML
TYPE_CARTE = "wintemp/fr/france/fl020" 

def get_session_cookie():
    """Authentification Selenium pour récupérer le PHPSESSID"""
    print("--- 1. Authentification ---")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        time.sleep(5)
        
        for cookie in driver.get_cookies():
            if cookie['name'] == 'PHPSESSID':
                print("   [OK] Session récupérée.")
                return cookie['value']
        return None
    except Exception as e:
        print(f"   [CRASH LOGIN] {e}")
        return None
    finally:
        driver.quit()

def download_wintem(cookie):
    """Téléchargement direct avec filtre de taille pour éviter l'image d'erreur"""
    print(f"--- 2. Téléchargement ({TYPE_CARTE}) ---")
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie)
    
    # WINTEM sort généralement toutes les 3h. On scanne les créneaux pour trouver la valide.
    now_utc = datetime.now(timezone.utc)
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # On teste : Prochaine, Actuelle, Précédente
    liste_dates = [
        heure_base + timedelta(hours=3),
        heure_base,
        heure_base - timedelta(hours=3)
    ]
    
    for date_obj in liste_dates:
        date_str = date_obj.strftime("%Y%m%d%H0000")
        nom_heure = date_obj.strftime("%Hh UTC")
        
        params = {
            'time': str(int(time.time())),
            'type': TYPE_CARTE,
            'date': date_str,
            'mode': 'img'
        }
        
        print(f"   > Test validité : {nom_heure}...")
        
        try:
            r = session.get(URL_IMAGE, params=params, timeout=20)
            
            # FILTRE : Si image < 15Ko, c'est le tableau d'erreur -> On jette.
            taille = len(r.content)
            if r.status_code == 200 and taille > 15000:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(r.content)
                print(f"   [VICTOIRE] WINTEM valide téléchargée ({taille} o).")
                return True
            else:
                print(f"   [INFO] Fichier trop petit ({taille} o). Carte pas encore prête.")
                
        except Exception as e:
            print(f"   [ERREUR] {e}")

    print("[FATAL] Aucune carte WINTEM valide trouvée.")
    return False

if __name__ == "__main__":
    c = get_session_cookie()
    if c:
        if not download_wintem(c):
            exit(1)
    else:
        exit(1)
