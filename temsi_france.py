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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- CONFIGURATION ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "temsi_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"

# Fonction de secours pour voir ce que voit le robot en cas de crash
def debug_screenshot(driver, nom="erreur_page.png"):
    try:
        driver.save_screenshot(nom)
        print(f"[DEBUG] Capture d'écran de l'erreur sauvegardée : {nom}")
        print(f"[DEBUG] URL au moment du crash : {driver.current_url}")
    except:
        print("[DEBUG] Impossible de prendre le screenshot.")

def recuperer_temsi_navigation_complexe():
    print("--- 1. Démarrage Selenium (Mode Navigation Menu Complexe) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Ecran large pour bien afficher les menus latéraux
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15) # On se donne 15s max pour trouver les éléments

    try:
        # --- PHASE 1 : LOGIN (Protocole standard fiable) ---
        print("2. Login...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image']").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        
        # Verification qu'on est connecté (redirigé vers accueil)
        try:
            wait.until(EC.url_contains("accueil"))
            print("   [OK] Connecté sur la page d'accueil.")
        except TimeoutException:
            print("[ERREUR] Login échoué ou redirection trop longue.")
            raise

        # --- PHASE 2 : OUVERTURE DU MENU LATERAL ---
        print("3. Recherche du menu déroulant 'TEMSI-WINTEM'...")
        try:
            # On cherche un élément cliquable qui contient le texte exact donné par l'utilisateur
            # XPath cherche n'importe quel élément (*) contenant le texte
            menu_opener = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'TEMSI-WINTEM')]")))
            print("   Menu trouvé. Clic...")
            menu_opener.click()
            time.sleep(3) # On laisse le temps au menu de se dérouler
        except TimeoutException:
             print("[ERREUR] Impossible de trouver le bouton 'TEMSI-WINTEM' dans le menu de gauche.")
             raise

        # --- PHASE 3 : CLIC SUR LE LIEN 'FRANCE' ---
        print("4. Recherche du lien 'FRANCE' dans le menu déroulé...")
        try:
            # On cherche un lien (tag 'a') qui est VISIBLE et contient le texte 'FRANCE'
            lien_france = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(text(), 'FRANCE')]")))
            print(f"   Lien France trouvé (URL cible: {lien_france.get_attribute('href')}). Clic...")
            lien_france.click()
            # On attend que la nouvelle page se charge
            time.sleep(5) 
            print(f"   [OK] Nouvelle page atteinte : {driver.current_url}")
        except TimeoutException:
             print("[ERREUR] Le lien 'FRANCE' n'est pas apparu après avoir ouvert le menu.")
             raise

        # --- PHASE 4 : RECUPERATION DE LA PLUS GRANDE IMAGE (Méthode robuste) ---
        print("5. Analyse de la page pour trouver la carte (la plus grande image)...")
        images = driver.find_elements(By.TAG_NAME, "img")
        url_finale = None
        surface_max = 0
        
        for img in images:
            try:
                # On ne prend que les images affichées (width > 0)
                if img.size['width'] > 50 and img.size['height'] > 50:
                    surface = img.size['width'] * img.size['height']
                    src = img.get_attribute("src")
                    # Aeroweb utilise souvent ce script pour servir les cartes
                    if surface > surface_max and src and "affiche_image" in src:
                        surface_max = surface
                        url_finale = src
                        print(f"   > Candidat (Surface: {surface}): {src[-40:]}")
            except:
                continue
        
        if not url_finale:
            print("[ERREUR FATALE] Aucune grande image de type 'carte' trouvée sur cette page.")
            raise

        print(f"   [VICTOIRE] Image finale identifiée : {url_finale}")

        # --- PHASE 5 : TELECHARGEMENT AVEC SESSION ---
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        selenium_cookies = driver.get_cookies()
        for cookie in selenium_cookies:
            session.cookies.set(cookie['name'], cookie['value'])
            
        resp = session.get(url_finale)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(NOM_FICHIER, 'wb') as f:
                f.write(resp.content)
            print(f"[SUCCES TOTAL] TEMSI France sauvegardée ({len(resp.content)} octets).")
        else:
            print(f"[ECHEC DOWNLOAD] Status: {resp.status_code}, Taille: {len(resp.content)}")
            raise Exception("Echec téléchargement final")

    except Exception as e:
        print(f"\n[ARRET DU SCRIPT SUR ERREUR] : {e}")
        # C'est ici qu'on prend la photo si ça plante
        debug_screenshot(driver)
        exit(1) # On force le rouge pour le workflow
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_temsi_navigation_complexe()
