"""
Systeme GODMOD V2 - Main Script
Mode: API Monitor (Optimise)

Ce script est le point d'entree principal de l'application.
Il utilise le module de surveillance API pour detecter automatiquement 
les nouvelles journees et lancer les analyses.

Version: 2.1
Date: Janvier 2025
"""

import logging
import sys
import os
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import des modules du projet
from src.core import config
from src.core import database
from src.analysis import intelligence
from src.api.api_monitor import start_monitoring

def callback_predictions_ia(journee: int):
    """
    Callback appele automatiquement quand une nouvelle journee est detectee.
    Execute apres la collecte complete des donnees (Resultats + Classement + Cotes).
    
    Args:
        journee: Numero de la journee qui vient d'etre collectee (ex: J15)
    """
    print(f"\n{'='*60}")
    print(f"\n{'='*60}")
    print(f"   [IA] ANALYSE INTELLIGENTE - J{journee}")
    print(f"{'='*60}")
    
    try:
        # 1. Mise a jour du scoring IA (validation des predictions precedentes)
        print(f"\n[ETAPE 1] Validation des predictions precedentes...")
        intelligence.mettre_a_jour_scoring()
        print(f"   [OK] Score IA mis a jour")
        
        # 2. Determiner la prochaine journee a predire
        # Si on vient de recuperer J15, on doit predire J16
        journee_prediction = journee + 1
        
        # 3. Verifier si on a atteint le debut des predictions (J10 par defaut)
        if journee_prediction < config.JOURNEE_DEPART_PREDICTION:
            print(f"\n[INFO] J{journee_prediction} < J{config.JOURNEE_DEPART_PREDICTION} (seuil de demarrage)")
            print(f"        Collecte des donnees uniquement. Pas de predictions.")
            print(f"{'='*60}\n")
            return
        
        # 4. Generation des predictions
        print(f"\n[ETAPE 2] Generation predictions pour J{journee_prediction}...")
        
        # Choix du mode selon configuration
        if config.USE_SELECTION_AMELIOREE:
            print(f"   Mode: Intelligence Complete (Phase 3 - 7 facteurs)")
            selections = intelligence.selectionner_meilleurs_matchs_ameliore(journee_prediction)
        else:
            print(f"   Mode: Standard")
            selections = intelligence.selectionner_meilleurs_matchs(journee_prediction)
        
        # 5. Affichage des resultats
        if selections:
            print(f"\n   [OK] {len(selections)} predictions generees pour J{journee_prediction}")
            print(f"\n   Details des Predictions :")
            for i, sel in enumerate(selections, 1):
                equipe_dom = sel.get('equipe_dom', 'N/A')
                equipe_ext = sel.get('equipe_ext', 'N/A')
                prediction = sel.get('prediction', 'N/A')
                fiabilite = sel.get('fiabilite', 0)
                
                # Affichage simple
                print(f"      {i}. {equipe_dom} vs {equipe_ext} → {prediction} ({fiabilite:.1f}%)")
        else:
            print(f"\n   [INFO] Aucune prediction retenue pour J{journee_prediction}")
            print(f"      (Les criteres de selection stricts n'ont pas ete remplis)")
        
    except Exception as e:
        logger.error(f"Erreur dans callback IA : {e}", exc_info=True)
        print(f"\n   [ERREUR] Erreur critique lors de l'analyse : {e}")
    
    print(f"\n{'='*60}")
    print(f"   [OK] CYCLE TERMINE - En attente de J{journee+1}...")
    print(f"{'='*60}\n")


def main():
    """
    Fonction principale
    """
    print("\n" + "="*60)
    print("   [START] GODMOD V2 - SYSTEME AUTONOME (API)")
    print("="*60)
    print("   [INFO] Mode: Surveillance API Temps Reel")
    print(f"   [INFO] Intervalle: 15 secondes")
    print("   [INFO] Detection automatique des nouvelles journees")
    print("="*60 + "\n")
    
    # 1. Initialisation BDD
    print("[INIT] Verification de la base de donnees...")
    try:
        database.initialiser_db()
        print("   [OK] Base de donnees connectee et a jour\n")
    except Exception as e:
        logger.error(f"Erreur initialisation BDD : {e}", exc_info=True)
        print(f"   [FATAL] Erreur fatale BDD : {e}\n")
        return

    # 2. Lancement de la surveillance
    print("🚀 Demarrage du cycle de surveillance...")
    print("   (Laissez cette fenetre ouverte)\n")
    
    try:
        # Cette fonction contient une boucle infinie qui surveille l'API
        # Elle appellera 'callback_predictions_ia' a chaque nouvelle journee
        start_monitoring(
            callback_on_new_journee=callback_predictions_ia,
            verbose=True
        )
        
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("   [STOP] ARRET DU SYSTEME DEMANDE PAR L'UTILISATEUR")
        print("="*60)
        logger.info("Arret par utilisateur (KeyboardInterrupt)")
        
    except Exception as e:
        logger.error(f"Erreur non geree dans main : {e}", exc_info=True)
        print(f"\n❌ Erreur critique du systeme : {e}")
        
    finally:
        print("\n[EXIT] Fermeture du programme.")
        time.sleep(1)

if __name__ == "__main__":
    main()
