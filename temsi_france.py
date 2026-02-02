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
    """Force le clic via JavaScript (contourne les bugs d'affichage)"""
    driver.execute_script("arguments[0].click();", element)

def recuperer_temsi_chirurgical():
    print("--- 1. Démarrage Selenium (Séquence Complète avec Validation) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # --- PHASE 1 : LOGIN ---
        print("2. Login...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except:
            pass 
        
        # Attente redirection accueil
        try:
            wait.until(EC.url_contains("accueil"))
        except:
            pass

        # --- PHASE 2 : OUVERTURE MENU ---
        print("3. Ouverture du menu 'TEMSI-WINTEM'...")
        try:
            menu = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'TEMSI-WINTEM')]")))
            force_click(driver, menu)
            time.sleep(2) 
        except Exception as e:
            print(f"[ERREUR] Menu introuvable : {e}")
            raise

        # --- PHASE 3 : SELECTION 'FRANCE' ---
        print("4. Sélection de la zone 'FRANCE'...")
        try:
            # On cherche l'élément visible qui contient FRANCE
            xpath_france = "//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'FRANCE')]"
            france_elements = driver.find_elements(By.XPATH, xpath_france)
            
            clicked = False
            for el in france_elements:
                if el.is_displayed() and ("a" == el.tag_name or "span" == el.tag_name):
                    print(f"   > Clic sur : {el.text}")
                    force_click(driver, el)
                    clicked = True
                    break
            
            if not clicked:
                print("[ALERTE] Pas de lien 'France' évident, on essaie de continuer si la zone est déjà par défaut...")
            
            time.sleep(2) # Pause technique
            
        except Exception as e:
            print(f"[ERREUR] Sélection France : {e}")

        # --- PHASE 4 : CLIC SUR VALIDER (LE BOUTON MAGIQUE) ---
        print("5. Clic sur le bouton VALIDER...")
        try:
            # On cherche l'image exactement comme vous me l'avez donnée (valider.gif)
            btn_valider = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='valider.gif']")))
            force_click(driver, btn_valider)
            print("   [OK] Bouton Valider cliqué ! Génération de la carte...")
            time.sleep(5) # On attend que la carte charge
        except Exception as e:
            print(f"[ERREUR FATALE] Bouton Valider introuvable : {e}")
            # On sauvegarde le HTML pour voir pourquoi il n'est pas là
            with open("debug_valider.html", "w") as f: f.write(driver.page_source)
            raise

        # --- PHASE 5 : RECUPERATION DE L'IMAGE ---
        print("6. Extraction de la carte générée...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                src = img.get_attribute("src")
                w = img.size['width']
                h = img.size['height']
                
                # La carte est toujours une image dynamique (affiche_image.php) et grande
                if w * h > 50000 and src and "affiche_image" in src:
                    print(f"   > Carte trouvée : {w}x{h} px")
                    if w * h > surface_max:
                        surface_max = w * h
                        url_finale = src
            except: pass

        if url_finale:
            print(f"   [VICTOIRE] URL Finale : {url_finale}")
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            for c in driver.get_cookies(): session.cookies.set(c['name'], c['value'])
            
            resp = session.get(url_finale)
            if resp.status_code == 200:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print("[SUCCES TOTAL] Image enregistrée sur le disque.")
            else:
                print("[ECHEC DOWNLOAD]")
                exit(1)
        else:
            print("[ERREUR] Malgré le clic sur Valider, aucune carte n'est apparue.")
            driver.save_screenshot("echec_carte.png")
            exit(1)

    except Exception as e:
        print(f"[CRASH SYSTEME] : {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_chirurgical()