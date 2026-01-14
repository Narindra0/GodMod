import logging
import importlib
import sys
from ..core import config
from ..core.database import get_db_connection
from ..zeus import inference as zeus_inference # Module ZEUS

logger = logging.getLogger(__name__)

def _reload_config():
    """Recharge le module config pour prendre en compte les changements depuis le dashboard."""
    if 'src.core.config' in sys.modules:
        importlib.reload(sys.modules['src.core.config'])
        # Réassigner la référence locale
        globals()['config'] = sys.modules['src.core.config']

def calculer_probabilite_avec_fallback(equipe_dom_id, equipe_ext_id, cote_1=None, cote_x=None, cote_2=None):
    """
    Phase 2 : Utilise toujours le calcul amélioré, avec fallback vers l'ancien si les cotes manquent.
    
    Cette fonction garantit que le nouveau système est utilisé par défaut, mais peut
    revenir à l'ancien calcul si les données nécessaires (cotes) ne sont pas disponibles.
    
    Args:
        equipe_dom_id: ID de l'équipe à domicile
        equipe_ext_id: ID de l'équipe à l'extérieur
        cote_1: Cote victoire domicile (optionnel)
        cote_x: Cote match nul (optionnel)
        cote_2: Cote victoire extérieur (optionnel)
    
    Returns:
        Tuple (prediction, score_confiance)
    """
    # Si les cotes sont disponibles, utiliser le système amélioré
    if cote_1 is not None and cote_x is not None and cote_2 is not None:
        return calculer_probabilite_amelioree(equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2)
    else:
        # Fallback vers l'ancien système si les cotes manquent
        logger.warning(f"Cotes manquantes pour match {equipe_dom_id} vs {equipe_ext_id}. Utilisation du calcul simple.")
        return calculer_probabilite(equipe_dom_id, equipe_ext_id)

def calculer_probabilite(equipe_dom_id, equipe_ext_id):
    """
    Calcule une probabilité simplifiée basée sur le classement et la forme.
    Renvoie une recommandation (1, X, ou 2) et un score de confiance.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT points, forme FROM classement WHERE equipe_id = ?", (equipe_dom_id,))
            stats_dom = cursor.fetchone()
            
            cursor.execute("SELECT points, forme FROM classement WHERE equipe_id = ?", (equipe_ext_id,))
            stats_ext = cursor.fetchone()
    except Exception as e:
        logger.error(f"Erreur lors du calcul de probabilité : {e}", exc_info=True)
        return None, 0
    
    if not stats_dom or not stats_ext:
        return None, 0
    
    pts_dom, forme_dom = stats_dom
    pts_ext, forme_ext = stats_ext
    
    score_pts = (pts_dom - pts_ext) * 0.5
    
    def pondere_forme(f):
        valeurs = {'V': 3, 'N': 1, 'D': 0}
        return sum(valeurs.get(c, 0) for c in (f[-5:] if f else "")) 
    
    score_forme = pondere_forme(forme_dom) - pondere_forme(forme_ext)
    score_total = score_pts + score_forme
    
    if score_total > 5:
        return "1", score_total
    elif score_total < -5:
        return "2", abs(score_total)
    else:
        return "X", abs(score_total)


# ============================================
# PHASE 3 : FONCTION PRINCIPALE AMÉLIORÉE
# ============================================

def calculer_probabilite_amelioree(equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2):
    """
    Système complet d'analyse pour matchs virtuels (version améliorée).
    
    Facteurs analysés :
    1. Différence de classement (40%)
    2. Forme récente pondérée (30%) - Les 2 derniers matchs comptent 1.5× plus
    3. Buts marqués/encaissés (15%) - Attaque et défense récentes
    4. Avantage domicile (10%)
    5. Confrontations directes (5%) - Patterns historiques
    6. Analyse des cotes (bonus/malus) - Détection des pièges
    7. Momentum des équipes (bonus/malus) - Détection des séries
    
    Args:
        equipe_dom_id: ID de l'équipe à domicile
        equipe_ext_id: ID de l'équipe à l'extérieur
        cote_1: Cote victoire domicile
        cote_x: Cote match nul
        cote_2: Cote victoire extérieur
    
    Returns:
        Tuple (prediction, score_confiance) où:
        - prediction: "1", "X" ou "2"
        - score_confiance: Score de confiance (float)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # === RÉCUPÉRATION DES DONNÉES ===
            
            # Stats de base (classement et forme)
            cursor.execute("SELECT points, forme FROM classement WHERE equipe_id = ?", (equipe_dom_id,))
            stats_dom = cursor.fetchone()
            
            cursor.execute("SELECT points, forme FROM classement WHERE equipe_id = ?", (equipe_ext_id,))
            stats_ext = cursor.fetchone()
            
            if not stats_dom or not stats_ext:
                return None, 0
            
            pts_dom, forme_dom = stats_dom
            pts_ext, forme_ext = stats_ext
            
            # Buts récents (analyse attaque/défense)
            buts_dom = analyser_buts_recents_internal(cursor, equipe_dom_id)
            buts_ext = analyser_buts_recents_internal(cursor, equipe_ext_id)
    
    except Exception as e:
        logger.error(f"Erreur lors du calcul de probabilité améliorée : {e}", exc_info=True)
        return None, 0
    
    # === CALCULS PONDÉRÉS ===
    
    # 1. CLASSEMENT (40% du poids)
    score_classement = (pts_dom - pts_ext) * 0.4
    
    # 2. FORME RÉCENTE PONDÉRÉE (30% du poids)
    forme_dom_score = pondere_forme_amelioree(forme_dom)
    forme_ext_score = pondere_forme_amelioree(forme_ext)
    score_forme = (forme_dom_score - forme_ext_score) * 0.3
    
    # 3. BUTS (15% du poids)
    score_buts = 0
    if buts_dom and buts_ext:
        buts_pour_dom, buts_contre_dom = buts_dom
        buts_pour_ext, buts_contre_ext = buts_ext
        
        diff_attaque = (buts_pour_dom - buts_pour_ext) * 0.1
        diff_defense = (buts_contre_ext - buts_contre_dom) * 0.1
        score_buts = (diff_attaque + diff_defense) * 0.15
    
    # 4. AVANTAGE DOMICILE (10% du poids)
    avantage_domicile = 2.0
    
    # Score de base
    score_base = score_classement + score_forme + score_buts + avantage_domicile
    
    # === VALIDATIONS ET REJETS STRICTS (Optimisations Roadmap) ===
    
    # REJET 1 : Instabilité détectée (patterns VDV, DVD, etc.)
    if detecter_instabilite(forme_dom) or detecter_instabilite(forme_ext):
        logger.info(f"🚫 Match REJETÉ (Instabilité) : {equipe_dom_id} vs {equipe_ext_id}")
        logger.info(f"   ↳ Forme Domicile: {forme_dom}, Forme Extérieur: {forme_ext}")
        return None, 0
    
    # REJET 2 : Match équilibré (triple cote proche)
    if detecter_match_equilibre(cote_1, cote_x, cote_2):
        logger.info(f"🚫 Match REJETÉ (Équilibre excessif) : {equipe_dom_id} vs {equipe_ext_id}")
        logger.info(f"   ↳ Cotes: {cote_1:.2f} - {cote_x:.2f} - {cote_2:.2f}")
        return None, 0
    
    # === BONUS/MALUS ADDITIONNELS ===
    
    # 5. CONFRONTATIONS DIRECTES
    bonus_pattern = analyser_confrontations_directes(equipe_dom_id, equipe_ext_id)
    
    # REJET 3 : Historique très défavorable
    if bonus_pattern <= -2.5:
        logger.info(f"🚫 Match REJETÉ (Historique défavorable) : {equipe_dom_id} vs {equipe_ext_id}")
        logger.info(f"   ↳ Pattern historique: {bonus_pattern:.2f}")
        return None, 0
    
    # 6. ANALYSE DES COTES (détection des pièges)
    bonus_cotes = analyser_cotes_suspectes(cote_1, cote_x, cote_2)
    
    # REJET 4 : Piège à cotes (favori évident)
    if bonus_cotes <= -3.0:
        logger.info(f"🚫 Match REJETÉ (Piège à cotes) : {equipe_dom_id} vs {equipe_ext_id} (Cote: {cote_1 if cote_1 < cote_2 else cote_2})")
        return None, 0
    
    # 7. MOMENTUM (séries de victoires/défaites)
    momentum_dom = calculer_momentum_internal(forme_dom)
    momentum_ext = calculer_momentum_internal(forme_ext)
    bonus_momentum = (momentum_dom - momentum_ext) * 0.5
    
    # === SCORE FINAL ===
    score_final = score_base + bonus_pattern + bonus_cotes + bonus_momentum
    
    # Détermination de la prédiction avec seuils optimisés (roadmap)
    SEUIL_VICTOIRE = 7.0
    SEUIL_NUL_MIN = -3.0   # Nouveau : limite basse du nul
    SEUIL_NUL_MAX = 3.0    # Nouveau : limite haute du nul
    
    if score_final > SEUIL_VICTOIRE:
        return "1", score_final
    elif score_final < -SEUIL_VICTOIRE:
        return "2", abs(score_final)
    elif SEUIL_NUL_MIN <= score_final <= SEUIL_NUL_MAX:
        return "X", abs(score_final)
    else:
        # Zone d'incertitude (3.0 < |score| < 7.0) : REJET
        logger.info(f"🚫 Match REJETÉ (Zone d'incertitude : score {score_final:.2f})")
        return None, 0


def analyser_performances_recentes():
    """
    Analyse les 9 dernières prédictions validées pour déterminer la tendance.
    Retourne: (taux_succes, message_etat)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT succes FROM predictions WHERE succes IS NOT NULL ORDER BY id DESC LIMIT 9")
            resultats = cursor.fetchall()
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des performances : {e}", exc_info=True)
        return 1.0, "Erreur (Vérification DB)"
    
    if not resultats:
        return 1.0, "Neutre (Pas d'historique)"
        
    succes_count = sum(1 for r in resultats if r[0] == 1)
    total = len(resultats)
    taux = succes_count / total
    
    return taux, f"{succes_count}/{total}"

def selectionner_meilleurs_matchs(journee):
    """Sélectionne 2-3 matchs maximum pour une journée donnée via IDs, avec adaptation dynamique."""
    
    # Recharger le module config pour prendre en compte les changements depuis le dashboard
    # Cela permet au programme principal de détecter les changements faits via le dashboard
    _reload_config()
    
    # 1. Cas J < 4 : Pas assez de données
    if journee < 4:
        print(f"Info : Journee {journee} < 4. Pas assez de données pour pronostic.")
        return []
        
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # --- VÉRIFICATION PAUSE / RENFORCEMENT ---
            cursor.execute("SELECT score, pause_until FROM score_ia WHERE id = 1")
            row_ia = cursor.fetchone()
            score_ia = row_ia[0] if row_ia else 100
            pause_until = row_ia[1] if row_ia and len(row_ia) > 1 else 0
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du score IA : {e}", exc_info=True)
        return []
    
    # Si une pause est active
    if pause_until >= journee:
        print(f"🛑 MODE RENFORCEMENT ACTIF (J{journee}). Pause jusqu'à la journée {pause_until + 1}.")
        print("   ↳ Le programme continue de scanner les données sans faire de pronostics.")
        return []

    # Si le score est trop faible -> Activation de la pause
    # MAIS : On vérifie si on vient de sortir d'une pause (Immunité de 3 journées pour laisser le temps au score de remonter)
    in_immunity = (journee <= pause_until + 3)
    
    if score_ia < 60 and not in_immunity:
        pause_until_new = journee + 2
        print(f"🚨 ALERTE : Score IA critique ({score_ia} < 60). Activation du mode RENFORCEMENT.")
        print(f"   ↳ Pause des pronostics pour les journées {journee}, {journee+1} et {journee+2}.")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE score_ia SET pause_until = ? WHERE id = 1", (pause_until_new,))
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la pause : {e}", exc_info=True)
        return []
    elif score_ia < 60 and in_immunity:
        print(f"🛡️ MODE IMMUNITÉ (J{journee}). Le score est critique ({score_ia}) mais on tente de se refaire (Fin pause J{pause_until}).")
    
    predictions = []
    
    # 2. Cas 4 <= J < 10 : Mode "Prise de risque"
    if 4 <= journee < 10:
        print(f"⚠️ Mode Prise de risque (J{journee}). Seuil de confiance réduit.")
        print(f"📊 Phase 2 : Utilisation du calcul amélioré (avec fallback si cotes manquantes)")
        seuil_confiance = 5.0  # Seuil modéré selon le guide (au lieu de 3.5)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2 FROM cotes WHERE journee = ?", (journee,))
                matchs = cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des matchs : {e}", exc_info=True)
            return []
        
        for m in matchs:
            dom_id, ext_id, c1, cx, c2 = m
            # Phase 2 : Utilisation systématique du calcul amélioré (avec fallback automatique)
            pred, confiance = calculer_probabilite_avec_fallback(dom_id, ext_id, c1, cx, c2)
            
            if pred and confiance > seuil_confiance:
                predictions.append({
                    'equipe_dom_id': dom_id,
                    'equipe_ext_id': ext_id,
                    'prediction': pred,
                    'confiance': confiance
                })
                
    # 3. Cas J >= 10 : Mode Standard (avec Intelligence Adaptative)
    else:
        # --- INTELLIGENCE ADAPTATIVE ---
        taux_succes, ratio_str = analyser_performances_recentes()
        
        # Définition des profils de risque (seuils ajustés selon le guide)
        # Par défaut : Seuil 7.0 (au lieu de 5.0)
        seuil_confiance = 7.0
        mode = "Standard"
        
        # Règle utilisateur : "Si moins de 5/9 réussites (55%), ajuster"
        if taux_succes < 0.35: # Crise (< 3/9)
            seuil_confiance = 10.0  # Ajusté selon le guide
            mode = "DÉFENSIF (Crise)"
        elif taux_succes < 0.55: # Prudence (< 5/9)
            seuil_confiance = 8.5  # Ajusté selon le guide
            mode = "PRUDENT"
        elif taux_succes > 0.80: # Confiance (> 7/9)
            seuil_confiance = 6.0  # Ajusté selon le guide
            mode = "OFFENSIF"
            
        print(f"🧠 ANALYSE IA : {ratio_str} ({taux_succes*100:.0f}%) -> {mode}")
        print(f"   ↳ Seuil de confiance : {seuil_confiance}")
        print(f"📊 Phase 2 : Utilisation du calcul amélioré (avec fallback si cotes manquantes)")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2 FROM cotes WHERE journee = ?", (journee,))
                matchs = cursor.fetchall()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des matchs : {e}", exc_info=True)
            return []
        
        for m in matchs:
            dom_id, ext_id, c1, cx, c2 = m
            # Phase 2 : Utilisation systématique du calcul amélioré (avec fallback automatique)
            pred, confiance = calculer_probabilite_avec_fallback(dom_id, ext_id, c1, cx, c2)
            
            # On utilise le seuil dynamique déterminé par l'IA
            if pred and confiance > seuil_confiance:
                predictions.append({
                    'equipe_dom_id': dom_id,
                    'equipe_ext_id': ext_id,
                    'prediction': pred,
                    'confiance': confiance
                })
    
    predictions.sort(key=lambda x: x['confiance'], reverse=True)
    
    # Enregistrement en DB (batch)
    if predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for p in predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]:
                    cursor.execute('''
                        INSERT INTO predictions (journee, equipe_dom_id, equipe_ext_id, prediction)
                        VALUES (?, ?, ?, ?)
                    ''', (journee, p['equipe_dom_id'], p['equipe_ext_id'], p['prediction']))
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des prédictions : {e}", exc_info=True)
    
    return predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]


# ============================================
# PHASE 3 : NOUVELLE SÉLECTION AMÉLIORÉE
# ============================================

def selectionner_meilleurs_matchs_ameliore(journee):
    """
    Phase 3 : Sélection intelligente avec le nouveau système d'analyse complet.
    
    Cette fonction utilise tous les facteurs améliorés :
    - Forme pondérée (les 2 derniers matchs comptent 1.5× plus)
    - Analyse des buts (attaque/défense)
    - Détection des pièges à cotes
    - Confrontations directes (patterns historiques)
    - Momentum (séries de victoires/défaites)
    - Seuils dynamiques selon les performances récentes
    
    Args:
        journee: Numéro de la journée à analyser
    
    Returns:
        Liste des prédictions sélectionnées (max MAX_PREDICTIONS_PAR_JOURNEE)
    """
    # Recharger le module config pour prendre en compte les changements depuis le dashboard
    _reload_config()
    
    # 1. Cas J < 4 : Pas assez de données
    if journee < 4:
        print(f"Info : Journée {journee} < 4. Pas assez de données pour pronostic.")
        return []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # --- VÉRIFICATION PAUSE / RENFORCEMENT ---
            cursor.execute("SELECT score, pause_until FROM score_ia WHERE id = 1")
            row_ia = cursor.fetchone()
            score_ia = row_ia[0] if row_ia else 100
            pause_until = row_ia[1] if row_ia and len(row_ia) > 1 else 0
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du score IA : {e}", exc_info=True)
        return []
    
    # Si une pause est active
    if pause_until >= journee:
        print(f"🛑 MODE RENFORCEMENT ACTIF (J{journee}). Pause jusqu'à la journée {pause_until + 1}.")
        print("   ↳ Le programme continue de scanner les données sans faire de pronostics.")
        return []

    # Si le score est trop faible -> Activation de la pause
    # MAIS : On vérifie si on vient de sortir d'une pause (Immunité de 3 journées)
    in_immunity = (journee <= pause_until + 3)
    
    if score_ia < 60 and not in_immunity:
        pause_until_new = journee + 2
        print(f"🚨 ALERTE : Score IA critique ({score_ia} < 60). Activation du mode RENFORCEMENT.")
        print(f"   ↳ Pause des pronostics pour les journées {journee}, {journee+1} et {journee+2}.")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE score_ia SET pause_until = ? WHERE id = 1", (pause_until_new,))
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la pause : {e}", exc_info=True)
        return []
    elif score_ia < 60 and in_immunity:
        print(f"🛡️ MODE IMMUNITÉ (J{journee}). Le score est critique ({score_ia}) mais on tente de se refaire (Fin pause J{pause_until}).")
    
    predictions = []
    
    # 2. Détermination du seuil de confiance (Intelligence adaptative)
    if 4 <= journee < 10:
        seuil_confiance = 5.0  # Mode prise de risque modéré
        print(f"⚠️ Mode Prise de risque (J{journee}). Seuil : {seuil_confiance}")
    else:
        taux_succes, ratio_str = analyser_performances_recentes()
        
        seuil_confiance = 7.0  # Défaut
        mode = "Standard"
        
        if taux_succes < 0.35:
            seuil_confiance = 10.0
            mode = "DÉFENSIF (Crise)"
        elif taux_succes < 0.55:
            seuil_confiance = 8.5
            mode = "PRUDENT"
        elif taux_succes > 0.80:
            seuil_confiance = 6.0
            mode = "OFFENSIF"
        
        print(f"🧠 ANALYSE IA : {ratio_str} ({taux_succes*100:.0f}%) -> {mode}")
        print(f"   ↳ Seuil de confiance : {seuil_confiance}")
    
    # 3. Récupération des matchs avec cotes
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2 FROM cotes WHERE journee = ?", (journee,))
            matchs = cursor.fetchall()
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des matchs : {e}", exc_info=True)
        return []
    
    # 4. Analyse de chaque match avec le nouveau système complet
    print(f"📊 Phase 3 : Analyse avec système amélioré multi-facteurs")
    for m in matchs:
        dom_id, ext_id, c1, cx, c2 = m
        
        # Utilisation directe de la fonction améliorée (pas de fallback en Phase 3)
        # Si les cotes sont None, on passe ce match (le système amélioré nécessite les cotes)
        if c1 is None or cx is None or c2 is None:
            logger.warning(f"Cotes manquantes pour match {dom_id} vs {ext_id}. Match ignoré.")
            continue
        
        pred, confiance = calculer_probabilite_amelioree(dom_id, ext_id, c1, cx, c2)
        
        if pred and confiance > seuil_confiance:
            predictions.append({
                'equipe_dom_id': dom_id,
                'equipe_ext_id': ext_id,
                'prediction': pred,
                'confiance': confiance
            })

    # =========================================================================
    # MODULE ZEUS (SHADOW MODE)
    # =========================================================================
    # On profite de la boucle pour demander l'avis de Zeus
    # Cela n'impacte PAS les predictions officielles (shadow)
    print("⚡ ZEUS : Analyse en cours (Shadow Mode)...")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for m in matchs:
                dom_id, ext_id, c1, cx, c2 = m
                
                # Récup info manquante pour vecteur (classement/forme)
                # Note: On refait une petite requête, ou on optimise en amont. 
                # Pour V1 shadow, on fait simple.
                cursor.execute("SELECT position, forme, points FROM classement WHERE equipe_id = ? AND journee = ?", (dom_id, journee))
                d_info = cursor.fetchone()
                cursor.execute("SELECT position, forme, points FROM classement WHERE equipe_id = ? AND journee = ?", (ext_id, journee))
                e_info = cursor.fetchone()

                if d_info and e_info:
                     # On construit l'objet data pour Zeus
                     match_data = {
                         'pos_dom': d_info[0], 'pos_ext': e_info[0],
                         'forme_dom': d_info[1], 'forme_ext': e_info[1],
                         'cote_1': c1, 'cote_x': cx, 'cote_2': c2,
                         'journee': journee,
                         # On pourrait ajouter les stats de buts ici si on veut etre precis
                     }
                     
                     action = zeus_inference.predire_match(match_data)
                     
                     # Traduction action -> texte
                     labels = {0: "1", 1: "X", 2: "2", 3: "SKIP"}
                     pred_zeus = labels.get(action, "SKIP")
                     
                     # Log console si intéressant
                     if action != 3:
                         print(f"   ⚡ Zeus conseille : {pred_zeus} pour {dom_id} vs {ext_id}")
                     
                     # Sauvegarde DB
                     try:
                         conn.execute('''
                            INSERT OR IGNORE INTO zeus_predictions (journee, equipe_dom_id, equipe_ext_id, prediction)
                            VALUES (?, ?, ?, ?)
                         ''', (journee, dom_id, ext_id, action))
                     except Exception as sub_e:
                         pass # Ignorer doublons unique
    except Exception as e:
        logger.error(f"Erreur Shadow Mode Zeus: {e}")
    # =========================================================================
    
    # 5. Tri par confiance décroissante
    predictions.sort(key=lambda x: x['confiance'], reverse=True)
    
    # 6. Enregistrement en DB (top 2-3 selon MAX_PREDICTIONS_PAR_JOURNEE)
    if predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]:
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for p in predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]:
                    cursor.execute('''
                        INSERT INTO predictions (journee, equipe_dom_id, equipe_ext_id, prediction)
                        VALUES (?, ?, ?, ?)
                    ''', (journee, p['equipe_dom_id'], p['equipe_ext_id'], p['prediction']))
                # Pas de commit ici - le context manager s'en charge automatiquement
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des prédictions : {e}", exc_info=True)
    
    return predictions[:config.MAX_PREDICTIONS_PAR_JOURNEE]


# ============================================
# PHASE 1 : FONCTIONS AMÉLIORÉES (FACILES)
# ============================================

def pondere_forme_amelioree(f):
    """
    Les 2 derniers matchs comptent 1.5× plus que les 3 précédents.
    Améliore la détection de la forme récente pour les matchs virtuels.
    
    Args:
        f: Chaîne de caractères représentant la forme (ex: "VVVDN")
    
    Returns:
        Score pondéré de la forme (float)
    """
    valeurs = {'V': 3, 'N': 1, 'D': 0}
    
    if not f or len(f) < 5:
        # Si pas assez de données, utiliser la méthode classique
        return sum(valeurs.get(c, 0) for c in (f[-5:] if f else ""))
    
    forme_recente = f[-5:]  # 5 derniers matchs
    total = 0
    
    for i, resultat in enumerate(forme_recente):
        # Les 2 derniers matchs (indices 3 et 4) comptent 1.5× plus
        multiplicateur = 1.5 if i >= 3 else 1.0
        total += valeurs.get(resultat, 0) * multiplicateur
    
    return total


def detecter_instabilite(forme):
    """
    Détecte les patterns d'instabilité qui indiquent un comportement imprévisible.
    Les équipes alternant victoires et défaites sont à éviter.
    
    Args:
        forme: Chaîne de caractères représentant les 5 derniers matchs
    
    Returns:
        True si instabilité détectée, False sinon
    """
    if not forme or len(forme) < 3:
        return False
    
    # Patterns d'instabilité à éviter (optimisation roadmap)
    patterns_instables = [
        'VDV',   # Victoire-Défaite-Victoire
        'DVD',   # Défaite-Victoire-Défaite
        'VNV',   # Victoire-Nul-Victoire avec nul instable
        'DND',   # Défaite-Nul-Défaite
        'VDVD',  # Pattern long d'alternance
        'DVDV'   # Pattern long d'alternance
    ]
    
    for pattern in patterns_instables:
        if forme.endswith(pattern):
            return True
    
    return False


def calculer_momentum_internal(forme):
    """
    Détecte les séries de victoires ou défaites pour calculer le momentum.
    Se concentre sur la fin de la chaîne (dynamique actuelle).
    
    Note: Cette fonction ne détecte plus l'instabilité (gérée par detecter_instabilite)
    """
    if not forme or len(forme) < 3:
        return 0
    
    # Séries de victoires (priorité à la plus longue)
    if forme.endswith('VVV'):
        return 3.0
    elif forme.endswith('VV'):
        return 1.5
    
    # Séries de défaites
    elif forme.endswith('DDD'):
        return -3.0
    elif forme.endswith('DD'):
        return -1.5
    
    return 0


def detecter_match_equilibre(cote_1, cote_x, cote_2):
    """
    Détecte si un match est trop équilibré (triple cote proche).
    Les matchs avec 3 cotes très proches sont imprévisibles.
    
    Args:
        cote_1: Cote victoire domicile
        cote_x: Cote match nul
        cote_2: Cote victoire extérieur
    
    Returns:
        True si match trop équilibré, False sinon
    """
    if cote_1 is None or cote_x is None or cote_2 is None:
        return False
    
    ecart_1_2 = abs(cote_1 - cote_2)
    ecart_1_x = abs(cote_1 - cote_x)
    ecart_2_x = abs(cote_2 - cote_x)
    
    # Si les 3 cotes sont dans un intervalle de 0.4 (optimisation roadmap)
    if ecart_1_2 < 0.3 and ecart_1_x < 0.4 and ecart_2_x < 0.4:
        return True
    
    return False


def analyser_cotes_suspectes(cote_1, cote_x, cote_2):
    """
    Détecte les pièges dans les cotes des matchs virtuels.
    Les algorithmes virtuels ont tendance à faire perdre les favoris évidents.
    
    Args:
        cote_1: Cote victoire domicile
        cote_x: Cote match nul
        cote_2: Cote victoire extérieur
    
    Returns:
        Bonus/malus de confiance selon l'analyse des cotes
    """
    # Gestion des valeurs None
    if cote_1 is None or cote_x is None or cote_2 is None:
        return 0
    
    # Trouver la cote favorite (la plus basse, en excluant le nul)
    cote_min = min(cote_1, cote_2)
    cote_max = max(cote_1, cote_2)
    ecart = abs(cote_1 - cote_2)
    
    # ÉTAPE 1 : PIÈGES ABSOLUS (vérifiés en priorité)
    
    # PIÈGE 1 : Favori trop évident (cote < 1.30)
    if cote_min < 1.30:
        return -3.0
    
    # PIÈGE 2 : Match trop équilibré (écart < 0.3)
    # Note: Le rejet strict est maintenant géré par detecter_match_equilibre()
    if ecart < 0.299:
        return -1.5
    
    # ÉTAPE 2 : ZONE IDÉALE (vérifiée avant le bonus outsider)
    
    # ZONE IDÉALE : Cote entre 1.50 et 2.20
    if 1.50 <= cote_min <= 2.20:
        return 2.0
    
    # ÉTAPE 3 : BONUS OUTSIDER (vérifié en dernier)
    
    # Outsider trop côté (cote > 5.0)
    if cote_max > 5.0:
        return 1.0
    
    return 0


# ============================================
# PHASE 2 : FONCTIONS AVEC REQUÊTES SQL
# ============================================

def analyser_buts_recents_internal(cursor, equipe_id):
    """
    Analyse les buts marqués et encaissés sur les 5 derniers matchs joués.
    Nécessite que les scores soient non NULL dans la table resultats.
    
    Args:
        cursor: Curseur DB (doit être dans une transaction active)
        equipe_id: ID de l'équipe à analyser
    
    Returns:
        Tuple (buts_pour, buts_contre) ou None si pas assez de données
    """
    try:
        # Nouvelle requête corrigée : sélectionner les lignes puis agréger
        cursor.execute("""
            SELECT 
                CASE WHEN equipe_dom_id = ? THEN score_dom ELSE score_ext END as buts_pour,
                CASE WHEN equipe_dom_id = ? THEN score_ext ELSE score_dom END as buts_contre
            FROM resultats 
            WHERE (equipe_dom_id = ? OR equipe_ext_id = ?)
            AND score_dom IS NOT NULL
            AND score_ext IS NOT NULL
            ORDER BY journee DESC
            LIMIT 5
        """, (equipe_id, equipe_id, equipe_id, equipe_id))
        
        results = cursor.fetchall()
        
        if not results:
            return None
        
        # Calculer les sommes
        buts_pour = sum(r[0] for r in results)
        buts_contre = sum(r[1] for r in results)
        
        return buts_pour, buts_contre
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des buts pour l'équipe {equipe_id}: {e}", exc_info=True)
        return None


def analyser_confrontations_directes(equipe_dom_id, equipe_ext_id):
    """
    Analyse l'historique des 5 dernières confrontations directes entre deux équipes.
    Détecte les patterns répétitifs (certaines équipes battent toujours les mêmes adversaires).
    
    Args:
        equipe_dom_id: ID de l'équipe à domicile
        equipe_ext_id: ID de l'équipe à l'extérieur
    
    Returns:
        Bonus/malus selon les patterns détectés (-3.0 à +3.0)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Récupérer les 5 dernières confrontations (domicile de equipe_dom_id)
            cursor.execute("""
                SELECT score_dom, score_ext 
                FROM resultats 
                WHERE equipe_dom_id = ? AND equipe_ext_id = ?
                AND score_dom IS NOT NULL AND score_ext IS NOT NULL
                ORDER BY journee DESC 
                LIMIT 5
            """, (equipe_dom_id, equipe_ext_id))
            
            historique = cursor.fetchall()
        
        if not historique or len(historique) < 3:
            # Pas assez de données pour détecter un pattern
            return 0
        
        # Compter les victoires domicile, nuls et défaites
        victoires_dom = sum(1 for h in historique if h[0] > h[1])
        nuls = sum(1 for h in historique if h[0] == h[1])
        total = len(historique)
        
        taux_victoire_dom = victoires_dom / total
        taux_nul = nuls / total
        
        # Pattern détecté : Dominance du domicile
        if taux_victoire_dom >= 0.80:  # 4/5 ou 5/5 victoires domicile
            return 3.0  # Fort bonus
        elif taux_victoire_dom >= 0.60:  # 3/5 victoires
            return 1.5  # Bonus moyen
        elif taux_nul >= 0.60:  # Beaucoup de nuls
            return -2.0  # Malus : tendance aux matchs nuls
        elif taux_victoire_dom <= 0.20:  # Domicile perd souvent
            return -3.0  # Gros malus pour le domicile (favorable à l'extérieur)
        
        return 0
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse des confrontations directes : {e}", exc_info=True)
        return 0


def mettre_a_jour_scoring():
    """Valide les prédictions passées via IDs."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, journee, equipe_dom_id, equipe_ext_id, prediction FROM predictions WHERE succes IS NULL")
            en_attente = cursor.fetchall()
            
            for p in en_attente:
                pid, j, dom_id, ext_id, pred = p
                
                cursor.execute('''
                    SELECT score_dom, score_ext FROM resultats 
                    WHERE journee = ? AND equipe_dom_id = ? AND equipe_ext_id = ?
                ''', (j, dom_id, ext_id))
                res = cursor.fetchone()
                
                if res:
                    sd, se = res
                    resultat_reel = "1" if sd > se else ("2" if se > sd else "X")
                    succes = 1 if resultat_reel == pred else 0
                    points = config.POINTS_VICTOIRE if succes else config.POINTS_DEFAITE
                    
                    cursor.execute('''
                        UPDATE predictions 
                        SET resultat = ?, succes = ?, points_gagnes = ?
                        WHERE id = ?
                    ''', (resultat_reel, succes, points, pid))
                    
                    # Mise à jour du score IA global
                    if succes:
                        cursor.execute('''
                            UPDATE score_ia 
                            SET score = score + ?, 
                                predictions_reussies = predictions_reussies + 1, 
                                predictions_total = predictions_total + 1, 
                                derniere_maj = datetime("now") 
                            WHERE id = 1
                        ''', (points,))
                    else:
                        cursor.execute('''
                            UPDATE score_ia 
                            SET score = score + ?, 
                                predictions_total = predictions_total + 1, 
                                derniere_maj = datetime("now") 
                            WHERE id = 1
                        ''', (points,))
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du scoring : {e}", exc_info=True)
        print(f"❌ Erreur lors de la mise à jour du scoring : {e}")
        return
    
    print("Mise a jour du scoring terminee.")

if __name__ == "__main__":
    print("Lancez via main.py")
