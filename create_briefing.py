import os
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from docx.enum.table import WD_ALIGN_VERTICAL

# --- CONFIGURATION ---
NOM_FICHIER_SORTIE = "Dossier_Vol_Complet.docx"

# Images à insérer
IMAGES_METEO = [
    ("SITUATION GENERALE (WAFC)", "fronts_wafc.png"),
    ("TEMSI FRANCE", "temsi_france.png"),
    ("WINTEM (Vents/Temp)", "wintem_france.png"),
    ("SIGMET (Sécurité)", "sigmet_france.png")
]

# --- FONCTIONS DE STYLE (Pour imiter votre design) ---
def set_cell_shading(cell, color_hex):
    """Met un fond gris ou couleur dans une case"""
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def style_header_cell(cell, text):
    """Style les titres de tableaux (Gris, Gras, Centré)"""
    set_cell_shading(cell, "D9D9D9") # Le Gris de votre document
    p = cell.paragraphs[0]
    p.text = text
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if p.runs:
        p.runs[0].font.bold = True
        p.runs[0].font.size = Pt(10)
        p.runs[0].font.name = 'Arial'

def add_section_header(doc, title):
    """Crée les bandeaux de section (ex: 2. DEPARTURE)"""
    p = doc.add_paragraph()
    p.space_before = Pt(12)
    run = p.add_run(title)
    run.bold = True
    run.font.size = Pt(12)
    run.font.name = 'Arial'
    run.font.color.rgb = RGBColor(0, 0, 0)
    # Ligne de séparation fine
    p_border = doc.add_paragraph()
    p_border.paragraph_format.line_spacing = Pt(0)
    p_border.paragraph_format.space_after = Pt(6)
    runner = p_border.add_run("_" * 95)
    runner.font.size = Pt(6)
    runner.font.color.rgb = RGBColor(160, 160, 160)

def create_document():
    doc = Document()
    
    # 1. MISE EN PAGE (Marges étroites comme votre doc)
    section = doc.sections[0]
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)
    
    # Police par défaut : Arial
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(9)

    # --- ENTETE (Votre style tableau) ---
    t_head = doc.add_table(rows=2, cols=3)
    t_head.autofit = False
    t_head.columns[0].width = Cm(8)
    t_head.columns[1].width = Cm(6)
    t_head.columns[2].width = Cm(5)

    # Titre
    c1 = t_head.cell(0, 0)
    r1 = c1.paragraphs[0].add_run("FLIGHT BRIEFING")
    r1.bold = True
    r1.font.size = Pt(18)
    
    # Cases à cocher (NCO / CAT)
    c2 = t_head.cell(0, 1)
    p2 = c2.paragraphs[0]
    p2.add_run("☐ BRIEFING NCO (VFR)\n")
    p2.add_run("☐ BRIEFING CAT (IFR)").bold = True
    
    # Date
    c3 = t_head.cell(0, 2)
    c3.paragraphs[0].add_run("DATE : ____________")
    
    # Ligne 2 : Equipage
    c_crew = t_head.cell(1, 0)
    t_head.cell(1, 0).merge(t_head.cell(1, 2)) # On fusionne toute la ligne
    p_crew = t_head.cell(1, 0).paragraphs[0]
    p_crew.add_run("AVION : ________   CDB : ____________________   INSTR : ____________________")
    p_crew.paragraph_format.space_before = Pt(6)
    
    doc.add_paragraph("")

    # --- 1. DOCS & ADMIN ---
    add_section_header(doc, "1. FLIGHT DOCUMENTS")
    t_docs = doc.add_table(rows=1, cols=4)
    t_docs.style = 'Table Grid'
    
    # Headers verticaux grisés
    c_ac = t_docs.cell(0, 0)
    c_ac.text = "AIRCRAFT"
    set_cell_shading(c_ac, "E7E6E6")
    c_ac.paragraphs[0].runs[0].font.bold = True
    
    # Liste Checkbox
    c_list1 = t_docs.cell(0, 1)
    c_list1.text = "☐ Insurance\n☐ Registration\n☐ Noise Cert.\n☐ CDN / CEN / ARC\n☐ Radio Lic. (LSA)\n☐ Tech Log (OK)\n☐ M&B Sheet"

    c_safe = t_docs.cell(0, 2)
    c_safe.text = "CREW & SAFETY"
    set_cell_shading(c_safe, "E7E6E6")
    c_safe.paragraphs[0].runs[0].font.bold = True
    
    c_list2 = t_docs.cell(0, 3)
    c_list2.text = "☐ Licences & Medical\n☐ Maps / Charts\n☐ Flight Plan\n☐ Gilet / Life Vest\n☐ Trousse Secours\n☐ Extincteur"

    doc.add_paragraph("")

    # --- 2. DEPARTURE (Chronologie Instructeur) ---
    add_section_header(doc, "2. DEPARTURE")
    t_dep = doc.add_table(rows=2, cols=2)
    t_dep.style = 'Table Grid'
    
    t_dep.cell(0,0).text = "TERRAIN DÉPART : ____________"
    t_dep.cell(0,1).text = "DÉGAGEMENT (ALTN) : ____________"
    
    # Cases vides pour NOTAM et METEO
    t_dep.cell(1,0).text = "NOTAM DÉPART & PISTE :\n\n\n\n"
    t_dep.cell(1,1).text = "MÉTÉO DÉPART (METAR/TAF) :\n\n\n\n"
    
    doc.add_paragraph("")

    # --- 3. EN ROUTE (Avec le tableau Fuel demandé) ---
    add_section_header(doc, "3. EN ROUTE")
    
    # NOTAM Route
    t_route = doc.add_table(rows=1, cols=1)
    t_route.style = 'Table Grid'
    t_route.cell(0,0).text = "NOTAM EN ROUTE (Zones, AZBA, NAVAIDS...) & PARTICULARITÉS :\n\n\n"
    
    doc.add_paragraph("")
    
    # TABLEAU LOG DE NAV (Demande Instructeur "Partie Route Incomplète")
    p_log = doc.add_paragraph()
    p_log.add_run("SUIVI NAVIGATION & CARBURANT (NAV LOG)").bold = True
    
    t_log = doc.add_table(rows=6, cols=5)
    t_log.style = 'Table Grid'
    headers = ["POINT", "ROUTE", "ALT/FL", "ETO", "FUEL EST."]
    for i, h in enumerate(headers):
        style_header_cell(t_log.cell(0, i), h)
        
    # Lignes vides
    for r in range(1, 6):
        for c in range(5):
            t_log.cell(r, c).text = ""

    doc.add_paragraph("")

    # --- 4. ARRIVAL ---
    add_section_header(doc, "4. DESTINATION")
    t_arr = doc.add_table(rows=2, cols=2)
    t_arr.style = 'Table Grid'
    
    t_arr.cell(0,0).text = "TERRAIN DESTINATION : ____________"
    t_arr.cell(0,1).text = "DÉGAGEMENT (ALTN) : ____________"
    t_arr.cell(1,0).text = "NOTAM ARRIVÉE & APPROCHE :\n\n\n\n"
    t_arr.cell(1,1).text = "MÉTÉO ARRIVÉE (METAR/TAF) :\n\n\n\n"
    
    doc.add_page_break()

    # --- 5. MÉTÉO GLOBALE (ROBOT) ---
    add_section_header(doc, "5. SITUATION MÉTÉO (CARTES ROBOT)")
    
    # Tableau 2x2
    t_img = doc.add_table(rows=2, cols=2)
    t_img.autofit = True
    
    for i, (titre, f_img) in enumerate(IMAGES_METEO):
        row, col = i // 2, i % 2
        cell = t_img.cell(row, col)
        
        # Titre
        p = cell.paragraphs[0]
        p.add_run(titre).bold = True
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Image
        if os.path.exists(f_img):
            p_img = cell.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p_img.add_run()
            try:
                run.add_picture(f_img, width=Cm(8.0))
            except:
                p_img.add_run("[Erreur Image]")
        else:
            cell.add_paragraph("\n[Image absente - Lancer le Robot]").alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")

    # --- 6. MINIMA ---
    add_section_header(doc, "6. PLANNING MINIMA")
    t_min = doc.add_table(rows=3, cols=5)
    t_min.style = 'Table Grid'
    
    # En-têtes
    cols_min = ["TERRAIN", "TYPE APPROCHE", "DA / MDA", "VISIBILITÉ", "PLAFOND"]
    for i, h in enumerate(cols_min):
        style_header_cell(t_min.cell(0, i), h)
        
    t_min.cell(1, 0).text = "DESTINATION"
    set_cell_shading(t_min.cell(1, 0), "F2F2F2")
    t_min.cell(2, 0).text = "ALTERNATE"
    set_cell_shading(t_min.cell(2, 0), "F2F2F2")
    
    doc.add_paragraph("")

    # --- 7. MASSE & CENTRAGE (AVANT FUEL - Demande Instructeur) ---
    add_section_header(doc, "7. MASSE & CENTRAGE (M&B)")
    
    t_mb = doc.add_table(rows=1, cols=4)
    t_mb.style = 'Table Grid'
    
    t_mb.cell(0,0).text = "MASSE À VIDE :\n________ kg"
    t_mb.cell(0,1).text = "CHARGE UTILE :\n________ kg"
    t_mb.cell(0,2).text = "MASSE DÉCOLLAGE :\n________ kg (Max: ____)"
    t_mb.cell(0,3).text = "CENTRAGE :\n☐ OK  ☐ NON"
    
    doc.add_paragraph("")

    # --- 8. FUEL ---
    add_section_header(doc, "8. CARBURANT")
    t_fuel = doc.add_table(rows=7, cols=3)
    t_fuel.style = 'Table Grid'
    
    style_header_cell(t_fuel.cell(0, 0), "ITEM")
    style_header_cell(t_fuel.cell(0, 1), "TEMPS")
    style_header_cell(t_fuel.cell(0, 2), "QUANTITÉ (L)")
    
    items_fuel = ["TAXI", "TRIP", "CONTINGENCY (5%)", "ALTERNATE", "FINAL RESERVE (45min)", "EXTRA"]
    for i, item in enumerate(items_fuel):
        t_fuel.cell(i+1, 0).text = item
        # Surlignage vert pâle pour la réserve finale (Sécurité)
        if "FINAL" in item:
            set_cell_shading(t_fuel.cell(i+1, 0), "E2EFDA")
            
    doc.add_paragraph("")

    # --- 9. PERF & TEM ---
    add_section_header(doc, "9. PERFORMANCES & DECISION")
    
    t_perf = doc.add_table(rows=2, cols=2)
    t_perf.style = 'Table Grid'
    
    t_perf.cell(0,0).text = "DÉCOLLAGE :\nDist. Roul _____ m / 50ft _____ m\nPiste Dispo _____ m"
    t_perf.cell(0,1).text = "ATTERRISSAGE :\nDist. Roul _____ m / 50ft _____ m\nPiste Dispo _____ m"
    
    # Case TEM fusionnée
    t_perf.cell(1,0).merge(t_perf.cell(1,1))
    c_tem = t_perf.cell(1,0)
    set_cell_shading(c_tem, "FFF2CC") # Jaune Attention
    p_tem = c_tem.paragraphs[0]
    p_tem.add_run("THREATS (Menaces) : Météo / Terrain / Trafic / Etat Avion\n").italic = True
    p_tem.add_run("ERRORS (Erreurs) : Oublis / Procédures / Pilotage\n\n").italic = True
    r_dec = p_tem.add_run("DECISION :   ☐ GO      ☐ DELAY      ☐ NO-GO")
    r_dec.bold = True
    r_dec.font.size = Pt(11)
    p_tem.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Sauvegarde
    doc.save(NOM_FICHIER_SORTIE)
    print(f"✅ DOCUMENT CRÉÉ : {NOM_FICHIER_SORTIE}")

if __name__ == "__main__":
    create_document()
