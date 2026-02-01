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
    """Force le clic JavaScript même si l'élément est un peu caché"""
    driver.execute_script("arguments[0].click();", element)

def recuperer_temsi_universal():
    print("--- 1. Démarrage Selenium (Mode Universel) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # --- LOGIN ---
        print("2. Login...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except:
            pass 
        
        # Attente d'être sur l'accueil
        try:
            wait.until(EC.url_contains("accueil"))
        except:
            print("   [INFO] Pas de redirection 'accueil' détectée, on continue...")

        # --- OUVERTURE MENU TEMSI ---
        print("3. Ouverture du menu 'TEMSI-WINTEM'...")
        try:
            # On cherche n'importe quel texte contenant TEMSI-WINTEM
            menu = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'TEMSI-WINTEM')]")))
            force_click(driver, menu)
            print("   Menu cliqué. Attente animation...")
            time.sleep(5) # Pause longue obligatoire pour le vieux site
        except Exception as e:
            print(f"[ERREUR] Menu principal introuvable : {e}")
            raise

        # --- RECHERCHE CIBLE 'FRANCE' ---
        print("4. Recherche de l'élément 'FRANCE'...")
        
        # Stratégie : On prend TOUS les éléments qui contiennent le mot "FRANCE"
        # On ignore la casse (minuscule/majuscule) grâce à translate()
        xpath_france = "//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'FRANCE')]"
        candidats = driver.find_elements(By.XPATH, xpath_france)
        
        cible_finale = None
        
        print(f"   {len(candidats)} éléments contenant 'FRANCE' trouvés.")
        
        for element in candidats:
            # On vérifie si l'élément est visible à l'écran
            if element.is_displayed():
                txt = element.text.strip()
                # On évite de cliquer sur le titre "Domaine : FRANCE" si ce n'est pas un lien
                # On privilégie les éléments qui sont des liens (a) ou qui sont dans le menu
                tag = element.tag_name
                print(f"   > Candidat visible : Tag={tag} | Texte='{txt}'")
                
                # Si c'est un lien ou un span cliquable, on prend !
                if tag == 'a' or tag == 'span' or tag == 'td':
                    cible_finale = element
                    break # On prend le premier trouvé
        
        if cible_finale:
            print(f"   [OK] Clic sur : {cible_finale.text}")
            force_click(driver, cible_finale)
            time.sleep(5) # Attente chargement page
        else:
            print("[ALERTE] Aucun élément 'FRANCE' visible trouvé. Dump du menu :")
            # Mouchard : On affiche tout ce qui est visible dans le menu pour debug
            menu_items = driver.find_elements(By.XPATH, "//div[contains(@style, 'block')]//a")
            for item in menu_items:
                print(f"   - Visible : {item.text}")
            raise Exception("Cible France introuvable")

        # --- RECUPERATION IMAGE ---
        print("5. Recherche de l'image carte...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                src = img.get_attribute("src")
                w = img.size['width']
                h = img.size['height']
                # On cherche une image assez grande qui contient "affiche_image" ou qui est générée dynamiquement
                if w * h > 50000:
                    print(f"   > Image détectée : {w}x{h} | {src[-30:]}")
                    if w * h > surface_max:
                        surface_max = w * h
                        url_finale = src
            except: pass

        if url_finale:
            print(f"   [VICTOIRE] URL Finale : {url_finale}")
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            # Transfert cookies
            for c in driver.get_cookies(): 
                session.cookies.set(c['name'], c['value'])
            
            resp = session.get(url_finale)
            if resp.status_code == 200:
                with open(NOM_FICHIER, 'wb') as f:
                    f.write(resp.content)
                print("[SUCCES TOTAL] Image enregistrée.")
            else:
                print(f"[ECHEC DOWNLOAD] Code {resp.status_code}")
        else:
            print("[ERREUR] Pas d'image trouvée sur la page finale.")
            raise Exception("Pas d'image")

    except Exception as e:
        print(f"[CRASH] {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_universal()
