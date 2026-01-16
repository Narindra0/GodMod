import gymnasium as gym
import numpy as np
import sqlite3
import logging
from gymnasium import spaces
from src.core import database
from src.zeus import feature_engineering
from src.zeus.archive_manager import get_classement_archive

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
                c.journee, c.equipe_dom_id, c.equipe_ext_id,
                c.cote_1, c.cote_x, c.cote_2,
                r.score_dom, r.score_ext  -- NULL si match non joué
            FROM cotes c
            LEFT JOIN resultats r ON c.journee = r.journee AND c.equipe_dom_id = r.equipe_dom_id AND c.equipe_ext_id = r.equipe_ext_id
            WHERE c.journee >= 1  -- Toutes les journées disponibles
            ORDER BY c.journee DESC, c.equipe_dom_id ASC
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
        
        return obs, reward, terminated, truncated, {"match_id": match.get('equipe_dom_id', 0)}

    def _get_observation(self):
        if self.current_step >= len(self.matches):
            return np.zeros(10, dtype=np.float32)
            
        match = self.matches[self.current_step]
        
        # Récupérer le classement archivé pour cette journée
        journee = match.get('journee')
        dom_id = match.get('equipe_dom_id')
        ext_id = match.get('equipe_ext_id')
        
        # Cloner les données du match et ajouter le classement archivé
        match_data = dict(match)
        
        # Ajouter les données du classement depuis l'archive
        classement_dom = get_classement_archive(journee, dom_id)
        classement_ext = get_classement_archive(journee, ext_id)
        
        if classement_dom:
            match_data['pos_dom'] = classement_dom[1]  # position
            match_data['forme_dom'] = classement_dom[3]  # forme
            match_data['pts_dom'] = classement_dom[2]  # points
            match_data['bp_dom'] = classement_dom[4] or 1.4  # buts_pour
            match_data['bc_dom'] = classement_dom[5] or 1.1  # buts_contre
        else:
            # Valeurs par défaut si pas d'archive
            match_data['pos_dom'] = 10
            match_data['forme_dom'] = 'VVNDD'
            match_data['pts_dom'] = 30
            match_data['bp_dom'] = 1.4
            match_data['bc_dom'] = 1.1
            
        if classement_ext:
            match_data['pos_ext'] = classement_ext[1]  # position
            match_data['forme_ext'] = classement_ext[3]  # forme
            match_data['pts_ext'] = classement_ext[2]  # points
            match_data['bp_ext'] = classement_ext[4] or 1.1  # buts_pour
            match_data['bc_ext'] = classement_ext[5] or 1.4  # buts_contre
        else:
            # Valeurs par défaut si pas d'archive
            match_data['pos_ext'] = 10
            match_data['forme_ext'] = 'VVNDD'
            match_data['pts_ext'] = 30
            match_data['bp_ext'] = 1.1
            match_data['bc_ext'] = 1.4
        
        return feature_engineering.construire_vecteur_etat(match_data)

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

        # SCENARIO B : Match à venir (Score = None)
        # On ne peut pas savoir si l'IA a gagné ou perdu.
        if s_dom is None or s_ext is None:
            if action == 3: # Skip prudent
                return 1 # Petite récompense pour la prudence
            else:
                return 0 # Neutre pour les paris (on ne sait pas encore)
        
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
