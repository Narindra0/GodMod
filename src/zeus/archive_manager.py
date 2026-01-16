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

def nettoyer_anciennes_archives(journees_a_garder=10):
    """
    Nettoie les anciennes archives pour garder l'espace de stockage gérable.
    
    Args:
        journees_a_garder (int): Nombre de journées récentes à conserver
    """
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Trouver la journée limite à garder
            cursor.execute("""
                SELECT MAX(journee) FROM zeus_classement_archive
            """)
            max_journee = cursor.fetchone()[0] or 0
            
            if max_journee <= journees_a_garder:
                logger.info("Pas assez d'archives pour nettoyer")
                return
            
            journee_limite = max_journee - journees_a_garder
            
            # Supprimer les anciennes archives
            cursor.execute("""
                DELETE FROM zeus_classement_archive 
                WHERE journee < ?
            """, (journee_limite,))
            
            deleted = cursor.rowcount
            logger.info(f"🧹 Nettoyage: {deleted} archives supprimées (J<{journee_limite})")
            
    except Exception as e:
        logger.error(f"Erreur nettoyage archives: {e}")

if __name__ == "__main__":
    # Test des fonctions
    print("Test du gestionnaire d'archive ZEUS")
    
    # Test snapshot
    derniere_journee = get_derniere_journee_archivee()
    print(f"Dernière journée archivée: {derniere_journee}")
    
    # Liste des journées
    journees = lister_journees_archivees()
    print(f"Journées archivées: {journees}")
