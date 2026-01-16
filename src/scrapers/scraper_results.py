import re
import logging
from ..core import config
from ..core import utils
from ..core.database import get_db_connection

logger = logging.getLogger(__name__)

def extraire_donnees_resultats(page):
    """Scrape les résultats historiques depuis Bet261 et les sauvegarde en DB normalisée."""
    print("Demarrage du scraper de resultats (version robuste)...")
    utils.fermer_popups(page)

    try:
        # Attente du chargement d'un titre de journée
        page.wait_for_selector("text=/Journée \\d+/", timeout=10000)
    except Exception as e:
        logger.error(f"Erreur : Aucun resultat trouve sur la page. {e}")
        print("Erreur : Aucun resultat trouve sur la page.")
        return

    # 1. Récupérer les journées déjà enregistrées pour éviter les doublons
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT journee FROM resultats")
            journees_existantes = {row[0] for row in cursor.fetchall()}
            print(f"INFO: Journées déjà en base : {sorted(list(journees_existantes))}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des journées existantes : {e}")
        journees_existantes = set()

    # 2. Récupérer tous les titres de journées
    titres_locators = page.locator("text=/Journée \\d+/").all()
    # 3. Récupérer tous les blocs de matchs
    match_containers = page.locator("div[class*='match']:has(.left-team)").all()
    
    print(f"📦 {len(titres_locators)} journees et {len(match_containers)} blocs de matchs trouves.")

    matchs_a_inserer = []
    
    # On fait correspondre chaque bloc de match à son titre de journée (indexé)
    for idx, container in enumerate(match_containers):
        try:
            if idx >= len(titres_locators):
                break
                
            journee_text = titres_locators[idx].inner_text()
            match_j = re.search(r"Journée\s+(\d+)", journee_text)
            if not match_j:
                continue
            
            journee_num = int(match_j.group(1))

            # --- MODIFICATION : Règle anti-doublon ---
            if journee_num in journees_existantes:
                # On log seulement la première fois pour éviter de spammer si plusieurs matchs
                # Mais ici idx est aligné sur les blocs de 'matches', qui contient souvent tous les matchs d'une journée?
                # Le code original semble dire 'titres_locators' (un par journée?) vs 'match_containers'.
                # Vérifions : "match_containers = page.locator("div[class*='match']...").all()"
                # Souvent les sites ont UN bloc par journée ou UN bloc par match.
                # Si c'est un bloc par match, 'idx >= len(titres_locators)' suggère que titres et containers sont alignés 1:1 ?
                # NON, le code original `if idx >= len(titres_locators): break` suggère que l'indexation est parallèle.
                # CELA SIGNIFIE QUE 'container' CONTIENT TOUS LES MATCHS D'UNE JOURNÉE.
                # Donc on peut skip tout le container.
                print(f"✅ Journée {journee_num} déjà existante. Ignorée.")
                continue
            # -----------------------------------------

            texte_bloc = container.inner_text().strip()
            
            # Parsing du bloc via la logique robuste : recherche du score X:X
            # On divise par ligne pour simuler la logique du code de test
            lignes = [l.strip() for l in texte_bloc.split('\n') if l.strip()]
            
            for i, ligne in enumerate(lignes):
                if re.match(r'^\d+:\d+$', ligne):
                    score_text = ligne
                    score_home, score_away = map(int, score_text.split(':'))
                    
                    # Recherche de l'équipe domicile (au-dessus du score)
                    found_home_name = None
                    for j in range(i-1, -1, -1):
                        potential_name = lignes[j]
                        
                        # 1. Vérification des alias
                        for alias, real_name in config.TEAM_ALIASES.items():
                            if alias in potential_name:
                                found_home_name = real_name
                                break
                        if found_home_name: break

                        # 2. Vérification des noms exacts
                        if any(eq in potential_name for eq in config.EQUIPES):
                            for eq in config.EQUIPES:
                                if eq in potential_name:
                                    found_home_name = eq
                                    break
                            if found_home_name: break
                    
                    # Recherche de l'équipe extérieur (en-dessous du score ou de MT:)
                    found_away_name = None
                    idx_away = i + 1
                    while idx_away < len(lignes):
                        potential_name = lignes[idx_away]
                        
                        # 1. Vérification des alias
                        for alias, real_name in config.TEAM_ALIASES.items():
                            if alias in potential_name:
                                found_away_name = real_name
                                break
                        if found_away_name: break
                        
                        # 2. Vérification des noms exacts
                        if any(eq in potential_name for eq in config.EQUIPES):
                            for eq in config.EQUIPES:
                                if eq in potential_name:
                                    found_away_name = eq
                                    break
                            if found_away_name: break
                        idx_away += 1
                        
                    if found_home_name and found_away_name:
                        matchs_a_inserer.append((journee_num, found_home_name, found_away_name, score_home, score_away))
                                
        except Exception as e:
            logger.warning(f"Erreur lors du parsing d'un match : {e}")
            continue

    # Insertion batch optimisée
    if matchs_a_inserer:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                matchs_ajoutes = 0
                
                for journee_num, found_home_name, found_away_name, score_home, score_away in matchs_a_inserer:
                    home_id = utils.get_equipe_id(found_home_name, conn)
                    away_id = utils.get_equipe_id(found_away_name, conn)
                    
                    if home_id and away_id:
                        cursor.execute('''
                        # Utilisation de UPSERT (On Conflict Update) pour mettre à jour les matchs qui étaient en attente (NULL)
                        cursor.execute('''
                            INSERT INTO resultats (journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(journee, equipe_dom_id, equipe_ext_id) 
                            DO UPDATE SET score_dom=excluded.score_dom, score_ext=excluded.score_ext
                        ''', (journee_num, home_id, away_id, score_home, score_away))
                        
                        if cursor.rowcount > 0:
                            matchs_ajoutes += 1
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion en DB : {e}", exc_info=True)
            print(f"❌ Erreur lors de l'insertion en DB : {e}")
            return
    
    print(f"Scraping resultats termine. {len(matchs_a_inserer)} matchs traites.")

if __name__ == "__main__":
    print("Ce script doit etre lance via main.py")
