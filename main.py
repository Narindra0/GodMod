from src.core import config
from src.scrapers import scraper_results
from src.scrapers import scraper_ranking
from src.scrapers import scraper_odds
from src.analysis import intelligence
from src.core import database
from src.core import utils
from src.core import archive
from src.core.database import get_db_connection
import time
import logging
import re
from playwright.sync_api import sync_playwright

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Variable globale pour tracker l'état précédent de la sélection améliorée
_last_selection_state = None

def determiner_prochaine_journee():
    """Détermine le numéro de la prochaine journée à prédire via les résultats."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(journee) FROM resultats")
            derniere_journee = cursor.fetchone()[0] or 0
            return derniere_journee + 1
    except Exception as e:
        logger.error(f"Erreur lors de la détermination de la prochaine journée : {e}", exc_info=True)
        return 1

def scraping_initial(page_results, page_ranking, force_same_session=False):
    """Effectue un scraping initial au démarrage pour constituer la base de données."""
    print("\n" + "="*50)
    print("🚀 SCRAPING INITIAL")
    print("="*50)
    
    if force_same_session:
        print("ℹ️ Mode 'Même Session' forcé par l'utilisateur. Détection de changement de session DÉSACTIVÉE.")
    
    try:
        print("🔎 Analyse préventive de la session...")
        # On attend un peu que le contenu soit là (le scraper fera un wait plus strict ensuite)
        try:
            page_results.wait_for_selector("text=/Journée \\d+/", timeout=5000)
        except:
            pass # Si pas trouvé, le scraper gérera ou la page est vide

        # On récupère les numéros de journées affichés
        headers = page_results.locator("text=/Journée \\d+/").all_inner_texts()
        days_on_page = []
        for h in headers:
            m = re.search(r"Journée\s+(\d+)", h)
            if m:
                days_on_page.append(int(m.group(1)))
        
        if days_on_page:
            # On prend la plus GRANDE journée trouvée pour éviter les faux resets avec des anciennes journées
            # Ex: Si on a J12, J13, J14, J15 et qu'on est à J14, prendre J12 causerait un reset.
            # On prend la plus GRANDE journée trouvée pour éviter les faux resets avec des anciennes journées
            max_day = max(days_on_page)
            
            # On ne vérifie le changement de session QUE si l'utilisateur n'a pas forcé "Même Session"
            if not force_same_session and archive.detecter_nouvelle_session(max_day):
                print(f"🔄 Détection changement de session via J{max_day} sur la page résultats.")
                print("\n" + "="*50)
                print("🗂️ NOUVELLE SESSION DÉTECTÉE AU DÉMARRAGE !")
                print("="*50)
                fichier = archive.archiver_session()
                
                if fichier:
                    print(f"✅ Session précédente archivée : {fichier}")
                    archive.reinitialiser_tables_session()
                else:
                    print("❌ ÉCHEC Archivage. Reset annulé par sécurité.")
                print("="*50 + "\n")
    except Exception as e:
        logger.warning(f"⚠️ Warning: Echec détection session pré-scraping (non bloquant): {e}")
    # -------------------------------------------------------------

    print("Récupération des données historiques...")
    
    scraper_results.extraire_donnees_resultats(page_results)
    scraper_ranking.extraire_donnees_classement(page_ranking)
    
    print("✅ Scraping initial terminé. Base de données prête.")
    print("="*50 + "\n")

def executer_cycle(p, browser, page_matches, page_results, page_ranking):
    """Exécute un cycle complet avec synchronisation séquentielle J+1."""
    print("\n--- Nouveau Cycle d'Analyse ---")
    
    # 1. Attente du moment valide (Timer, LIVE 5s, et Séquence J-1)
    # utils.wait_for_valid_cycle gère maintenant la vérification de la présence de J-1
    if not utils.wait_for_valid_cycle(page_matches, page_results, page_ranking):
        return False

    # 1.5 Détection de nouvelle session avant scraping
    journee_site = utils.get_journee_from_page(page_matches)
    if archive.detecter_nouvelle_session(journee_site):
        print("\n" + "="*50)
        print("🗂️ NOUVELLE SESSION DÉTECTÉE !")
        print("="*50)
        fichier = archive.archiver_session()
        
        if fichier:
            print(f"✅ Session précédente archivée : {fichier}")
            archive.reinitialiser_tables_session()
        else:
            print("❌ ÉCHEC Archivage. La réinitialisation est ANNULÉE par sécurité pour ne pas perdre de données.")
            
        print("="*50 + "\n")

    # Mémorisation de l'état avant scraping
    ancienne_max_journee = determiner_prochaine_journee() - 1

    # 2. Scraping Séquentiel (Playwright n'est pas thread-safe)
    # Note: Playwright utilise des greenlets qui ne peuvent pas être partagés entre threads
    print("Demarrage du scraping (Tentative 1)...")
    try:
        scraper_results.extraire_donnees_resultats(page_results)
        logger.info("✅ Résultats terminé avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur dans le scraper Résultats: {e}", exc_info=True)
        print(f"❌ Erreur dans le scraper Résultats: {e}")
    
    try:
        scraper_ranking.extraire_donnees_classement(page_ranking)
        logger.info("✅ Classement terminé avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur dans le scraper Classement: {e}", exc_info=True)
        print(f"❌ Erreur dans le scraper Classement: {e}")
    
    try:
        scraper_odds.extraire_donnees_cotes(page_matches)
        logger.info("✅ Cotes terminé avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur dans le scraper Cotes: {e}", exc_info=True)
        print(f"❌ Erreur dans le scraper Cotes: {e}")
    
    # 2.5 Vérification et Re-Scraping si nécessaire
    nouvelle_max_journee = determiner_prochaine_journee() - 1
    
    if nouvelle_max_journee == ancienne_max_journee:
        print(f"⚠️ Warning : Aucune nouvelle journée détectée (Max J{ancienne_max_journee}).")
        print("⏳ Le site n'a peut-être pas encore affiché les résultats. Attente de 15s avant retentive...")
        
        time.sleep(15)
        page_results.reload(wait_until="domcontentloaded")
        
        # Tentative 2
        print("🔄 Demarrage du scraping (Tentative 2)...")
        scraper_results.extraire_donnees_resultats(page_results)
        
        # On ne re-scrape le classement/cotes que si les résultats sont là, mais pour simplifier on peut ou non
        # Ici on re-tente surtout les résultats car c'est le déclencheur
        
        nouvelle_max_journee_v2 = determiner_prochaine_journee() - 1
        if nouvelle_max_journee_v2 > ancienne_max_journee:
            print(f"✅ Succès Tentative 2 : Données récupérées (J{nouvelle_max_journee_v2}) !")
        else:
            print("❌ Echec Tentative 2 : Toujours pas de nouvelles données. On passe au cycle suivant.")
    else:
        print(f"✅ Données récupérées avec succès (J{nouvelle_max_journee}).")

    # 3. Validation des prédictions
    intelligence.mettre_a_jour_scoring()

    # 4. Intelligence et Prédiction
    journee = determiner_prochaine_journee()
    print(f"Analyse pour la Journee {journee}...")
    
    # Recharger le config pour détecter les changements depuis le dashboard
    import importlib
    import sys
    global _last_selection_state
    
    if 'src.core.config' in sys.modules:
        importlib.reload(sys.modules['src.core.config'])
        # Réimporter config pour avoir la valeur à jour
        from src.core import config
        
        # Détecter le changement de phase et afficher le message
        current_state = config.USE_SELECTION_AMELIOREE
        
        # Initialiser l'état au premier chargement
        if _last_selection_state is None:
            _last_selection_state = current_state
            # Afficher l'état initial si Phase 3 est active
            if current_state:
                print("="*60)
                print("   🧠 INTELLIGENCE ACTIVE")
                print("="*60)
                print("   ✅ Mode Intelligence Complète (Phase 3)")
                print("   ↳ 7 facteurs d'analyse pondérés")
                print("   ↳ Détection automatique des pièges")
                print("   ↳ Analyse des patterns historiques")
                print("="*60 + "\n")
            else:
                print("="*60)
                print("   ℹ️ MODE STANDARD")
                print("="*60)
                print("   ↳ Calcul simple : Classement + Forme")
                print("="*60 + "\n")
        # Détecter les changements ultérieurs
        elif _last_selection_state != current_state:
            print("\n" + "="*60)
            if current_state:
                print("   🔄 CHANGEMENT DE MODE DÉTECTÉ")
                print("="*60)
                print("   ✅ ACTIVATION : Mode Intelligence Complète")
                print("   ↳ Passage à la Phase 3 (7 facteurs)")
                print("   ↳ Détection des pièges activée")
                print("   ↳ Analyse approfondie activée")
            else:
                print("   🔄 CHANGEMENT DE MODE DÉTECTÉ")
                print("="*60)
                print("   ℹ️ DÉSACTIVATION : Retour au Mode Standard")
                print("   ↳ Calcul simple uniquement")
            print("="*60 + "\n")
            _last_selection_state = current_state
    else:
        from src.core import config
        if _last_selection_state is None:
            _last_selection_state = config.USE_SELECTION_AMELIOREE
            if config.USE_SELECTION_AMELIOREE:
                print("="*60)
                print("   🧠 INTELLIGENCE ACTIVE")
                print("="*60)
                print("   ✅ Mode Intelligence Complète (Phase 3)")
                print("="*60 + "\n")
    
    # Phase 3 : Choix de la fonction de sélection selon la configuration
    if config.USE_SELECTION_AMELIOREE:
        selections = intelligence.selectionner_meilleurs_matchs_ameliore(journee)
    else:
        selections = intelligence.selectionner_meilleurs_matchs(journee)
    
    if selections:
        print(f"Succes : {len(selections)} predictions generees pour la Journee {journee}.")
    else:
        print("Info : Aucune prediction pour ce cycle.")
    
    return True

def main():
    print("="*60)
    print("   🚀 SYSTÈME GODMOD V2 - DÉMARRAGE")
    print("="*60)
    
    # Afficher le mode activé
    if config.USE_INTELLIGENCE_AMELIOREE and config.USE_SELECTION_AMELIOREE:
        print("✅ MODE INTELLIGENT ACTIVÉ")
        print("   ↳ Phase 3 Complète : 7 facteurs d'analyse")
        print("   ↳ Détection des pièges de cotes")
        print("   ↳ Analyse des confrontations directes")
        print("   ↳ Calcul du momentum des équipes")
    elif config.USE_INTELLIGENCE_AMELIOREE:
        print("⚠️ MODE INTERMÉDIAIRE ACTIVÉ")
        print("   ↳ Phase 2 : Calcul amélioré avec fallback")
    else:
        print("ℹ️ MODE NORMAL ACTIVÉ")
        print("   ↳ Calcul simple : Classement + Forme")
    
    print("="*60 + "\n")
    
    # --- MODIFICATION : Demande manuelle de session ---
    print("\n" + "!"*60)
    print("   ❓ QUESTION UTILISATEUR")
    print("!"*60)
    choix_session = input("   Est-ce une nouvelle session (reset + archive) ? (y/n) : ").strip().lower()
    
    force_same_session = False
    
    if choix_session == 'y':
        print("\n" + "="*50)
        print("🗂️ NOUVELLE SESSION FORCÉE PAR L'UTILISATEUR")
        print("="*50)
        fichier = archive.archiver_session()
        if fichier:
            print(f"✅ Session précédente archivée : {fichier}")
        else:
            print("⚠️ Pas d'archive créée (peut-être vide ou erreur).")
            
        archive.reinitialiser_tables_session()
        print("✅ Tables réinitialisées.")
        print("="*50 + "\n")
        
    elif choix_session == 'n':
        print("\nℹ️ Mode 'Même Session' sélectionné. La détection automatique sera désactivée pour ce démarrage.")
        force_same_session = True
    else:
        print("\n⚠️ Réponse non reconnue. Comportement par défaut (Détection automatique).")

    # Réinitialisation pour migration propre (ne touche pas aux données, juste structure)
    database.initialiser_db()
    
    dernier_scrap_time = 0
    INTERVALLE_MIN_SCRAP = 60 
    
    with sync_playwright() as p:
        browser, page_matches, page_results, page_ranking = utils.init_persistent_browser(p)
        
        # Scraping initial pour avoir une base de données dès le départ
        scraping_initial(page_results, page_ranking, force_same_session=force_same_session)
        
        try:
            while True:
                # On lance le cycle. La fonction wait_for_valid_cycle gère l'attente intelligente.
                executer_cycle(p, browser, page_matches, page_results, page_ranking)
                
                print("Fin du cycle. Reprise de la surveillance dans 5 secondes...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\nArret par l'utilisateur.")
        except Exception as e:
            logger.error(f"Erreur critique dans la boucle principale : {e}", exc_info=True)
            print(f"❌ Erreur critique : {e}")
        finally:
            try:
                browser.close()
            except Exception as e:
                logger.warning(f"Erreur lors de la fermeture du navigateur : {e}")
            print("Navigateur ferme. Fin.")

if __name__ == "__main__":
    main()
