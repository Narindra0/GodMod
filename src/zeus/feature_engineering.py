import numpy as np

def get_stats_manquantes(match_data):
    """
    Fournit des valeurs par défaut intelligentes pour les stats manquantes.
    Basé sur les moyennes réelles du football français Ligue 1.
    """
    return {
        # Moyennes Ligue 1 : ~1.4 buts marqués domicile, ~1.1 encaissés
        'bp_dom': match_data.get('bp_dom', 1.4),  # Buts pour domicile
        'bc_dom': match_data.get('bc_dom', 1.1),  # Buts contre domicile
        'bp_ext': match_data.get('bp_ext', 1.1),  # Buts pour extérieur
        'bc_ext': match_data.get('bc_ext', 1.4),  # Buts contre extérieur
    }

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def normaliser_classement(pos_dom, pos_ext):
    """
    Calcule le différentiel de classement normalisé.
    Formule: (Pos_Dom - Pos_Ext) / 20
    Résultat entre -1 et 1 environ.
    """
    # Si positions invalides, on retourne 0 (neutre)
    if not pos_dom or not pos_ext:
        return 0.0
    return (pos_dom - pos_ext) / 20.0

def calculer_score_forme(forme_str):
    """
    Calcule un score de forme sur les 3 derniers matchs.
    Format attendu: "V-N-D" ou similaire.
    V=3, N=1, D=0.
    Retourne la somme normalisée sur 9 pts max (donc 0 à 1).
    """
    if not forme_str or not isinstance(forme_str, str):
        return 0.5 # Valeur neutre par défaut

    # Le projet stocke généralement la forme sous forme compacte "VVNDV" (sans séparateurs).
    # Mais on accepte aussi "V-N-D" / "V N D" etc.
    s = forme_str.upper().strip()
    s = s.replace("-", "").replace(" ", "")

    # On conserve uniquement les tokens valides.
    tokens = [c for c in s if c in ("V", "N", "D")]

    if not tokens:
        return 0.5

    # Prendre jusqu'à 5 matchs (cohérent avec le reste du projet) ; si tu veux 3, change ici.
    recent = tokens[:5]

    points = 0
    for c in recent:
        if c == "V":
            points += 3
        elif c == "N":
            points += 1
        else:  # "D"
            points += 0

    return points / (3.0 * len(recent))

def normaliser_stats_buts(buts_pour_moy, buts_contre_moy):
    """
    Normalise les stats de buts (Attaque/Défense).
    On suppose une moyenne max raisonnable de 3.0 ou 4.0 buts/match pour normaliser entre 0 et 1.
    """
    # Clip à 4.0 pour éviter valeurs aberrantes
    bp = min(safe_float(buts_pour_moy), 4.0) / 4.0
    bc = min(safe_float(buts_contre_moy), 4.0) / 4.0
    return bp, bc

def normaliser_cotes(cote_1, cote_x, cote_2):
    """
    Normalise les cotes.
    Si cotes manquantes (None ou 0), retourne 0.
    """
    def _inv(c):
        val = safe_float(c)
        if val <= 1.0: return 0.0 # Cote invalide/manquante
        return 1.0 / val

    return _inv(cote_1), _inv(cote_x), _inv(cote_2)

def construire_vecteur_etat(match_data):
    """
    Construit le vecteur d'état final (7 dimensions ou plus selon spec).
    Ordre:
    0: Diff Classement
    1: Forme Dom
    2: Forme Ext
    3: Attaque Dom
    4: Défense Dom
    5: Attaque Ext
    6: Défense Ext
    7,8,9: Probas implicites (Cotes)
    10: Progression Session (Journée/38)
    
    Note: Le document mentionnait "Vitesse de Forme" unique?
    "Vitesse de Forme : Évolution de la forme sur les 3 derniers matchs." -> Probablement delta?
    Simplifions: Score de forme Dom et Ext séparés pour que l'IA déduise le delta.
    
    Le document listait:
    1. Diff Classement
    2. Vitesse de Forme (Disons Delta Forme Dom - Forme Ext ?)
    3. Puissance Attaque (Dom)
    4. Fragilité Defensive (Dom) -> Ah "Moyenne buts marqués (Dom/Ext)", peut-être 2 features?
    5. Cotes (3 features)
    6. Session
    Total document spec: ~8 features.
    
    On va fournir le maximum d'info utile.
    """
    # Extraction
    pos_dom = match_data.get('pos_dom')
    pos_ext = match_data.get('pos_ext')
    
    forme_dom_score = calculer_score_forme(match_data.get('forme_dom', ''))
    forme_ext_score = calculer_score_forme(match_data.get('forme_ext', ''))
    
    # "Vitesse de Forme" interprétée comme différentiel
    diff_forme = forme_dom_score - forme_ext_score
    
    stats = get_stats_manquantes(match_data)
    bp_dom, bc_dom = normaliser_stats_buts(stats['bp_dom'], stats['bc_dom'])
    bp_ext, bc_ext = normaliser_stats_buts(stats['bp_ext'], stats['bc_ext'])
    
    p1, px, p2 = normaliser_cotes(match_data.get('cote_1'), match_data.get('cote_x'), match_data.get('cote_2'))
    
    progression = match_data.get('journee', 1) / 38.0
    
    # Vecteur assemblé
    # 1. Diff Classement
    f1 = normaliser_classement(pos_dom, pos_ext)
    # 2. Diff Forme
    f2 = diff_forme
    # 3. Attaque Dom / 4. Def Dom
    f3 = bp_dom
    f4 = bc_dom
    # 5. Attaque Ext / 6. Def Ext (Document disait Dom/Ext global? Mieux vaut séparer)
    f5 = bp_ext
    f6 = bc_ext
    # 7,8,9 Cotes (Probas)
    f7 = p1
    f8 = px
    f9 = p2
    # 10. Session
    f10 = progression
    
    return np.array([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10], dtype=np.float32)
