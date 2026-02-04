import os
import time
import textwrap
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
IDENTIFIANT = os.environ["METEO_LOGIN"]
MOT_DE_PASSE = os.environ["METEO_PASS"]
NOM_FICHIER = "sigmet_france.png"
URL_LOGIN = "https://aviation.meteo.fr/login.php"

def generer_image_message(texte, niveau_alerte):
    """
    Génère une image contenant le texte.
    niveau_alerte : 'RAS' (Vert) ou 'ALERTE' (Rouge)
    """
    # Dimensions de l'image (Bandeau large)
    W, H = 800, 200
    
    # Couleurs
    if niveau_alerte == 'RAS':
        bg_color = (200, 255, 200) # Vert clair
        text_color = (0, 100, 0)   # Vert fonce
    else:
        bg_color = (255, 200, 200) # Rouge clair
        text_color = (150, 0, 0)   # Rouge fonce

    img = Image.new('RGB', (W, H), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Tentative de chargement d'une police (sinon defaut)
    try:
        # On essaie une police standard Linux
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Découpage du texte pour qu'il rentre dans l'image (wrap)
    lignes = textwrap.wrap(texte, width=60) # Coupe tous les 60 caractères
    
    # Centrage vertical
    y_text = 20
    for ligne in lignes:
        # Calcul de la largeur de la ligne pour centrer horizontalement
        # (Méthode simple compatible vieilles versions Pillow)
        draw.text((20, y_text), ligne, font=font, fill=text_color)
        y_text += 30 # Saut de ligne

    img.save(NOM_FICHIER)
    print(f"   [IMAGE] Générée : {NOM_FICHIER} (Mode {niveau_alerte})")

def recuperer_sigmet():
    print("--- SEQUENCE SIGMET ---")
    
    # Setup Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. Login
        print("> Connexion...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except: pass
        
        time.sleep(5)

        # 2. Lecture du SIGMET (Page Accueil)
        print("> Analyse texte page d'accueil...")
        
        # On cherche le texte qui contient "SIGMET" dans la classe "texte3"
        try:
            element = driver.find_element(By.XPATH, "//*[contains(text(),'SIGMET')]")
            texte_brut = element.text.strip()
            print(f"   [LU] : {texte_brut}")
            
            # 3. Logique de décision
            if "Pas de SIGMET" in texte_brut or "Aucun SIGMET" in texte_brut:
                generer_image_message(texte_brut, "RAS")
            else:
                # Si le texte est différent de "Pas de SIGMET", c'est qu'il y en a un !
                generer_image_message(f"ATTENTION : {texte_brut}", "ALERTE")
                
        except Exception as e:
            print(f"[INFO] Balise SIGMET non trouvée ({e}). Génération image neutre.")
            generer_image_message("Information SIGMET indisponible (Erreur Robot)", "ALERTE")

    except Exception as e:
        print(f"[CRASH] {e}")
        generer_image_message("ECHEC CONNEXION AEROWEB", "ALERTE")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_sigmet()
