import sys
import os
import logging

# Add project root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.zeus.agent import ZeusAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_training(steps=50000, model_name="zeus_v2"):
    """
    Lance l'entraînement de l'agent Zeus.
    """
    print(f"\n⚡ Démarrage de l'entraînement ZEUS ({steps} steps)")
    print(f"   Modèle cible : {model_name}")
    print("   Chargement de l'environnement et des archives...")
    
    try:
        # Initialisation
        agent = ZeusAgent(model_name=model_name)
        
        # Lancement
        print("   🏋️ Entraînement en cours... (Cela peut prendre quelques minutes)")
        agent.train(total_timesteps=steps)
        
        print("\n✅ Entraînement terminé avec succès !")
        print(f"   Modèle sauvegardé dans : models/zeus/{model_name}.zip")
        
    except Exception as e:
        print(f"\n❌ Erreur fatale pendant l'entraînement : {e}")
        logger.error(f"Training failed: {e}", exc_info=True)

if __name__ == "__main__":
    # On peut passer le nombre de steps en argument
    steps = 30000
    model = "zeus_v3"
    
    if len(sys.argv) > 1:
        try:
            steps = int(sys.argv[1])
        except ValueError:
            pass
            
    run_training(steps=steps, model_name=model)
