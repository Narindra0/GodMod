"""
Script pour créer les archives initiales de ZEUS
Récupère le classement actuel et crée des snapshots pour les journées passées
"""

import logging
from src.core import database
from src.zeus.archive_manager import prendre_snapshot_classement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def creer_archives_initiales():
    """Crée les archives manquantes pour les journées passées"""
    
    # Récupérer les journées réellement disponibles dans les cotes
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT journee FROM cotes ORDER BY journee DESC")
        journees_disponibles = [row[0] for row in cursor.fetchall()]
    
    print(f"📸 Journées disponibles dans cotes : {journees_disponibles}")
    print("Création des archives initiales pour ZEUS...")
    
    for journee in journees_disponibles:
        try:
            # Créer le snapshot (utilisera le classement si disponible)
            archived = prendre_snapshot_classement(journee)
            if archived > 0:
                print(f"✅ J{journee}: {archived} équipes archivées")
            else:
                print(f"⚠️  J{journee}: Aucun classement à archiver")
                    
        except Exception as e:
            print(f"❌ Erreur J{journee}: {e}")
    
    print("\n🎉 Archives initiales créées !")
    
    # Vérification
    from src.zeus.archive_manager import lister_journees_archivees
    journees_archivees = lister_journees_archivees()
    print(f"📚 Journées maintenant archivées : {journees_archivees}")

if __name__ == "__main__":
    creer_archives_initiales()
