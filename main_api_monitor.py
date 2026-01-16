"""
Version alternative de main.py utilisant la surveillance API
Mode: API Monitor (sans Playwright)

Version: 2.1 - API Monitor
Date: Janvier 2025
"""

from src.core import config
from src.core import database
from src.analysis import intelligence
from src.api.api_monitor import start_monitoring
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def callback_predictions_ia(journee: int):
    """
    Callback appele automatiquement quand une nouvelle journee est detectee
    
    Cette fonction est executee apres la collecte complete des donnees.
    Elle met a jour le scoring IA et genere les predictions pour J+1.
    
    Args:
        journee: Numero de la journee qui vient d'etre collectee
    """
    print(f"\n{'='*60}")
    print(f"   [IA] ANALYSE INTELLIGENTE - J{journee}")
    print(f"{'='*60}")
    
    try:
        # 1. Mettre a jour le score IA
        print(f"\n[ETAPE 1] Mise a jour du scoring IA...")
        intelligence.mettre_a_jour_scoring()
        print(f"   [OK] Score IA mis a jour")
        
        # 2. Determiner la journee a predire (J+1)
        journee_prediction = journee + 1
        
        # 3. Verifier si on peut faire des predictions
        if journee_prediction < config.JOURNEE_DEPART_PREDICTION:
            print(f"\n[INFO] J{journee_prediction} < J{config.JOURNEE_DEPART_PREDICTION} (minimum)")
            print(f"        Collecte des donnees uniquement, pas de predictions.")
            print(f"{'='*60}\n")
            return
        
        # 4. Generer les predictions selon le mode
        print(f"\n[ETAPE 2] Generation predictions pour J{journee_prediction}...")
        
        if config.USE_SELECTION_AMELIOREE:
            print(f"   Mode: Intelligence Complete (Phase 3)")
            selections = intelligence.selectionner_meilleurs_matchs_ameliore(journee_prediction)
        else:
            print(f"   Mode: Standard")
            selections = intelligence.selectionner_meilleurs_matchs(journee_prediction)
        
        # 5. Afficher les resultats
        if selections:
            print(f"\n   [OK] {len(selections)} predictions generees pour J{journee_prediction}")
            print(f"\n   Predictions:")
            for i, sel in enumerate(selections, 1):
                equipe_dom = sel.get('equipe_dom', 'N/A')
                equipe_ext = sel.get('equipe_ext', 'N/A')
                prediction = sel.get('prediction', 'N/A')
                fiabilite = sel.get('fiabilite', 0)
                print(f"      {i}. {equipe_dom} vs {equipe_ext} → {prediction} ({fiabilite:.1f}%)")
        else:
            print(f"\n   [INFO] Aucune prediction generee pour J{journee_prediction}")
            print(f"      (Criteres de selection non remplis)")
        
    except Exception as e:
        logger.error(f"Erreur dans callback IA : {e}", exc_info=True)
        print(f"\n   [ERREUR] Erreur lors de l'analyse : {e}")
    
    print(f"\n{'='*60}")
    print(f"   [OK] ANALYSE TERMINEE")
    print(f"{'='*60}\n")


def main():
    """
    Point d'entree principal - Mode API Monitor
    """
    print("\n" + "="*60)
    print("   [START] GODMOD V2 - MODE API MONITOR")
    print("="*60)
    print("   [INFO] Surveillance continue de l'API")
    print("   [INFO] Detection automatique nouvelles journees")
    print("   [INFO] Ultra-leger (pas de navigateur)")
    print("="*60 + "\n")
    
    # Afficher le mode intelligent
    if config.USE_INTELLIGENCE_AMELIOREE and config.USE_SELECTION_AMELIOREE:
        print("[OK] MODE INTELLIGENT ACTIF")
        print("   -> Phase 3 Complete : 7 facteurs d'analyse")
        print("   -> Detection des pieges de cotes")
        print("   -> Analyse des confrontations directes")
    elif config.USE_INTELLIGENCE_AMELIOREE:
        print("[WARN] MODE INTERMEDIAIRE ACTIF")
        print("   -> Phase 2 : Calcul ameliore")
    else:
        print("[INFO] MODE NORMAL ACTIF")
        print("   -> Calcul simple : Classement + Forme")
    
    print("="*60 + "\n")
    
    # Initialiser la base de donnees
    print("[INIT] Initialisation de la base de donnees...")
    try:
        database.initialiser_db()
        print("   [OK] Base de donnees prete\n")
    except Exception as e:
        logger.error(f"Erreur initialisation BDD : {e}", exc_info=True)
        print(f"   [ERREUR] Erreur BDD : {e}\n")
        return
    
    # Demarrer la surveillance avec callback IA
    print("[START] Demarrage de la surveillance API...\n")
    try:
        start_monitoring(
            callback_on_new_journee=callback_predictions_ia,
            verbose=True
        )
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("   [STOP] ARRET DU SYSTEME")
        print("="*60)
        logger.info("Arret par utilisateur")
    except Exception as e:
        logger.error(f"Erreur critique : {e}", exc_info=True)
        print(f"\n[ERREUR] Erreur critique : {e}")
    finally:
        print("\n[OK] Systeme arrete proprement.")


if __name__ == "__main__":
    main()
