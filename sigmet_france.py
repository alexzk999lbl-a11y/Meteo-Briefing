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

def generer_image(texte, is_alerte):
    """
    Génère l'image avec le texte EXACT trouvé sur le site.
    """
    # Nettoyage
    texte_propre = " ".join(texte.split())
    
    if is_alerte:
        # ROUGE (Danger/SIGMET Actif)
        bg_color = (255, 200, 200) # Rouge clair
        text_color = (150, 0, 0)   # Rouge foncé
        titre = "⚠️ ALERTE SIGMET :"
    else:
        # VERT (RAS)
        bg_color = (200, 255, 200) # Vert clair
        text_color = (0, 100, 0)   # Vert foncé
        titre = "SITUATION NORMALE :"

    # Dimensions
    W, H = 800, 250
    img = Image.new('RGB', (W, H), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Police
    try:
        font_main = ImageFont.truetype("DejaVuSans-Bold.ttf", 18)
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except:
        font_main = ImageFont.load_default()
        font_title = ImageFont.load_default()

    # Titre
    draw.text((20, 20), titre, font=font_title, fill=text_color)
    
    # Le texte exact du site
    lignes = textwrap.wrap(texte_propre, width=65)
    y = 60
    for ligne in lignes:
        draw.text((20, y), ligne, font=font_main, fill=text_color)
        y += 25

    img.save(NOM_FICHIER)
    print(f"   [IMAGE] Mode {'ALERTE' if is_alerte else 'RAS'} - Texte : {texte_propre[:30]}...")

def recuperer_sigmet_strict():
    print("--- SCAN SIGMET (Logique Stricte) ---")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 1. LOGIN
        driver.get(URL_LOGIN)
        driver.find_element(By.NAME, "login").send_keys(IDENTIFIANT)
        driver.find_element(By.NAME, "password").send_keys(MOT_DE_PASSE)
        try:
            driver.find_element(By.XPATH, "//input[@type='image'] | //input[@type='submit']").click()
        except: pass
        
        time.sleep(5)

        # 2. LECTURE
        print("> Recherche du message...")
        try:
            # On cherche tout élément contenant "SIGMET" qui N'EST PAS un lien (pour éviter le menu)
            xpath = "//*[contains(text(), 'SIGMET')][not(self::a)]"
            elements = driver.find_elements(By.XPATH, xpath)
            
            texte_trouve = None
            
            for elem in elements:
                # On filtre les éléments invisibles ou trop courts
                if elem.is_displayed() and len(elem.text) > 5:
                    # On ignore le titre du menu s'il est capté par erreur
                    if "Type de cartes" in elem.text: continue
                    
                    texte_trouve = elem.text
                    break # On prend le premier trouvé
            
            if texte_trouve:
                print(f"   [LU] : {texte_trouve}")
                
                # --- REGLE STRICTE PILOTE ---
                # Si "Pas de" est présent -> VERT
                # Sinon -> ROUGE
                if "Pas de" in texte_trouve:
                    generer_image(texte_trouve, is_alerte=False)
                else:
                    generer_image(texte_trouve, is_alerte=True)
            else:
                print("[INFO] Aucun message texte trouvé. Génération image erreur.")
                generer_image("Information SIGMET illisible (Structure page changée)", True)

        except Exception as e:
            print(f"[ERREUR] {e}")
            exit(1)

    except Exception as e:
        print(f"[CRASH] {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_sigmet_strict()
