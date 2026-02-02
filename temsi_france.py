import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "temsi_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"

def force_click(driver, element):
    """Force le clic JS pour contourner les blocages d'interface"""
    driver.execute_script("arguments[0].click();", element)

def recuperer_temsi_direct():
    print("--- SEQUENCE PILOTE : TEMSI FRANCE ---")
    
    # 1. SETUP NAVIGATEUR
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15)

    try:
        # 2. LOGIN
        print("> Connexion...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except:
            pass
        
        # Vérification chargement accueil
        try:
            wait.until(EC.url_contains("accueil"))
        except:
            pass # On continue, parfois l'URL ne change pas visuellement

        # 3. SEQUENCE MENU
        print("> Navigation Menu...")
        
        # A. Clic Menu Principal "TEMSI-WINTEM"
        menu_principal = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'TEMSI-WINTEM')]")))
        force_click(driver, menu_principal)
        time.sleep(1) # Bref délai pour l'ouverture
        
        # B. Clic Sous-Menu "FRANCE"
        # On cherche l'élément visible qui contient le texte exact FRANCE
        sous_menu = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'FRANCE')]")))
        force_click(driver, sous_menu)
        time.sleep(1) # Bref délai pour la prise en compte des paramètres
        
        # 4. VALIDATION
        print("> Validation...")
        # Clic sur l'image 'valider.gif' identifiée via l'inspection
        bouton_valider = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='valider.gif']")))
        force_click(driver, bouton_valider)
        
        # 5. RECUPERATION CARTE
        print("> Récupération image...")
        time.sleep(4) # Attente génération carte
        
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                src = img.get_attribute("src")
                if src and "affiche_image" in src:
                    # On prend la plus grande image "affiche_image"
                    w = img.size['width']
                    h = img.size['height']
                    if w * h > surface_max:
                        surface_max = w * h
                        url_finale = src
            except:
                continue

        if url_finale:
            # Téléchargement avec session (cookies)
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            for c in driver.get_cookies():
                session.cookies.set(c['name'], c['value'])
            
            resp = session.get(url_finale)
            if resp.status_code == 200:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print(f"[SUCCES] Carte enregistrée : {NOM_FICHIER}")
            else:
                print("[ECHEC] Erreur lors du téléchargement du fichier.")
                exit(1)
        else:
            print("[ECHEC] La carte n'est pas apparue après validation.")
            exit(1)

    except Exception as e:
        print(f"[ERREUR] {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_direct()
