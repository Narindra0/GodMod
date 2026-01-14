import time
import re
import sqlite3
from . import config

# Cache global pour les IDs d'équipes {nom: id}
_EQUIPE_ID_CACHE = {}

def get_equipe_id(nom, conn=None):
    """Récupère l'ID d'une équipe par son nom, utilise le cache."""
    global _EQUIPE_ID_CACHE
    if nom in _EQUIPE_ID_CACHE:
        return _EQUIPE_ID_CACHE[nom]
    
    if conn is None:
        from .database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM equipes WHERE nom = ?", (nom,))
            res = cursor.fetchone()
            
            if res:
                _EQUIPE_ID_CACHE[nom] = res[0]
                return res[0]
            return None
    else:
        # Utilisation de la connexion fournie
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM equipes WHERE nom = ?", (nom,))
        res = cursor.fetchone()
        
        if res:
            _EQUIPE_ID_CACHE[nom] = res[0]
            return res[0]
        return None

def invalidate_equipe_cache():
    """Invalide le cache des équipes (utile après modifications)."""
    global _EQUIPE_ID_CACHE
    _EQUIPE_ID_CACHE.clear()

def init_persistent_browser(p, max_retries=3):
    """
    Initialise un navigateur persistant avec 3 onglets parallèles.
    Retry automatique en cas d'erreur réseau.
    
    Args:
        p: Instance playwright
        max_retries: Nombre maximum de tentatives (défaut: 3)
    
    Returns:
        Tuple (browser, page_matches, page_results, page_ranking)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Initialisation du navigateur (tentative {attempt}/{max_retries})...")
            browser = p.chromium.launch(headless=config.HEADLESS)
            context = browser.new_context()
            
            page_matches = context.new_page()
            page_results = context.new_page()
            page_ranking = context.new_page()
            
            print("Chargement des pages initiales...")
            page_matches.goto(config.URL_MATCHS, wait_until="domcontentloaded", timeout=config.TIMEOUT)
            page_results.goto(config.URL_RESULTATS, wait_until="domcontentloaded", timeout=config.TIMEOUT)
            page_ranking.goto(config.URL_CLASSEMENT, wait_until="domcontentloaded", timeout=config.TIMEOUT)
            
            print("Attente du rendu JavaScript...")
            time.sleep(5)
            
            print("✅ Navigateur initialisé avec succès")
            return browser, page_matches, page_results, page_ranking
            
        except Exception as e:
            logger.warning(f"Tentative {attempt}/{max_retries} échouée : {e}")
            print(f"⚠️ Tentative {attempt}/{max_retries} échouée : {e}")
            
            if attempt == max_retries:
                logger.error("Échec de l'initialisation du navigateur après toutes les tentatives")
                raise
            
            # Attente progressive : 5s, 10s, 15s
            wait_time = 5 * attempt
            print(f"⏳ Nouvelle tentative dans {wait_time}s...")
            time.sleep(wait_time)

def extraire_texte_si_present(element, selector):
    """Extrait le texte d'un élément si le sélecteur est présent."""
    target = element.query_selector(selector)
    return target.inner_text().strip() if target else ""

def get_journee_from_page(page):
    """Détecte la journée sur une page via locator (méthode robuste)."""
    try:
        # On essaie plusieurs sélecteurs/patterns
        patterns = [
            "text=/Journée \\d+/",  # Standard
            "text=/Journee \\d+/",  # Sans accent
            "text=/Journées \\d+/"  # Pluriel
        ]
        
        for p in patterns:
            loc = page.locator(p).first
            if loc.count() > 0:
                journee_text = loc.inner_text(timeout=2000)
                # Regex flexible : Journe(e|é)(s)? + Espace + Chiffres
                match_j = re.search(r"Journ[eé]es?\s+(\d+)", journee_text, re.IGNORECASE)
                if match_j:
                    return int(match_j.group(1))
    except:
        pass
    return 0

def wait_for_valid_cycle(page_matches, page_results, page_ranking=None, timeout=600):
    """
    Surveille la page Matchs pour détecter le bon moment pour scraper.
    Règles strictes :
    1. Si LIVE < 80' : check toutes les 6s.
    2. Si LIVE >= 80' : check toutes les 5s.
    3. Si Timer présent et entre 01:03 et 00:45 ET nouvelle journée détectée sur le site : on scrap.
    
    Args:
        timeout: Timeout en secondes (défaut: 600 = 10 minutes)
    """
    import time as time_module
    print("Surveillance du cycle (Synchronisation par Timer, LIVE & Sequence)...")
    
    start_time = time_module.time()
    while True:
        # Vérification du timeout
        if time_module.time() - start_time > timeout:
            raise TimeoutError(f"Timeout ({timeout}s) lors de l'attente du cycle valide")
        try:
            content = page_matches.evaluate("() => document.body.innerText")
            
            # --- 1. DÉTECTION DU LIVE ---
            match_live = re.search(r"Live\s+(\d+)'", content)
            if match_live:
                minute = int(match_live.group(1))
                if minute >= 85:
                    print(f"LIVE en cours ({minute}'). Fin imminente... Préparation du rafraîchissement.")
                    time.sleep(14)
                    print("🔄 Actualisation des pages Résultats et Classement...")
                    page_results.reload(wait_until="domcontentloaded")
                    if page_ranking:
                        page_ranking.reload(wait_until="domcontentloaded")
                    time.sleep(3)
                elif minute >= 80:
                    print(f"LIVE en cours ({minute}'). Fin proche... Mode reactif (5s).")
                    time.sleep(5)
                else:
                    print(f"LIVE en cours ({minute}'). On attend (6s).")
                    time.sleep(6)
                continue

            # --- 2. DÉTECTION DU TIMER ---
            match_timer = re.search(r"(\d{2}:\d{2})", content)
            if match_timer:
                timer_text = match_timer.group(1)
                m, s = map(int, timer_text.split(":"))
                total_sec = m * 60 + s
                
                # Détection (informative seulement maintenant)
                journee_site = get_journee_from_page(page_matches)
                
                # On regarde la dernière journée en DB (pour info)
                try:
                    from .database import get_db_connection
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT MAX(journee) FROM resultats")
                        derniere_j_db = cursor.fetchone()[0] or 0
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Erreur lors de la récupération de la journée : {e}")
                    derniere_j_db = 0
                
                if 45 <= total_sec <= 63: # Fenêtre 01:03 - 00:45
                    # LOGIQUE SIMPLIFIÉE : Si on est dans la fenêtre de tir, ON SCRAPE.
                    # On ne bloque plus si le site n'affiche pas encore la nouvelle journée,
                    # car le scraper complet (scraper_results) le gérera mieux.
                    
                    print(f"✅ Conditions remplies : Timer {timer_text} (Fenêtre de tir).")
                    print(f"ℹ️ Infos : Site J{journee_site}, DB J{derniere_j_db}")
                    print("⏳ Attente de 1 seconde pour assurer la cohérence des données...")
                    time.sleep(1)
                    
                    print("🔄 Actualisation des pages avant scraping...")
                    page_results.reload(wait_until="domcontentloaded")
                    if page_ranking:
                        page_ranking.reload(wait_until="domcontentloaded")
                    time.sleep(0.5) # Petit temps de stabilisation
                    
                    print(f"✅ Lancement du scraping (J{max(journee_site, derniere_j_db + 1)}) !")
                    return True
                    
                elif total_sec <= 300:
                    journee_display = journee_site if journee_site > 0 else "?"
                    print(f"⏳ Timer ({timer_text})... Site: J{journee_display}, DB: J{derniere_j_db}. Attente fenêtre (01:03-00:45).")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur lors de la surveillance : {e}")
            print(f"Erreur lors de la surveillance : {e}")
            
        time.sleep(2)

def fermer_popups(page):
    """Ferme les popups ou publicités éventuelles sur le site."""
    # 1. Bannière de cookies (Priorité)
    try:
        cookie_btn = page.get_by_role("button", name="Autoriser tous les cookies")
        if cookie_btn.is_visible(timeout=2000):
            cookie_btn.click()
            print("🍪 Banniere cookies acceptee.")
            time.sleep(1)
    except:
        pass

    # 2. Popups classiques
    popups = [
        "button.close", ".modal-close", ".close-button", 
        "button[aria-label='Close']", ".hg-close", ".qa-close-icon"
    ]
    for selector in popups:
        try:
            loc = page.locator(selector)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click()
                print(f"Popup ferme : {selector}")
                time.sleep(1)
        except:
            continue

def _update_config_flag(flag_name, new_value):
    """
    Fonction générique pour mettre à jour un flag dans config.py.
    
    Args:
        flag_name: Nom du flag à mettre à jour (ex: "USE_INTELLIGENCE_AMELIOREE")
        new_value: Nouvelle valeur (True/False)
    
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    import os
    
    # Chemin vers config.py
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    
    try:
        # Lire le fichier
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Trouver et remplacer la ligne
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(flag_name):
                # Remplacer la ligne en conservant les commentaires si présents
                lines[i] = f"{flag_name} = {new_value}\n"
                updated = True
                break
        
        if not updated:
            # Si la ligne n'existe pas, l'ajouter avant les sélecteurs CSS
            for i, line in enumerate(lines):
                if line.strip().startswith("# Sélecteurs CSS"):
                    lines.insert(i, f"{flag_name} = {new_value}\n")
                    updated = True
                    break
        
        if updated:
            # Réécrire le fichier
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Recharger le module config pour que les changements soient pris en compte
            import importlib
            import sys
            if 'src.core.config' in sys.modules:
                importlib.reload(sys.modules['src.core.config'])
            
            return True
        else:
            return False
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la mise à jour du flag {flag_name} : {e}", exc_info=True)
        return False

def update_intelligence_flag(new_value):
    """
    Met à jour le flag USE_INTELLIGENCE_AMELIOREE dans config.py.
    
    Args:
        new_value: True pour activer l'intelligence améliorée, False pour la désactiver
    
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    return _update_config_flag("USE_INTELLIGENCE_AMELIOREE", new_value)

def update_selection_flag(new_value):
    """
    Met à jour le flag USE_SELECTION_AMELIOREE dans config.py (Phase 3).
    
    Args:
        new_value: True pour activer la sélection améliorée (Phase 3), False pour Phase 2
    
    Returns:
        True si la mise à jour a réussi, False sinon
    """
    return _update_config_flag("USE_SELECTION_AMELIOREE", new_value)

def update_global_intelligence_flags(new_value):
    """
    Met à jour simultanément les flags USE_INTELLIGENCE_AMELIOREE et USE_SELECTION_AMELIOREE dans config.py.
    
    Args:
        new_value: True pour activer tout le système d'intelligence, False pour le mode simple.
    
    Returns:
        True si la mise à jour a réussi, False sinon.
    """
    # On met à jour les deux flags séquentiellement
    # Note: On pourrait optimiser pour faire une seule écriture, mais _update_config_flag est déjà implémentée.
    # On va faire une implémentation optimisée locale pour éviter deux écritures fichiers.
    import os
    
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        updated_count = 0
        flags_to_update = ["USE_INTELLIGENCE_AMELIOREE", "USE_SELECTION_AMELIOREE"]
        
        for i, line in enumerate(lines):
            line_strip = line.strip()
            for flag in flags_to_update:
                if line_strip.startswith(flag):
                    lines[i] = f"{flag} = {new_value}\n"
                    updated_count += 1
        
        # Si on a trouvé au moins un flag, on réécrit
        if updated_count > 0:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Recharger le module config
            import importlib
            import sys
            if 'src.core.config' in sys.modules:
                importlib.reload(sys.modules['src.core.config'])
                
            return True
        return False
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur lors de la mise à jour globale des flags : {e}", exc_info=True)
        return False