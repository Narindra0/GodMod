from src.zeus.agent import ZeusAgent
from src.zeus import feature_engineering, env
import logging

logger = logging.getLogger(__name__)

# Singleton pour l'agent (éviter de recharger à chaque requête)
_zeus_agent = None

def get_agent():
    global _zeus_agent
    if _zeus_agent is None:
        try:
            # On instancie l'agent sans entraînement
            # MODÈLE ACTIF : zeus_v3 (Profit-Driven)
            _zeus_agent = ZeusAgent(model_name="zeus_v3")
            success = _zeus_agent.load()
            if not success:
                logger.warning("Zeus: Impossible de charger le modèle zeus_v3.")
                _zeus_agent = None
        except Exception as e:
            logger.error(f"Zeus: Erreur init agent: {e}")
            return None
    return _zeus_agent

def reload_model():
    """
    Force le rechargement du modèle Zeus depuis le disque.
    """
    global _zeus_agent
    logger.info("Zeus: Reloading model...")
    _zeus_agent = None  # Force reset
    success = get_agent() is not None
    if success:
         logger.info("Zeus: Model reloaded successfully.")
    else:
         logger.error("Zeus: Failed to reload model.")
    return success

def predire_match(match_data):
    """
    Effectue une prédiction pour un match donné.
    match_data doit contenir:
     - pos_dom, pos_ext
     - forme_dom, forme_ext
     - cote_1, cote_x, cote_2
     - journee
    Retourne l'action (0..3)
    """
    agent = get_agent()
    if not agent:
        return 3 # Skip par défaut si pas d'agent
        
    try:
        # Construction du vecteur
        obs = feature_engineering.construire_vecteur_etat(match_data)
        
        # Prédiction
        action, confidence = agent.predict_with_confidence(obs, deterministic=True)
        return action, confidence
    except Exception as e:
        logger.error(f"Zeus: Erreur prédiction: {e}")
        return 3, 0.0 # Skip en cas d'erreur


