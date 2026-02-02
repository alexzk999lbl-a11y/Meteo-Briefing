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

# URLS OFFICIELLES
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

# LE CODE EXACT EXTRAIT DE VOTRE HTML
TYPE_CARTE = "sigwx/fr/france"

def get_session_cookie():
    """Authentification Selenium pure pour récupérer le cookie PHPSESSID"""
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
        
        # Validation (Click Image ou Submit)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        time.sleep(5) # Tempo serveur
        
        # Extraction Cookie
        for cookie in driver.get_cookies():
            if cookie['name'] == 'PHPSESSID':
                print("   [OK] Session récupérée.")
                return cookie['value']
        print("   [ERREUR] Pas de cookie de session.")
        return None
    except Exception as e:
        print(f"   [CRASH LOGIN] {e}")
        return None
    finally:
        driver.quit()

def download_map(cookie):
    """Téléchargement direct via Requests avec le code sigwx/fr/france"""
    print(f"--- 2. Téléchargement ({TYPE_CARTE}) ---")
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie)
    
    # Stratégie TEMSI : Sortie toutes les 3h (00, 03, 06, 09, 12, 15, 18, 21 UTC)
    # On teste : Heure Pile, Heure Pile - 3h, Heure Pile + 3h (pour avoir la dernière dispo)
    
    now_utc = datetime.now(timezone.utc)
    # Arrondi à l'heure multiple de 3 la plus proche (basse)
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # On teste 3 créneaux : [Futur proche, Actuel, Passé]
    liste_dates = [
        heure_base + timedelta(hours=3), # Prochaine (parfois dispo en avance)
        heure_base,                      # Actuelle
        heure_base - timedelta(hours=3)  # Précédente
    ]
    
    for date_obj in liste_dates:
        date_str = date_obj.strftime("%Y%m%d%H0000")
        nom_heure = date_obj.strftime("%Hh UTC")
        
        params = {
            'time': str(int(time.time())),
            'type': TYPE_CARTE,  # sigwx/fr/france
            'date': date_str,
            'mode': 'img'
        }
        
        print(f"   > Tentative pour {nom_heure} (Date: {date_str})...")
        
        try:
            r = session.get(URL_IMAGE, params=params, timeout=20)
            
            # FILTRE INTELLIGENT :
            # Une vraie carte TEMSI fait > 20 Ko (souvent 50-100 Ko).
            # L'image d'erreur (tableau vide) fait souvent < 10 Ko.
            taille = len(r.content)
            
            if r.status_code == 200 and taille > 15000: # Seuil sécurité 15 Ko
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(r.content)
                print(f"   [VICTOIRE] Carte valide téléchargée ! ({taille} octets)")
                return True
            else:
                print(f"   [ECHEC] Fichier trop petit ({taille} o) ou erreur serveur. Ce n'est pas la carte.")
                
        except Exception as e:
            print(f"   [ERREUR RESEAU] {e}")

    print("[FATAL] Aucune carte valide trouvée sur les créneaux testés.")
    return False

if __name__ == "__main__":
    c = get_session_cookie()
    if c:
        if not download_map(c):
            exit(1) # Force l'erreur rouge dans GitHub
    else:
        exit(1)
