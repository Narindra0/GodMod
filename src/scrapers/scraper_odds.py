import re
import logging
from ..core import config
from ..core import utils
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)

def extraire_donnees_cotes(page):
    """Scrape les cotes des matchs à venir depuis Bet261 et les sauvegarde en DB normalisée."""
    print("Demarrage du scraper de cotes (version robuste)...")
    utils.fermer_popups(page)

    try:
        # Attente du chargement des blocs de matchs
        page.wait_for_selector("div[class*='match']", timeout=10000)
    except Exception as e:
        logger.error(f"Erreur : Les blocs de matchs n'ont pas ete trouves. {e}")
        print("Erreur : Les blocs de matchs n'ont pas ete trouves.")
        return

    # 2. Détection de la Journée
    journee = 0
    try:
        journee_text = page.locator("text=/Journée \\d+/").first.inner_text()
        match_j = re.search(r"Journée\s+(\d+)", journee_text)
        if match_j:
            journee = int(match_j.group(1))
            print(f"📅 Journée détectée : {journee}")
    except Exception as e:
        # Fallback : on récupère la dernière journée en DB + 1 si non trouvée
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(journee) FROM resultats")
                res = cursor.fetchone()
                journee = (res[0] if res[0] else 0) + 1
                print(f"Journee non detectee, utilisation de J{journee}")
        except Exception as db_e:
            logger.error(f"Erreur lors de la récupération de la journée : {db_e}")
            journee = 1

    # 3. Extraction par blocs de texte (approche robuste)
    match_elements = page.locator("div[class*='match']").all()
    print(f"Analyse de {len(match_elements)} blocs de matchs potentiels.")

    cotes_a_inserer = []
    seen_text = set()

    for el in match_elements:
        try:
            text = el.inner_text().strip()
            if not text or text in seen_text: 
                continue
            
            # Extraction des cotes via regex (format X,XX)
            cotes_match = re.findall(r"(\d+,\d{2})", text)
            if len(cotes_match) >= 3:
                # On prend les 3 dernières cotes trouvées dans le bloc pour 1 X 2
                c1 = float(cotes_match[-3].replace(',', '.'))
                cx = float(cotes_match[-2].replace(',', '.'))
                c2 = float(cotes_match[-1].replace(',', '.'))
                
                # Identification des équipes (avec support des alias)
                team_indices = []
                
                # 1. Alias
                for alias, real_name in config.TEAM_ALIASES.items():
                    idx = text.find(alias)
                    if idx != -1:
                        team_indices.append((idx, real_name))
                
                # 2. Noms officiels
                for eq_nom in config.EQUIPES:
                    idx = text.find(eq_nom)
                    if idx != -1:
                        if not any(t[1] == eq_nom for t in team_indices):
                            team_indices.append((idx, eq_nom))
                
                if len(team_indices) >= 2:
                    team_indices.sort(key=lambda x: x[0])
                    found_home_name = team_indices[0][1]
                    found_away_name = team_indices[1][1]
                    
                    cotes_a_inserer.append((journee, found_home_name, found_away_name, c1, cx, c2))
                    seen_text.add(text)
                else:
                    logger.debug(f"Bloc ignore (Equipes insuffisantes : {len(team_indices)}) : {text[:50]}...")
            else:
                logger.debug(f"Bloc ignore (Cotes insuffisantes : {len(cotes_match)}) : {text[:50]}...")

        except Exception as e:
            logger.warning(f"Erreur lors du parsing d'un match : {e}")
            continue

    # Insertion batch optimisée
    if cotes_a_inserer:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Vidage des cotes existantes
                cursor.execute("DELETE FROM cotes")
                
                cotes_ajoutees = 0
                for journee, found_home_name, found_away_name, c1, cx, c2 in cotes_a_inserer:
                    home_id = utils.get_equipe_id(found_home_name, conn)
                    away_id = utils.get_equipe_id(found_away_name, conn)
                    
                    if home_id and away_id:
                        # 1. Insertion dans la table COTES (Comportement actuel)
                        cursor.execute('''
                            INSERT INTO cotes (journee, equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (journee, home_id, away_id, c1, cx, c2))
                        cotes_ajoutees += 1
                        
                        # 2. Insertion dans la table RESULTATS (Nouveau : Matchs à venir = NULL)
                        # On utilise INSERT OR IGNORE pour ne pas écraser si le match existe déjà (avec ou sans score)
                        cursor.execute('''
                            INSERT OR IGNORE INTO resultats (journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext)
                            VALUES (?, ?, ?, NULL, NULL)
                        ''', (journee, home_id, away_id))
                    else:
                        logger.warning(f"Echec ID pour : {found_home_name} ({home_id}) ou {found_away_name} ({away_id})")
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion en DB : {e}", exc_info=True)
            print(f"❌ Erreur lors de l'insertion en DB : {e}")
            return

    print(f"Cotes mises a jour. {len(cotes_a_inserer)} matchs traites.")

if __name__ == "__main__":
    print("Ce script doit etre lance via main.py")
