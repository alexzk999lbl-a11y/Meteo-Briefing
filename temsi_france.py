import os
import time
import requests
from datetime import datetime, timezone, timedelta

# Outils Selenium (Identique à main.py)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- 1. SECRETS ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]

# --- 2. CONFIGURATION ---
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_GENERATION_IMAGE = "https://aviation.meteo.fr/affiche_image.php"
NOM_FICHIER = "temsi_france.png"

def recuperer_cookie():
    print("--- 1. Connexion Selenium (Même protocole que Fronts) ---")
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
                print("   [OK] Cookie sécurisé récupéré.")
                return cookie['value']
        return None
    except Exception as e:
        print(f"   [ERREUR] Selenium: {e}")
        return None
    finally:
        driver.quit()

def telecharger_carte_intelligente(session):
    # Logique TEMSI : Validité 3h (00, 03, 06, 09, 12, 15, 18, 21)
    # On tente l'heure actuelle, puis -3h, puis -6h (Recul)
    
    now_utc = datetime.now(timezone.utc)
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    # Arrondi au multiple de 3 inférieur
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # LISTE DES TYPES A TESTER (Priorité France, Secours Europe)
    TYPES_CARTES = ['temsi/france', 'temsi/euroc'] 

    # Boucle Temporelle (0h, -3h, -6h)
    for i in range(3):
        date_obj = heure_base - timedelta(hours=3 * i)
        date_str = date_obj.strftime("%Y%m%d%H0000")
        heure_lisible = date_obj.strftime("%Hh00 UTC")
        
        # Boucle Type (France puis Europe)
        for type_carte in TYPES_CARTES:
            print(f"--- Tentative : {type_carte} à {heure_lisible} ---")
            
            params = {
                'time': str(int(time.time())), 
                'type': type_carte,
                'date': date_str,
                'mode': 'img'
            }
            
            try:
                resp = session.get(URL_GENERATION_IMAGE, params=params)
                
                # Vérification rigoureuse (Code 200 + Contenu Image + Taille > 1ko)
                if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', '') and len(resp.content) > 1000:
                    with open(NOM_FICHIER, 'wb') as f:
                        f.write(resp.content)
                    print(f"   [SUCCES TOTAL] Image enregistrée : {NOM_FICHIER} ({type_carte})")
                    return True # On arrête tout, on a l'image
                else:
                    print(f"   [ECHEC] Serveur code: {resp.status_code} | Taille: {len(resp.content)}")
            except Exception as e:
                print(f"   [ERREUR] {e}")

    print("[FATAL] Aucune carte récupérée après toutes les tentatives.")
    return False

if __name__ == "__main__":
    cookie = recuperer_cookie()
    if cookie:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        session.cookies.set('PHPSESSID', cookie)
        
        reussite = telecharger_carte_intelligente(session)
        if not reussite:
            exit(1) # Force le ROUGE dans GitHub
    else:
        print("[FATAL] Echec connexion.")
        exit(1)
