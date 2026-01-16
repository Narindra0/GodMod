"""
Module de collecte double source (API + Scraper)
Collecte les donnees simultanement depuis l'API et le Scraper HTML
Compare les resultats et genere des rapports

Version: 2.1 - Phase 4
Date: Janvier 2025
"""

import logging
import sys
import os
from typing import Dict, Tuple

# Ajouter le chemin du projet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.api.api_client import get_ranking, get_recent_results, get_upcoming_matches
from src.api.results_filter import extract_results_minimal
from src.api.matches_filter import extract_matches_with_local_ids
from src.api.db_integration import insert_api_ranking, insert_api_results, insert_api_matches
from src.api.data_comparator import (
    compare_rankings, compare_results, compare_odds,
    generate_comparison_report, save_comparison_log
)

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

DUAL_MODE_CONFIG = {
    "enabled": True,
    "log_file": "logs/dual_mode_comparison.log",
    "coherence_threshold": 90.0,  # Seuil d'alerte si coherence < 90%
}

# ==================== COLLECTE DOUBLE SOURCE ====================

def fetch_dual_ranking() -> Tuple[Dict, Dict]:
    """
    Collecte le classement depuis API ET Scraper
    
    Returns:
        Tuple (api_data, scraper_data, comparison_result)
    """
    logger.info("[DUAL MODE] Collecte du classement...")
    
    # 1. Collecte API
    api_data = get_ranking()
    logger.info(f"[API] {len(api_data)} equipes recuperees")
    
    # 2. Collecte Scraper (simule pour le moment)
    # TODO: Integrer avec le vrai scraper quand disponible
    scraper_data = []  # Placeholder
    logger.info(f"[SCRAPER] {len(scraper_data)} equipes recuperees")
    
    # 3. Comparaison
    comparison = compare_rankings(api_data, scraper_data) if scraper_data else None
    
    # 4. Insertion API (priorite pour Phase 4)
    if api_data:
        count = insert_api_ranking(api_data)
        logger.info(f"[DB] {count} equipes inserees depuis API")
    
    return {
        "api": api_data,
        "scraper": scraper_data,
        "comparison": comparison
    }


def fetch_dual_results(take: int = 3) -> Dict:
    """
    Collecte les resultats depuis API ET Scraper
    
    Args:
        take: Nombre de journees a recuperer
        
    Returns:
        Dictionnaire avec donnees API, Scraper et comparaison
    """
    logger.info("[DUAL MODE] Collecte des resultats...")
    
    # 1. Collecte API
    api_raw = get_recent_results(take=take)
    api_data = extract_results_minimal(api_raw)
    logger.info(f"[API] {len(api_data)} journees recuperees")
    
    # 2. Collecte Scraper (simule)
    scraper_data = []  # Placeholder
    logger.info(f"[SCRAPER] {len(scraper_data)} journees recuperees")
    
    # 3. Comparaison
    comparison = compare_results(api_data, scraper_data) if scraper_data else None
    
    # 4. Insertion API
    if api_data:
        count = insert_api_results(api_data)
        logger.info(f"[DB] {count} resultats inseres depuis API")
    
    return {
        "api": api_data,
        "scraper": scraper_data,
        "comparison": comparison
    }


def fetch_dual_matches(limit: int = 1) -> Dict:
    """
    Collecte les matchs a venir depuis API ET Scraper
    
    Args:
        limit: Nombre de journees a recuperer
        
    Returns:
        Dictionnaire avec donnees API, Scraper et comparaison
    """
    logger.info("[DUAL MODE] Collecte des matchs a venir...")
    
    # 1. Collecte API
    api_raw = get_upcoming_matches()
    api_data = extract_matches_with_local_ids(api_raw, limit=limit)
    logger.info(f"[API] {len(api_data)} journees recuperees")
    
    # 2. Collecte Scraper (simule)
    scraper_data = []  # Placeholder
    logger.info(f"[SCRAPER] {len(scraper_data)} matchs recuperes")
    
    # 3. Comparaison
    comparison = compare_odds(api_data, scraper_data) if scraper_data else None
    
    # 4. Insertion API
    if api_data:
        count = insert_api_matches(api_data)
        logger.info(f"[DB] {count} matchs inseres depuis API")
    
    return {
        "api": api_data,
        "scraper": scraper_data,
        "comparison": comparison
    }


# ==================== COLLECTE COMPLETE ====================

def fetch_all_dual() -> Dict:
    """
    Collecte complete en mode dual (classement + resultats + matchs)
    
    Returns:
        Dictionnaire avec toutes les donnees et comparaisons
    """
    logger.info("=" * 60)
    logger.info("[DUAL MODE] Demarrage collecte complete")
    logger.info("=" * 60)
    
    # Collecte
    ranking_data = fetch_dual_ranking()
    results_data = fetch_dual_results(take=3)
    matches_data = fetch_dual_matches(limit=2)
    
    # Generer rapport global si comparaisons disponibles
    if ranking_data["comparison"] and results_data["comparison"] and matches_data["comparison"]:
        report = generate_comparison_report(
            ranking_data["comparison"],
            results_data["comparison"],
            matches_data["comparison"]
        )
        
        print(report)
        save_comparison_log(report, DUAL_MODE_CONFIG["log_file"])
        
        # Verifier coherence
        avg_coherence = (
            ranking_data["comparison"]["coherence"] +
            results_data["comparison"]["coherence"] +
            matches_data["comparison"]["coherence"]
        ) / 3
        
        if avg_coherence < DUAL_MODE_CONFIG["coherence_threshold"]:
            logger.warning(f"[ALERTE] Coherence globale faible: {avg_coherence:.2f}%")
    
    logger.info("=" * 60)
    logger.info("[DUAL MODE] Collecte terminee")
    logger.info("=" * 60)
    
    return {
        "ranking": ranking_data,
        "results": results_data,
        "matches": matches_data
    }


# ==================== TEST ====================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("[TEST] Module Dual Fetcher")
    print("=" * 60)
    print("\nMode DUAL active: API uniquement pour le moment")
    print("(Le scraper sera integre dans une prochaine etape)\n")
    
    # Test de collecte complete
    result = fetch_all_dual()
    
    print("\n[RESULTAT]")
    print(f"  Classement API: {len(result['ranking']['api'])} equipes")
    print(f"  Resultats API: {len(result['results']['api'])} journees")
    print(f"  Matchs API: {len(result['matches']['api'])} journees")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Test termine")
    print(f"Logs disponibles dans: {DUAL_MODE_CONFIG['log_file']}")
