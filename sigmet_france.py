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

def generer_image(texte, type_message):
    """
    type_message : 'ALERTE' (Rouge) ou 'RAS' (Vert)
    """
    # Nettoyage du texte (remplace les <br> par des espaces si Selenium ne l'a pas fait)
    texte_propre = " ".join(texte.split())
    
    if type_message == 'ALERTE':
        bg_color = (255, 200, 200) # Rouge clair
        text_color = (150, 0, 0)   # Rouge foncé
        titre = "⚠️ ALERTE SIGMET (LFOT/LFFF) :"
        hauteur = 300 # Plus haut car le SIGMET peut être long
    else:
        bg_color = (200, 255, 200) # Vert clair
        text_color = (0, 100, 0)   # Vert foncé
        titre = "SITUATION NORMALE :"
        hauteur = 200

    # Création Image
    img = Image.new('RGB', (800, hauteur), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Police
    try:
        font_titre = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_txt = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except:
        font_titre = ImageFont.load_default()
        font_txt = ImageFont.load_default()

    # Titre
    draw.text((20, 20), titre, font=font_titre, fill=text_color)
    
    # Corps du message
    lignes = textwrap.wrap(texte_propre, width=75)
    y = 60
    for ligne in lignes:
        draw.text((20, y), ligne, font=font_txt, fill=text_color)
        y += 20

    img.save(NOM_FICHIER)
    print(f"   [IMAGE] Générée en mode {type_message}")

def recuperer_sigmet_final():
    print("--- SCAN SIGMET (Basé sur HTML LFBB/LFFF) ---")
    
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

        # 2. ANALYSE PRIORITAIRE : Y a-t-il une ALERTE ROUGE (texte1) ?
        # Ton exemple : <span class="texte1" style="color:red;">LFBB SIGMET...</span>
        try:
            # On cherche spécifiquement la classe d'alerte rouge
            alerte_rouge = driver.find_element(By.XPATH, "//span[@class='texte1' and contains(@style, 'red')]")
            if alerte_rouge.is_displayed():
                texte = alerte_rouge.text
                print(f"   [DANGER] SIGMET Détecté : {texte[:30]}...")
                generer_image(texte, 'ALERTE')
                return # On a trouvé le pire, on s'arrête là.
        except:
            pass # Pas d'alerte rouge explicite trouvée, on continue.

        # 3. ANALYSE SECONDAIRE : Y a-t-il le message "Pas de SIGMET" ?
        # Ton exemple précédent : <span class="texte3">Pas de SIGMET...</span>
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'SIGMET')]")
            trouve = False
            for elem in elements:
                # On ignore le menu
                if "Type de cartes" in elem.text: continue
                if elem.tag_name == 'a': continue
                
                txt = elem.text
                if "Pas de" in txt:
                    print(f"   [RAS] Message trouvé : {txt}")
                    generer_image(txt, 'RAS')
                    trouve = True
                    break
            
            if not trouve:
                # Si on n'a ni rouge, ni vert "Pas de", mais qu'on a trouvé un texte avec SIGMET...
                # Par sécurité, on considère que c'est une info importante.
                print("   [INFO] Texte ambigu trouvé, affichage par sécurité.")
                # On essaie de récupérer le premier texte SIGMET visible qui n'est pas le menu
                for elem in elements:
                    if "Type de cartes" not in elem.text and elem.tag_name != 'a' and len(elem.text) > 10:
                        generer_image(elem.text, 'ALERTE') # Dans le doute, Rouge
                        trouve = True
                        break
                
                if not trouve:
                    generer_image("Aucune info SIGMET trouvée sur la page d'accueil", 'ALERTE')

        except Exception as e:
            print(f"[ERREUR] {e}")
            exit(1)

    except Exception as e:
        print(f"[CRASH] {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    recuperer_sigmet_final()
