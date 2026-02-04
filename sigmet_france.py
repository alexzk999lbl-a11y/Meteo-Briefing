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

def generer_image_brute(texte_brut):
    """
    Crée une image avec le texte EXACT trouvé sur le site.
    Gestion intelligente de la couleur de fond.
    """
    # Nettoyage du texte (on vire les sauts de ligne multiples pour avoir une phrase propre)
    texte_propre = " ".join(texte_brut.split())
    
    # LOGIQUE DE COULEUR STRICTE
    # 1. Cas VERT : On est sûr qu'il n'y a rien
    if "Pas de SIGMET" in texte_propre:
        bg_color = (200, 255, 200) # Vert 
        text_color = (0, 100, 0)
        status = "RAS"
    # 2. Cas ROUGE : Il y a un SIGMET actif (et pas la phrase 'Pas de...')
    elif "SIGMET" in texte_propre and "Pas de" not in texte_propre:
        bg_color = (255, 200, 200) # Rouge
        text_color = (150, 0, 0)
        status = "ALERTE"
    # 3. Cas ORANGE : Texte inconnu ou informatif (ex: Maintenance, Gamet seul...)
    else:
        bg_color = (255, 220, 150) # Orange
        text_color = (100, 50, 0)
        status = "INFO"

    # Création Image
    W, H = 800, 200
    img = Image.new('RGB', (W, H), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Police
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
    except:
        font = ImageFont.load_default()

    # Affichage du texte brut (Wrap pour que ça rentre)
    lignes = textwrap.wrap(texte_propre, width=70)
    
    y_text = 20
    # Titre indicatif
    draw.text((20, y_text), f"ETAT SIGMET ({status}) :", font=font, fill=text_color)
    y_text += 30
    
    # Le vrai texte du site
    for ligne in lignes:
        draw.text((20, y_text), ligne, font=font, fill=text_color)
        y_text += 25

    img.save(NOM_FICHIER)
    print(f"   [IMAGE] Texte : '{texte_propre}' | Couleur : {status}")

def recuperer_sigmet_reel():
    print("--- LECTURE SIGMET EXACTE ---")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Login
        print("> Connexion...")
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except: pass
        
        time.sleep(5)

        # Extraction
        print("> Lecture du SPAN...")
        try:
            # On vise la classe texte3 qui contient le mot SIGMET (votre structure HTML)
            # On prend le texte entier
            element = driver.find_element(By.XPATH, "//span[@class='texte3'][contains(text(),'SIGMET')]")
            texte_site = element.text
            
            if texte_site:
                generer_image_brute(texte_site)
            else:
                generer_image_brute("Erreur : Balise trouvée mais texte vide.")
                
        except Exception as e:
            print(f"[INFO] Balise spécifique introuvable : {e}")
            generer_image_brute("Information SIGMET non trouvée sur l'accueil.")

    except Exception as e:
        print(f"[CRASH] {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_sigmet_reel()
