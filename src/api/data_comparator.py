"""
Module de comparaison des donnees entre API et Scraper
Detecte les ecarts et genere des rapports

Version: 2.1
Date: Janvier 2025
"""

import logging
from typing import List, Dict, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# ==================== COMPARAISON CLASSEMENT ====================

def compare_rankings(api_data: List[Dict], scraper_data: List[Dict]) -> Dict:
    """
    Compare les classements de l'API et du Scraper
    
    Args:
        api_data: Donnees de classement depuis l'API
        scraper_data: Donnees de classement depuis le Scraper
        
    Returns:
        Dictionnaire avec statistiques de comparaison
    """
    if not api_data or not scraper_data:
        return {"coherence": 0.0, "differences": [], "error": "Donnees manquantes"}
    
    differences = []
    total_teams = len(api_data)
    matching = 0
    
    # Creer des dictionnaires pour faciliter la comparaison
    api_dict = {team["name"]: team for team in api_data}
    scraper_dict = {team.get("name", team.get("nom", "")): team for team in scraper_data}
    
    for team_name, api_team in api_dict.items():
        if team_name in scraper_dict:
            scraper_team = scraper_dict[team_name]
            
            # Comparer les points
            api_points = api_team.get("points")
            scraper_points = scraper_team.get("points")
            
            if api_points == scraper_points:
                matching += 1
            else:
                differences.append({
                    "team": team_name,
                    "field": "points",
                    "api": api_points,
                    "scraper": scraper_points
                })
        else:
            differences.append({
                "team": team_name,
                "field": "existence",
                "api": "present",
                "scraper": "absent"
            })
    
    coherence = (matching / total_teams * 100) if total_teams > 0 else 0
    
    return {
        "coherence": round(coherence, 2),
        "total_teams": total_teams,
        "matching": matching,
        "differences_count": len(differences),
        "differences": differences[:10]  # Limiter a 10 pour la lisibilite
    }


# ==================== COMPARAISON RESULTATS ====================

def compare_results(api_data: List[Dict], scraper_data: List[Dict]) -> Dict:
    """
    Compare les resultats de matchs entre API et Scraper
    
    Args:
        api_data: Resultats depuis l'API (filtre)
        scraper_data: Resultats depuis le Scraper
        
    Returns:
        Dictionnaire avec statistiques de comparaison
    """
    if not api_data or not scraper_data:
        return {"coherence": 0.0, "differences": [], "error": "Donnees manquantes"}
    
    differences = []
    total_matches = 0
    matching = 0
    
    for api_round in api_data:
        journee = api_round.get("roundNumber")
        
        # Trouver la journee correspondante dans scraper_data
        scraper_round = next((r for r in scraper_data if r.get("journee") == journee), None)
        
        if not scraper_round:
            continue
        
        for api_match in api_round.get("matches", []):
            total_matches += 1
            
            home = api_match.get("homeTeam")
            away = api_match.get("awayTeam")
            api_score = api_match.get("score")
            
            # Chercher le match correspondant dans scraper
            scraper_match = next(
                (m for m in scraper_round.get("matches", [])
                 if m.get("homeTeam") == home and m.get("awayTeam") == away),
                None
            )
            
            if scraper_match:
                scraper_score = scraper_match.get("score")
                
                if api_score == scraper_score:
                    matching += 1
                else:
                    differences.append({
                        "journee": journee,
                        "match": f"{home} vs {away}",
                        "api_score": api_score,
                        "scraper_score": scraper_score
                    })
            else:
                differences.append({
                    "journee": journee,
                    "match": f"{home} vs {away}",
                    "api_score": api_score,
                    "scraper_score": "NOT_FOUND"
                })
    
    coherence = (matching / total_matches * 100) if total_matches > 0 else 0
    
    return {
        "coherence": round(coherence, 2),
        "total_matches": total_matches,
        "matching": matching,
        "differences_count": len(differences),
        "differences": differences[:10]
    }


# ==================== COMPARAISON COTES ====================

def compare_odds(api_data: List[Dict], scraper_data: List[Dict]) -> Dict:
    """
    Compare les cotes entre API et Scraper
    
    Args:
        api_data: Matchs a venir depuis l'API (filtre)
        scraper_data: Cotes depuis le Scraper
        
    Returns:
        Dictionnaire avec statistiques de comparaison
    """
    if not api_data or not scraper_data:
        return {"coherence": 0.0, "differences": [], "error": "Donnees manquantes"}
    
    differences = []
    total_matches = 0
    matching = 0
    
    for api_round in api_data:
        for api_match in api_round.get("matches", []):
            total_matches += 1
            
            home = api_match.get("homeTeam")
            away = api_match.get("awayTeam")
            api_odds = api_match.get("odds", [])
            
            # Extraire les cotes API
            api_1 = next((o["odds"] for o in api_odds if o["type"] == "1"), None)
            api_x = next((o["odds"] for o in api_odds if o["type"] == "X"), None)
            api_2 = next((o["odds"] for o in api_odds if o["type"] == "2"), None)
            
            # Chercher dans scraper_data
            scraper_match = next(
                (m for m in scraper_data
                 if m.get("homeTeam") == home and m.get("awayTeam") == away),
                None
            )
            
            if scraper_match:
                scraper_1 = scraper_match.get("cote_1")
                scraper_x = scraper_match.get("cote_x")
                scraper_2 = scraper_match.get("cote_2")
                
                # Tolerance de 0.01 pour les differences de cotes
                tolerance = 0.01
                if (abs(api_1 - scraper_1) < tolerance and
                    abs(api_x - scraper_x) < tolerance and
                    abs(api_2 - scraper_2) < tolerance):
                    matching += 1
                else:
                    differences.append({
                        "match": f"{home} vs {away}",
                        "api": f"1={api_1}, X={api_x}, 2={api_2}",
                        "scraper": f"1={scraper_1}, X={scraper_x}, 2={scraper_2}"
                    })
            else:
                differences.append({
                    "match": f"{home} vs {away}",
                    "api": f"1={api_1}, X={api_x}, 2={api_2}",
                    "scraper": "NOT_FOUND"
                })
    
    coherence = (matching / total_matches * 100) if total_matches > 0 else 0
    
    return {
        "coherence": round(coherence, 2),
        "total_matches": total_matches,
        "matching": matching,
        "differences_count": len(differences),
        "differences": differences[:10]
    }


# ==================== RAPPORT GLOBAL ====================

def generate_comparison_report(ranking_comp: Dict, results_comp: Dict, odds_comp: Dict) -> str:
    """
    Genere un rapport complet de comparaison
    
    Args:
        ranking_comp: Comparaison classement
        results_comp: Comparaison resultats
        odds_comp: Comparaison cotes
        
    Returns:
        Rapport formate en texte
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""
{'='*60}
RAPPORT DE COMPARAISON API vs SCRAPER
Date: {timestamp}
{'='*60}

[CLASSEMENT]
  Coherence: {ranking_comp.get('coherence', 0)}%
  Equipes: {ranking_comp.get('matching', 0)}/{ranking_comp.get('total_teams', 0)}
  Differences: {ranking_comp.get('differences_count', 0)}

[RESULTATS]
  Coherence: {results_comp.get('coherence', 0)}%
  Matchs: {results_comp.get('matching', 0)}/{results_comp.get('total_matches', 0)}
  Differences: {results_comp.get('differences_count', 0)}

[COTES]
  Coherence: {odds_comp.get('coherence', 0)}%
  Matchs: {odds_comp.get('matching', 0)}/{odds_comp.get('total_matches', 0)}
  Differences: {odds_comp.get('differences_count', 0)}

[COHERENCE GLOBALE]
  Moyenne: {((ranking_comp.get('coherence', 0) + results_comp.get('coherence', 0) + odds_comp.get('coherence', 0)) / 3):.2f}%

{'='*60}
"""
    
    # Ajouter les differences si elles existent
    if ranking_comp.get('differences'):
        report += "\n[DETAILS - CLASSEMENT]\n"
        for diff in ranking_comp['differences'][:5]:
            report += f"  {diff}\n"
    
    if results_comp.get('differences'):
        report += "\n[DETAILS - RESULTATS]\n"
        for diff in results_comp['differences'][:5]:
            report += f"  {diff}\n"
    
    if odds_comp.get('differences'):
        report += "\n[DETAILS - COTES]\n"
        for diff in odds_comp['differences'][:5]:
            report += f"  {diff}\n"
    
    return report


def save_comparison_log(report: str, filepath: str = "logs/dual_mode_comparison.log"):
    """
    Sauvegarde le rapport dans un fichier log
    
    Args:
        report: Rapport a sauvegarder
        filepath: Chemin du fichier log
    """
    import os
    
    # Creer le dossier logs si necessaire
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(report)
        f.write("\n\n")
    
    logger.info(f"Rapport sauvegarde dans {filepath}")


# ==================== TEST ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("[TEST] Module Data Comparator")
    print("=" * 60)
    
    # Donnees de test
    api_ranking = [
        {"name": "Manchester Blue", "points": 43, "position": 1},
        {"name": "Newcastle", "points": 41, "position": 2}
    ]
    
    scraper_ranking = [
        {"name": "Manchester Blue", "points": 43, "position": 1},
        {"name": "Newcastle", "points": 41, "position": 2}
    ]
    
    # Test comparaison
    result = compare_rankings(api_ranking, scraper_ranking)
    print(f"\n[TEST] Comparaison classement:")
    print(f"  Coherence: {result['coherence']}%")
    print(f"  Matching: {result['matching']}/{result['total_teams']}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Test termine")
