import os

# URLs de base (extraites du README)
URL_RESULTATS = "https://bet261.mg/virtual/category/instant-league/8035/results"
URL_MATCHS = "https://bet261.mg/virtual/category/instant-league/8035/matches"
URL_CLASSEMENT = "https://bet261.mg/virtual/category/instant-league/8035/ranking"

# Configuration de la base de données
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "godmod_v2.db")
TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")

# Équipes de la English Virtual League (20)
EQUIPES = [
    "London Reds", "Manchester Blue", "Manchester Red", "Wolverhampton", "N. Forest",
    "Fulham", "West Ham", "Spurs", "London Blues", "Brighton",
    "Brentford", "Everton", "Aston Villa", "Leeds", "Sunderland",
    "Crystal Palace", "Liverpool", "Newcastle", "Burnley", "Bournemouth"
]

# Alias pour normaliser les noms d'équipes (Site -> DB)
TEAM_ALIASES = {
    "A. Villa": "Aston Villa",
    "C. Palace": "Crystal Palace",
    "Man Blue": "Manchester Blue",
    "Man Red": "Manchester Red",
}

# Paramètres de prédiction
JOURNEE_DEPART_PREDICTION = 2
MAX_PREDICTIONS_PAR_JOURNEE = 3
POINTS_VICTOIRE = 5
POINTS_DEFAITE = -8

# ============================================
# CONFIGURATION DU SYSTÈME INTELLIGENT
# ============================================

# Mode d'intelligence activé par défaut au démarrage
# - False : Mode Normal (calcul simple : classement + forme)
# - True  : Mode Intelligent Multi-Facteurs (Phase 2 & 3)
USE_INTELLIGENCE_AMELIOREE = True

# Sélection améliorée (Phase 3 complète)
# - False : utilise selectionner_meilleurs_matchs() (Phase 2)
# - True  : utilise selectionner_meilleurs_matchs_ameliore() (Phase 3 - Recommandé)
#           Inclut : 7 facteurs, détection pièges, confrontations directes, momentum
USE_SELECTION_AMELIOREE = True

# Sélecteurs CSS pour les résultats
SELECTORS = {
    "result_container": ".result-container",
    "result_header": ".header",
    "result_row": ".row",
    "home_team": ".left-team.column .team span",
    "away_team": ".right-team.column .team span",
    "match_score": ".match-score",
    # Sélecteurs pour le classement
    "ranking_row": "hg-instant-league-ranking table tbody tr",
    "ranking_team": "td div.rank-name",
    "ranking_points": "td span.points",
    "ranking_form": "td ul li img",
    # Sélecteurs pour les cotes des matchs à venir
    "match_row_odds": "div.match.bet-type-1x2",
    "teams_container": ".teams",
    "odds_item": "hg-event-bet-type-item span.odds.no-label",
    "time_slot_active": "li.ng-star-inserted.active div",
    # Sélecteurs de synchronisation
    "live_indicator": "div:has-text('Live')",
    "results_section_title": "div:has-text('Résultats')",
    "timer_indicator": "text=/01:../"
}

# Configuration Playwright
HEADLESS = False  # Set to True for production
TIMEOUT = 60000  # 60 seconds
