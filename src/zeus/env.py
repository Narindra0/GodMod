import gymnasium as gym
import numpy as np
import sqlite3
import logging
from gymnasium import spaces
from src.core import database
from src.zeus import feature_engineering

logger = logging.getLogger(__name__)

class ZeusEnv(gym.Env):
    """
    Environnement Gym pour le Module ZEUS.
    Simule une session de paris match par match.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, db_path=None):
        super(ZeusEnv, self).__init__()
        
        # Define Action Space: 4 actions
        # 0: Parier 1, 1: Parier N, 2: Parier 2, 3: Skip
        self.action_space = spaces.Discrete(4)
        
        # Define Observation Space: 10 features (cf feature_engineering)
        # Valeurs continues entre -1 et 1 (environ)
        self.observation_space = spaces.Box(low=-5.0, high=5.0, shape=(10,), dtype=np.float32)
        
        self.matches = []
        self.current_step = 0
        self.total_reward = 0
        
        # Chargement des données
        self._load_data()

    def _load_data(self):
        """Charge TOUS les matchs joués (avec résultat) depuis la DB pour l'entraînement."""
        # Note: En production/inférence, on chargera un seul match spécifique.
        # Ici c'est pour l'entraînement offline sur historique.
        query = """
            SELECT 
                r.id, r.journee, r.score_dom, r.score_ext,
                c.cote_1, c.cote_x, c.cote_2,
                cl_dom.position as pos_dom, cl_dom.forme as forme_dom, cl_dom.points as pts_dom,
                cl_ext.position as pos_ext, cl_ext.forme as forme_ext, cl_ext.points as pts_ext
                -- On pourrait ajouter les stats de buts ici si dispo dans classement ou calculé
            FROM resultats r
            LEFT JOIN cotes c ON r.journee = c.journee AND r.equipe_dom_id = c.equipe_dom_id AND r.equipe_ext_id = c.equipe_ext_id
            LEFT JOIN classement cl_dom ON r.journee = cl_dom.journee AND r.equipe_dom_id = cl_dom.equipe_id
            LEFT JOIN classement cl_ext ON r.journee = cl_ext.journee AND r.equipe_ext_id = cl_ext.equipe_id
            WHERE r.score_dom IS NOT NULL  -- Seulement les matchs joués
            ORDER BY r.journee ASC, r.id ASC
        """
        try:
            with database.get_db_connection() as conn:
                # Need to fetch as dict for easier handling
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                rows = cursor.execute(query).fetchall()
                self.matches = [dict(row) for row in rows]
                logger.info(f"ZeusEnv chargé avec {len(self.matches)} matchs historiques.")
        except Exception as e:
            logger.error(f"Erreur chargement données ZeusEnv: {e}")
            self.matches = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.total_reward = 0
        
        if not self.matches:
            # Fallback si pas de données (éviter crash)
            return np.zeros(10, dtype=np.float32), {}
            
        return self._get_observation(), {}

    def step(self, action):
        if self.current_step >= len(self.matches):
            return np.zeros(10, dtype=np.float32), 0, True, False, {}
            
        match = self.matches[self.current_step]
        reward = self._calculate_reward(action, match)
        self.total_reward += reward
        
        self.current_step += 1
        terminated = self.current_step >= len(self.matches)
        truncated = False
        
        obs = self._get_observation() if not terminated else np.zeros(10, dtype=np.float32)
        
        return obs, reward, terminated, truncated, {"match_id": match['id']}

    def _get_observation(self):
        if self.current_step >= len(self.matches):
            return np.zeros(10, dtype=np.float32)
            
        match = self.matches[self.current_step]
        # Mapper les données DB vers le format attendu par feature_engineering
        # Attention: feature_engineering attend bp_dom, bc_dom etc. 
        # Si on ne les a pas dans la requête SQL ci-dessus, il faut les ajouter ou simuler
        # Pour l'instant on passe ce qu'on a.
        
        # TODO: Améliorer la requête SQL pour avoir les stats Buts Pour/Contre (Moyenne)
        # Pour une V1, on met 0 par défaut si manquant.
        
        return feature_engineering.construire_vecteur_etat(match)

    def is_risky_match(self, match):
        """
        Détermine si un match est risqué.
        Critères (un ou plusieurs):
        1. Cotes serrées: Différence entre fav et outsider faible.
        2. Cote favori élevée (> 2.10).
        3. Match de bas de tableau (2 équipes > 15ème).
        """
        try:
            c1 = float(match.get('cote_1', 0) or 0)
            cx = float(match.get('cote_x', 0) or 0)
            c2 = float(match.get('cote_2', 0) or 0)
            
            if c1 <= 1 or c2 <= 1: return True # Cotes manquantes -> Risque total
            
            odds = [c1, c2]
            fav_odd = min(odds)
            gap = abs(c1 - c2)
            
            # Critère 1: Match très serré (gap < 0.5)
            if gap < 0.5:
                return True
                
            # Critère 2: Favori incertain (> 2.10)
            if fav_odd > 2.10:
                return True
                
            # Critère 3: Proba de Nul élevée (Cote X < 3.20)
            if cx < 3.20:
                return True
                
            return False
        except:
            return True # Par défaut, dans le doute, c'est risqué.

    def _calculate_reward(self, action, match):
        """
        Calcule la récompense.
        """
        s_dom = match['score_dom']
        s_ext = match['score_ext']
        
        # Déterminer le vrai résultat
        if s_dom > s_ext:
            real_result = 0 # 1
        elif s_dom == s_ext:
            real_result = 1 # N
        else:
            real_result = 2 # 2
            
        if action == 3: # Skip
            # Récompense conditionnelle:
            # +2 SEULEMENT si le match était réellement risqué.
            # Sinon 0 (Manque à gagner acceptable, mais pas de bonus gratuit).
            if self.is_risky_match(match):
                return 2 
            else:
                return 0 # Skip sur un match "facile" = pas de bonus
            
        if action == real_result:
            return 10
        else:
            return -15

    def render(self, mode='human'):
        pass
