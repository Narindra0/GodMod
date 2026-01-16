"""
Gestionnaire d'archive pour ZEUS - Mémoire Photographique
Permet de conserver l'historique du classement pour analyses précises
"""

import logging
from datetime import datetime
from src.core import database

logger = logging.getLogger(__name__)

def prendre_snapshot_classement(journee):
    """
    Prend un instantané du classement actuel et l'archive.
    
    Args:
        journee (int): Numéro de la journée à archiver
        
    Returns:
        int: Nombre d'équipes archivées
    """
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Récupérer le classement actuel (avant mise à jour)
            cursor.execute("""
                SELECT equipe_id, position, points, forme, buts_pour, buts_contre
                FROM classement
                WHERE journee = ?
            """, (journee,))
            
            classement_actuel = cursor.fetchall()
            
            if not classement_actuel:
                logger.warning(f"Aucun classement trouvé pour la journée {journee}")
                return 0
            
            # Archiver chaque équipe
            archived_count = 0
            for equipe_id, position, points, forme, bp, bc in classement_actuel:
                cursor.execute("""
                    INSERT OR REPLACE INTO zeus_classement_archive 
                    (journee, equipe_id, position, points, forme, buts_pour, buts_contre, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (journee, equipe_id, position, points, forme, bp, bc, datetime.now().isoformat()))
                archived_count += 1
            
            logger.info(f"📸 Snapshot J{journee}: {archived_count} équipes archivées")
            return archived_count
            
    except Exception as e:
        logger.error(f"Erreur lors du snapshot J{journee}: {e}")
        return 0

def get_classement_archive(journee, equipe_id=None):
    """
    Récupère le classement archivé pour une journée donnée.
    
    Args:
        journee (int): Journée souhaitée
        equipe_id (int, optional): ID d'équipe spécifique
        
    Returns:
        list: Données du classement archivé
    """
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            
            if equipe_id:
                cursor.execute("""
                    SELECT equipe_id, position, points, forme, buts_pour, buts_contre
                    FROM zeus_classement_archive
                    WHERE journee = ? AND equipe_id = ?
                """, (journee, equipe_id))
                return cursor.fetchone()
            else:
                cursor.execute("""
                    SELECT equipe_id, position, points, forme, buts_pour, buts_contre
                    FROM zeus_classement_archive
                    WHERE journee = ?
                    ORDER BY position ASC
                """, (journee,))
                return cursor.fetchall()
                
    except Exception as e:
        logger.error(f"Erreur récupération archive J{journee}: {e}")
        return []

def get_derniere_journee_archivee():
    """
    Récupère la dernière journée archivée.
    
    Returns:
        int: Numéro de la dernière journée archivée (0 si aucune)
    """
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(journee) FROM zeus_classement_archive
            """)
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0
            
    except Exception as e:
        logger.error(f"Erreur dernière journée archivée: {e}")
        return 0

def lister_journees_archivees():
    """
    Liste toutes les journées disponibles dans l'archive.
    
    Returns:
        list: Liste des numéros de journée archivés
    """
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT journee 
                FROM zeus_classement_archive 
                ORDER BY journee DESC
            """)
            return [row[0] for row in cursor.fetchall()]
            
    except Exception as e:
        logger.error(f"Erreur liste journées archivées: {e}")
        return []

def calculate_points(score_dom, score_ext):
    if score_dom > score_ext: return 3, 0
    if score_dom < score_ext: return 0, 3
    return 1, 1

def rebuild_history_from_db():
    """
    Reconstruit tout l'historique Zeus à partir de la table resultats.
    Utilisé en fin de saison pour consolider la mémoire avant le reset.
    """
    logger.info("Starting Zeus History Reconstruction...")
    print("[ZEUS] Reconstruction de la mémoire (Histoire)...")
    
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Récupérer TOUS les résultats ordonnés
            cursor.execute("SELECT journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext FROM resultats WHERE score_dom IS NOT NULL ORDER BY journee ASC")
            matchs = cursor.fetchall()
            
            if not matchs:
                logger.warning("Aucun match trouvé pour reconstruction.")
                return 0

            # 2. Rejouer la saison match par match
            teams = {}
            from collections import defaultdict
            matchs_par_journee = defaultdict(list)
            for m in matchs:
                matchs_par_journee[m[0]].append(m)
                
            sorted_journees = sorted(matchs_par_journee.keys())
            count_total = 0
            
            for journee in sorted_journees:
                for _, d_id, e_id, s_d, s_e in matchs_par_journee[journee]:
                    if d_id not in teams: teams[d_id] = {'pts': 0, 'bp': 0, 'bc': 0, 'forme': []}
                    if e_id not in teams: teams[e_id] = {'pts': 0, 'bp': 0, 'bc': 0, 'forme': []}
                    
                    teams[d_id]['bp'] += s_d
                    teams[d_id]['bc'] += s_e
                    teams[e_id]['bp'] += s_e
                    teams[e_id]['bc'] += s_d
                    
                    p_d, p_e = calculate_points(s_d, s_e)
                    teams[d_id]['pts'] += p_d
                    teams[e_id]['pts'] += p_e
                    
                    res_d = 'V' if s_d > s_e else ('N' if s_d == s_e else 'D')
                    res_e = 'V' if s_e > s_d else ('N' if s_e == s_d else 'D')
                    teams[d_id]['forme'].append(res_d)
                    teams[e_id]['forme'].append(res_e)
                
                # Snapshot
                sorted_teams = sorted(teams.items(), key=lambda x: (x[1]['pts'], x[1]['bp'] - x[1]['bc'], x[1]['bp']), reverse=True)
                
                for position, (tid, stats) in enumerate(sorted_teams, 1):
                    forme_str = "".join(stats['forme'][-5:])
                    cursor.execute("""
                        INSERT OR REPLACE INTO zeus_classement_archive 
                        (journee, equipe_id, position, points, forme, buts_pour, buts_contre, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (journee, tid, position, stats['pts'], forme_str, stats['bp'], stats['bc'], datetime.now().isoformat()))
                    count_total += 1
            
            conn.commit()
            logger.info(f"Reconstruction terminée ({count_total} entrées).")
            print(f"[ZEUS] Mémoire consolidée : {count_total} snapshots créés.")
            return count_total
            
    except Exception as e:
        logger.error(f"Erreur reconstruction historique: {e}")
        return 0


if __name__ == "__main__":
    # Test des fonctions
    print("Test du gestionnaire d'archive ZEUS")
    
    # Test snapshot
    derniere_journee = get_derniere_journee_archivee()
    print(f"Dernière journée archivée: {derniere_journee}")
    
    # Liste des journées
    journees = lister_journees_archivees()
    print(f"Journées archivées: {journees}")
