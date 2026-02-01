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
# C'EST LA CLE MANQUANTE : Le site veut savoir qu'on est sur la page TEMSI
URL_REFERER_TEMSI = "https://aviation.meteo.fr/temsi.php" 

def recuperer_cookie():
    print("1. Connexion Selenium...")
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
        print(f"   [ERREUR LOGIN] : {e}")
        return None
    finally:
        driver.quit()

def telecharger_temsi(session, type_code, date_obj):
    date_str = date_obj.strftime("%Y%m%d%H0000")
    heure_lisible = date_obj.strftime("%Hh00 UTC")
    
    print(f"   > Test: '{type_code}' pour {heure_lisible}...")
    
    params = {
        'time': str(int(time.time())), 
        'type': type_code,
        'date': date_str,
        'mode': 'img'
    }
    
    resp = session.get(URL_GENERATION_IMAGE, params=params)
    
    # On vérifie la taille (>1ko) pour être sûr que c'est une image et pas une icône d'erreur
    if resp.status_code == 200 and len(resp.content) > 1000:
        with open(NOM_FICHIER, 'wb') as f:
            f.write(resp.content)
        print(f"      [SUCCES] Image trouvée ! ({len(resp.content)} octets)")
        return True
    else:
        # On affiche le code erreur pour comprendre (403 = Interdit, 404 = Pas trouvée)
        print(f"      [ECHEC] Code: {resp.status_code} | Taille: {len(resp.content)} octets")
        return False

def script_principal(cookie_val):
    session = requests.Session()
    # ON TROMPE LE SERVEUR ICI : On dit qu'on vient de la page TEMSI
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': URL_REFERER_TEMSI
    })
    session.cookies.set('PHPSESSID', cookie_val)
    
    # LISTE DES NOMS POSSIBLES (On essaie les deux standards)
    TYPES_A_TESTER = ['temsi/france', 'temsi_france']
    
    # 1. Calcul de l'heure de base (arrondi 3h)
    now_utc = datetime.now(timezone.utc)
    heure_base = now_utc.replace(minute=0, second=0, microsecond=0)
    heure_base = heure_base - timedelta(hours=heure_base.hour % 3)
    
    # 2. BOUCLE (Temps et Types)
    for i in range(3): # On recule de 0h, 3h, 6h
        date_test = heure_base - timedelta(hours=3 * i)
        
        for code_temsi in TYPES_A_TESTER:
            if telecharger_temsi(session, code_temsi, date_test):
                return # Gagné, on s'arrête
                
    print("[ECHEC TOTAL] Aucune carte trouvée.")
    exit(1)

if __name__ == "__main__":
    cookie = recuperer_cookie()
    if cookie:
        script_principal(cookie)
    else:
        exit(1)
