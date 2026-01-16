import logging
import os
from stable_baselines3 import PPO, DQN
from stable_baselines3.common.callbacks import CheckpointCallback
from src.zeus.env import ZeusEnv

logger = logging.getLogger(__name__)

MODELS_DIR = "models/zeus"
LOGS_DIR = "logs/zeus"

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

class ZeusAgent:
    """
    Wrapper autour du modèle RL (PPO par défaut).
    Gère l'entraînement, la sauvegarde et l'inférence.
    """
    def __init__(self, model_name="zeus_v1", algo="PPO"):
        self.model_name = model_name
        self.algo = algo
        self.model = None
        self.env = ZeusEnv()

    def train(self, total_timesteps=100000):
        """Lance l'entraînement offline."""
        logger.info(f"Démarrage de l'entraînement {self.algo} pour {total_timesteps} steps.")
        
        if self.algo == "PPO":
            self.model = PPO("MlpPolicy", self.env, verbose=1, tensorboard_log=LOGS_DIR)
        elif self.algo == "DQN":
            self.model = DQN("MlpPolicy", self.env, verbose=1, tensorboard_log=LOGS_DIR)
        
        checkpoint_callback = CheckpointCallback(
            save_freq=10000, 
            save_path=MODELS_DIR,
            name_prefix=f"{self.model_name}"
        )
        
        self.model.learn(total_timesteps=total_timesteps, callback=checkpoint_callback)
        self.save()
        logger.info("Entraînement terminé.")

    def save(self):
        path = os.path.join(MODELS_DIR, f"{self.model_name}.zip")
        if self.model:
            self.model.save(path)
            logger.info(f"Modèle sauvegardé sous {path}")

    def load(self, path=None):
        if path is None:
            path = os.path.join(MODELS_DIR, f"{self.model_name}.zip")
        
        if os.path.exists(path):
            if self.algo == "PPO":
                self.model = PPO.load(path, env=self.env)
            elif self.algo == "DQN":
                self.model = DQN.load(path, env=self.env)
            logger.info(f"Modèle chargé depuis {path}")
            return True
        else:
            logger.warning(f"Aucun modèle trouvé à {path}")
            return False

    def predict(self, observation, deterministic=True):
        """
        Predit l'action pour une observation donnée.
        Retourne l'action et la confiance (si dispo).
        """
        if not self.model:
            logger.error("Modèle non chargé !")
            return None, None
            
        action, _states = self.model.predict(observation, deterministic=deterministic)
        return int(action)

    def predict_with_confidence(self, observation, deterministic=True):
        """
        Predit l'action avec un score de confiance.
        Supporte uniquement PPO pour l'instant.
        """
        if not self.model:
            logger.error("Modèle non chargé !")
            return 3, 0.0
            
        action, _ = self.model.predict(observation, deterministic=deterministic)
        confidence = 0.0
        
        try:
            if self.algo == "PPO":
                # Extraction des probabilités pour PPO (Categorical)
                import torch as th
                obs_tensor = self.model.policy.obs_to_tensor(observation)[0]
                distribution = self.model.policy.get_distribution(obs_tensor)
                probs = distribution.distribution.probs
                confidence = float(probs[0][action].item())
            elif self.algo == "DQN":
                # Pour DQN, on peut estimer via Q-values mais c'est moins standard
                # On retourne 1.0 par défaut ou une heuristique
                confidence = 1.0 
        except Exception as e:
            logger.warning(f"Impossible de calculer confiance: {e}")
            
        return int(action), confidence

if __name__ == "__main__":
    # Test simple
    agent = ZeusAgent()
    print("Agent initialisé.")
