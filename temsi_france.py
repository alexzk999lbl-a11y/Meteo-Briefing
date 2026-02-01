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
# On va directement sur la page qui affiche la carte TEMSI
URL_PAGE_TEMSI = "https://aviation.meteo.fr/temsi.php" 

def recuperer_image_depuis_page():
    print("1. Démarrage du Navigateur...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Mode invisible
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # --- PHASE 1 : LOGIN ---
        print("2. Connexion au site...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        time.sleep(3) # On attend que le login se valide
        
        # --- PHASE 2 : ALLER SUR LA PAGE TEMSI ---
        print(f"3. Visite de la page TEMSI : {URL_PAGE_TEMSI}")
        driver.get(URL_PAGE_TEMSI)
        
        # On attend un peu que la carte se charge
        time.sleep(3)
        
        # --- PHASE 3 : TROUVER L'IMAGE SUR LA PAGE ---
        # On cherche l'image principale. Sur Aeroweb, les cartes sont générées via "affiche_image.php"
        # On demande à Selenium de trouver l'image dont la source contient ce mot clé.
        print("4. Recherche de la carte sur la page...")
        element_image = driver.find_element(By.CSS_SELECTOR, "img[src*='affiche_image.php']")
        
        # On récupère l'URL exacte de cette image (le lien que le site a généré lui-même)
        url_image_valide = element_image.get_attribute("src")
        print(f"   Trouvé ! URL de l'image : {url_image_valide[:50]}...")
        
        # --- PHASE 4 : TELECHARGEMENT ---
        # On doit utiliser les cookies de Selenium pour télécharger
        print("5. Téléchargement du fichier...")
        
        # On transfère les cookies de Selenium vers Requests
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        # On télécharge l'URL qu'on vient de trouver
        resp = session.get(url_image_valide)
        
        if resp.status_code == 200:
            with open(NOM_FICHIER, 'wb') as f:
                f.write(resp.content)
            print(f"[SUCCES] TEMSI téléchargée ({len(resp.content)} octets).")
        else:
            print(f"[ECHEC] Erreur téléchargement : {resp.status_code}")
            exit(1)

    except Exception as e:
        print(f"[ERREUR] Un problème est survenu : {e}")
        # On affiche le code source de la page si on ne trouve pas l'image (pour le diagnostic)
        # print(driver.page_source[:500]) 
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_image_depuis_page()
