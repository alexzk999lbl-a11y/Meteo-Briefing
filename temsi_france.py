import os
import time
import requests
from datetime import datetime, timezone

# Outils Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- 1. RECUPERATION DES MEMES SECRETS ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]

# --- 2. CONFIGURATION TEMSI ---
NOM_FICHIER = "temsi_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"
URL_GENERATION_IMAGE = "https://aviation.meteo.fr/affiche_image.php"

def recuperer_cookie():
    # On relance une session propre pour ce script
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
                return cookie['value']
        return None
    except:
        return None
    finally:
        driver.quit()

def telecharger_temsi(cookie_val):
    # REGLE TEMSI FRANCE : Validité 3h (00, 03, 06, 09...)
    now_utc = datetime.now(timezone.utc)
    h = now_utc.hour
    
    # Calcul du multiple de 3 inférieur
    heure_temsi = h - (h % 3)
    
    date_str = now_utc.strftime(f"%Y%m%d{heure_temsi:02d}0000")
    print(f"TEMSI visée : {heure_temsi}h00 UTC")

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    session.cookies.set('PHPSESSID', cookie_val)
    
    params = {
        'time': str(int(time.time())), 
        'type': 'temsi/france',   # C'est ici que ça change
        'date': date_str,
        'mode': 'img'
    }
    
    resp = session.get(URL_GENERATION_IMAGE, params=params)
    if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
        with open(NOM_FICHIER, 'wb') as f:
            f.write(resp.content)
        print("SUCCES : TEMSI téléchargée.")
    else:
        print("ECHEC : Pas d'image TEMSI.")

if __name__ == "__main__":
    cookie = recuperer_cookie()
    if cookie:
        telecharger_temsi(cookie)
