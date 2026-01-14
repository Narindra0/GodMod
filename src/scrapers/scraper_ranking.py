import re
import logging
from ..core import config
from ..core import utils
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)

def extraire_donnees_classement(page):
    """Scrape le classement actuel depuis Bet261 et le sauvegarde en DB normalisée."""
    print("Demarrage du scraper de classement...")
    utils.fermer_popups(page)

    try:
        page.wait_for_selector(config.SELECTORS["ranking_row"], timeout=10000)
    except Exception as e:
        logger.error(f"Erreur : Le tableau de classement n'a pas ete trouve. {e}")
        print("Erreur : Le tableau de classement n'a pas ete trouve.")
        return

    rows = page.query_selector_all(config.SELECTORS["ranking_row"])
    print(f"Classement : {len(rows)} equipes trouves.")

    # Détection de la journée actuelle
    journee_actuelle = utils.get_journee_from_page(page)
    if journee_actuelle == 0:
        # Fallback : récupérer la dernière journée depuis la DB
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(journee) FROM resultats")
                res = cursor.fetchone()
                journee_actuelle = res[0] if res[0] else 0
        except Exception as e:
            logger.warning(f"Impossible de récupérer la journée depuis la DB : {e}")
            journee_actuelle = 0

    # Collecte des données avant insertion batch
    classement_data = []
    
    for idx, row in enumerate(rows, start=1):
        try:
            team_container = row.query_selector(config.SELECTORS["ranking_team"])
            if not team_container:
                continue
                
            full_text = team_container.inner_text().strip()
            team_name = re.sub(r"^\d+\s*", "", full_text).strip()
            
            # Normalisation via alias
            if team_name in config.TEAM_ALIASES:
                team_name = config.TEAM_ALIASES[team_name]
            
            points_text = utils.extraire_texte_si_present(row, config.SELECTORS["ranking_points"])
            points = int(points_text) if points_text.isdigit() else 0
            
            form_icons = row.query_selector_all(config.SELECTORS["ranking_form"])
            forme = ""
            for icon in form_icons:
                src = icon.get_attribute("src") or ""
                if "victoire" in src or "win" in src.lower():
                    forme += "V"
                elif "nul" in src or "draw" in src.lower():
                    forme += "N"
                elif "defaite" in src or "loss" in src.lower():
                    forme += "D"
            
            # Position: index de la ligne dans le tableau (1..20)
            # Important pour Zeus (différentiel de classement)
            position = idx
            classement_data.append((team_name, points, forme, position))
        except Exception as e:
            logger.warning(f"Erreur lors du parsing d'une équipe : {e}")
            continue

    # Insertion batch optimisée
    if classement_data:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Nettoyage avant mise à jour
                cursor.execute("DELETE FROM classement")
                
                entrees_mises_a_jour = 0
                for team_name, points, forme, position in classement_data:
                    team_id = utils.get_equipe_id(team_name, conn)
                    if not team_id:
                        logger.warning(f"Équipe non trouvée : {team_name}")
                        continue
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO classement (equipe_id, points, forme, journee, position)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (team_id, points, forme, journee_actuelle, position))
                    
                    entrees_mises_a_jour += 1
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion en DB : {e}", exc_info=True)
            print(f"❌ Erreur lors de l'insertion en DB : {e}")
            return

    print(f"Classement mis a jour. {len(classement_data)} equipes traitees.")

if __name__ == "__main__":
    print("Ce script doit etre lance via main.py")
