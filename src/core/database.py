import sqlite3
import logging
import os
try:
    import libsql
    HAS_LIBSQL = True
except ImportError:
    HAS_LIBSQL = False
from contextlib import contextmanager
from . import config

# Configuration du logging
logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """
    Context manager pour les connexions DB.
    Gère automatiquement l'ouverture (SQLite ou libSQL), la configuration, le commit/rollback et la fermeture.
    """
    is_remote = config.TURSO_URL and config.TURSO_TOKEN
    
    if is_remote:
        if not HAS_LIBSQL:
            raise ImportError("La bibliothèque 'libsql' est requise pour se connecter à Turso. Installez-la avec 'pip install libsql'.")
        conn = libsql.connect(config.TURSO_URL, auth_token=config.TURSO_TOKEN)
    else:
        conn = sqlite3.connect(config.DB_NAME)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    
    conn.row_factory = sqlite3.Row if not is_remote else None # libSQL may handle rows differently but usually compatible
    
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erreur DB, rollback effectué: {e}", exc_info=True)
        raise
    finally:
        conn.close()

def initialiser_db():
    """Initialise la base de données avec une structure normalisée."""
    is_remote = config.TURSO_URL and config.TURSO_TOKEN
    
    if is_remote:
        conn = libsql.connect(config.TURSO_URL, auth_token=config.TURSO_TOKEN)
    else:
        conn = sqlite3.connect(config.DB_NAME)
    
    cursor = conn.cursor()
    
    if not is_remote:
        # Activation des clés étrangères pour SQLite uniquement
        cursor.execute("PRAGMA foreign_keys = ON")
    # 1. Table des équipes (Référence unique)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL
        )
    ''')
    # 2. Table des résultats (Matchs joués ET à venir)
    # MODIFICATION : On autorise NULL pour les scores (matchs non joués)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_dom_id INTEGER NOT NULL,
            equipe_ext_id INTEGER NOT NULL,
            score_dom INTEGER,  -- Peut être NULL avant le match
            score_ext INTEGER,  -- Peut être NULL avant le match
            FOREIGN KEY (equipe_dom_id) REFERENCES equipes(id),
            FOREIGN KEY (equipe_ext_id) REFERENCES equipes(id),
            UNIQUE(journee, equipe_dom_id, equipe_ext_id)
        )
    ''')
    # 3. Table des cotes (Liée au match)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_dom_id INTEGER NOT NULL,
            equipe_ext_id INTEGER NOT NULL,
            cote_1 DECIMAL(5,2),
            cote_x DECIMAL(5,2),
            cote_2 DECIMAL(5,2),
            FOREIGN KEY (equipe_dom_id) REFERENCES equipes(id),
            FOREIGN KEY (equipe_ext_id) REFERENCES equipes(id),
            UNIQUE(journee, equipe_dom_id, equipe_ext_id)
        )
    ''')
    # 4. Table du classement
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_id INTEGER NOT NULL,
            position INTEGER,
            points INTEGER NOT NULL,
            forme TEXT,
            FOREIGN KEY (equipe_id) REFERENCES equipes(id),
            UNIQUE(journee, equipe_id)
        )
    ''')
    # 5. Table des prédictions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_dom_id INTEGER NOT NULL,
            equipe_ext_id INTEGER NOT NULL,
            prediction TEXT NOT NULL,
            resultat TEXT,
            fiabilite DECIMAL(5,2),
            succes INTEGER, -- 1 (Vrai) ou 0 (Faux), NULL si pas encore joué
            points_gagnes INTEGER,
            FOREIGN KEY (equipe_dom_id) REFERENCES equipes(id),
            FOREIGN KEY (equipe_ext_id) REFERENCES equipes(id)
        )
    ''')
    # 6. Table des scores IA (Historique)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS score_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score DECIMAL(10,2) DEFAULT 100.00,
            predictions_total INTEGER DEFAULT 0,
            predictions_reussies INTEGER DEFAULT 0,
            pause_until INTEGER DEFAULT 0,
            session_archived INTEGER DEFAULT 0,
            derniere_maj TEXT
        )
    ''')
    
    # 7. Table des prédictions ZEUS (Shadow Mode)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zeus_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_dom_id INTEGER NOT NULL,
            equipe_ext_id INTEGER NOT NULL,
            prediction INTEGER NOT NULL, -- 0=1, 1=N, 2=2, 3=Skip
            confiance DECIMAL(5,2) DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipe_dom_id) REFERENCES equipes(id),
            FOREIGN KEY (equipe_ext_id) REFERENCES equipes(id),
            UNIQUE(journee, equipe_dom_id, equipe_ext_id)
        )
    ''')
    
    # 8. Table d'archive du classement pour ZEUS (Mémoire Photographique)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zeus_classement_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journee INTEGER NOT NULL,
            equipe_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            points INTEGER NOT NULL,
            forme TEXT,
            buts_pour DECIMAL(4,2) DEFAULT 0,
            buts_contre DECIMAL(4,2) DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (equipe_id) REFERENCES equipes(id),
            UNIQUE(journee, equipe_id)
        )
    ''')
    
    # --- IMPORTANT : Initialisation des données de base ---
    
    # 1. Insérer les équipes si elles n'existent pas
    cursor.executemany('INSERT OR IGNORE INTO equipes (nom) VALUES (?)', [(e,) for e in config.EQUIPES])
    
    # 2. Initialiser le score IA si la table est vide
    cursor.execute("SELECT COUNT(*) FROM score_ia")
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO score_ia (score, predictions_total, predictions_reussies, pause_until, session_archived, derniere_maj) VALUES (100, 0, 0, 0, 0, datetime("now"))')
    
    # 3. Création des index pour optimiser les performances
    logger.info("Création des index SQL...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_resultats_journee ON resultats(journee)",
        "CREATE INDEX IF NOT EXISTS idx_resultats_equipes ON resultats(equipe_dom_id, equipe_ext_id)",
        "CREATE INDEX IF NOT EXISTS idx_predictions_journee ON predictions(journee)",
        "CREATE INDEX IF NOT EXISTS idx_predictions_succes ON predictions(succes)",
        "CREATE INDEX IF NOT EXISTS idx_cotes_journee ON cotes(journee)",
        "CREATE INDEX IF NOT EXISTS idx_classement_equipe ON classement(equipe_id)",
        "CREATE INDEX IF NOT EXISTS idx_classement_journee ON classement(journee)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    conn.commit()
    conn.close()
    logger.info(f"{len(indexes)} index crees avec succes.")
    print(f"Base de donnees '{config.DB_NAME}' mise a jour (Structure v2 avec index optimises).")
if __name__ == "__main__":
    initialiser_db()