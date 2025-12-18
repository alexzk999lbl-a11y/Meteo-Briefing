import os
import time
import requests
from datetime import datetime, timezone

# Outils Selenium pour serveur Linux (Headless)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- 1. RECUPERATION DES SECRETS ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]

# --- 2. CONFIGURATION ---
NOM_FICHIER = "carte_fronts.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_GENERATION_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

def recuperer_cookie():
    print("--- Démarrage Robot Selenium ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Invisible
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(URL_LOGIN)
        print("Page de login atteinte.")
        
        # Remplissage
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        
        # Clic Bouton (Image ou Submit)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
            
        time.sleep(5) # Pause pour laisser le temps au cookie d'arriver
        
        # Vol du cookie PHPSESSID
        cookies = driver.get_cookies()
        for cookie in cookies:
            if cookie['name'] == 'PHPSESSID':
                print("Cookie PHPSESSID trouvé !")
                return cookie['value']
        return None
    except Exception as e:
        print(f"Erreur Selenium: {e}")
        return None
    finally:
        driver.quit()

def telecharger_image(cookie_val):
    # Calcul date UTC
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour
    if h < 6: heure = 0
    elif h < 12: heure = 6
    elif h < 18: heure = 12
    else: heure = 18
    date_str = now_utc.strftime(f"%Y%m%d{heure:02d}0000")
    print(f"Carte visée : {heure}h00 UTC")

    # Téléchargement avec Requests
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie_val)
    
    params = {
        'time': str(int(time.time())), 
        'type': 'front/europeouest',
        'date': date_str,
        'mode': 'img'
    }
    
    resp = session.get(URL_GENERATION_IMAGE, params=params)
    if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
        with open(NOM_FICHIER, 'wb') as f:
            f.write(resp.content)
        print("SUCCES : Image téléchargée.")
    else:
        print("ECHEC : Pas d'image.")

if __name__ == "__main__":
    cookie = recuperer_cookie()
    if cookie:
        telecharger_image(cookie)
    else:
        print("Impossible de récupérer le cookie.")
