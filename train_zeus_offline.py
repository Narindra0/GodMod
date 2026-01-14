from src.zeus.agent import ZeusAgent
import argparse

def main():
    parser = argparse.ArgumentParser(description="Entrainer l'agent Zeus.")
    parser.add_argument("--steps", type=int, default=100000, help="Nombre de steps d'entrainement")
    parser.add_argument("--algo", type=str, default="PPO", help="Algorithme (PPO ou DQN)")
    parser.add_argument("--model_name", type=str, default="zeus_v1", help="Nom du modele")
    
    args = parser.parse_args()
    
    print(f"--- Démarrage Entraînement ZEUS ({args.algo}) ---")
    agent = ZeusAgent(model_name=args.model_name, algo=args.algo)
    
    try:
        agent.train(total_timesteps=args.steps)
        print("✅ Entraînement terminé avec succès.")
    except Exception as e:
        print(f"❌ Erreur durant l'entraînement: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
