import sqlite3
import os
import sys
import logging

# Ajouter le dossier parent au path pour importer les modules du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import config, database

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_to_turso():
    """
    Migre les données de la base SQLite locale vers Turso.
    """
    if not config.TURSO_URL or not config.TURSO_TOKEN:
        logger.error("TURSO_URL et TURSO_TOKEN doivent être définis dans les variables d'environnement.")
        print("\nERREUR : Variables d'environnement manquantes.")
        print("Assurez-vous d'avoir TURSO_URL (ex: libsql://...) et TURSO_TOKEN.")
        return

    local_db_path = config.DB_NAME
    if not os.path.exists(local_db_path):
        logger.error(f"Base de données locale non trouvée : {local_db_path}")
        return

    logger.info("Début de la migration vers Turso...")
    
    # 1. Initialiser la structure sur Turso (si nécessaire)
    logger.info("Initialisation de la structure sur Turso...")
    database.initialiser_db()

    # 2. Se connecter aux deux bases
    try:
        # Note: database.get_db_connection() utilisera Turso si les variables sont là
        # On a besoin d'une connexion locale explicite
        local_conn = sqlite3.connect(local_db_path)
        local_conn.row_factory = sqlite3.Row
        local_cursor = local_conn.cursor()

        # On utilise libsql directement pour la destination
        import libsql
        remote_conn = libsql.connect(config.TURSO_URL, auth_token=config.TURSO_TOKEN)
        remote_cursor = remote_conn.cursor()

        tables = [
            "equipes", "resultats", "cotes", "classement", 
            "predictions", "score_ia", "zeus_predictions", "zeus_classement_archive"
        ]

        for table in tables:
            logger.info(f"Migration de la table : {table}...")
            
            # Lire les données locales
            local_cursor.execute(f"SELECT * FROM {table}")
            rows = local_cursor.fetchall()
            
            if not rows:
                logger.info(f"Table {table} vide, passage à la suivante.")
                continue

            # Préparer l'insertion sur Turso
            columns = rows[0].keys()
            placeholders = ", ".join(["?"] * len(columns))
            cols_str = ", ".join(columns)
            
            # Nettoyer la table destination avant (optionnel, mais plus sûr pour une fresh migration)
            # remote_cursor.execute(f"DELETE FROM {table}")
            
            # Insérer par lots
            insert_sql = f"INSERT OR IGNORE INTO {table} ({cols_str}) VALUES ({placeholders})"
            
            data_to_insert = [tuple(row) for row in rows]
            remote_cursor.executemany(insert_sql, data_to_insert)
            
            remote_conn.commit()
            logger.info(f"Table {table} : {len(rows)} lignes migrées.")

        logger.info("Migration terminée avec succès !")
        print("\nFélicitations ! Vos données sont maintenant sur Turso.")

    except Exception as e:
        logger.error(f"Erreur durant la migration : {e}", exc_info=True)
    finally:
        if 'local_conn' in locals(): local_conn.close()
        if 'remote_conn' in locals(): remote_conn.close()

if __name__ == "__main__":
    migrate_to_turso()
