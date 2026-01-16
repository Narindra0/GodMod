import sqlite3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core import database
from src.core import config
from src.api.db_integration import insert_api_ranking

def test_goal_calculation():
    print("[TEST] Verifiant le calcul des buts...")
    
    # 1. Setup Test Data
    test_team_name = "TestTeamZeus"
    test_opponent = "OpponentZeus"
    
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create dummy teams
        cursor.execute("INSERT OR IGNORE INTO equipes (nom) VALUES (?)", (test_team_name,))
        cursor.execute("SELECT id FROM equipes WHERE nom = ?", (test_team_name,))
        team_id = cursor.fetchone()[0]
        
        cursor.execute("INSERT OR IGNORE INTO equipes (nom) VALUES (?)", (test_opponent,))
        cursor.execute("SELECT id FROM equipes WHERE nom = ?", (test_opponent,))
        opp_id = cursor.fetchone()[0]
        
        # Insert matches with goals
        # Match 1: TestTeam (Home) 2 - 1 Opponent (Away)
        cursor.execute("""
            INSERT OR REPLACE INTO resultats (journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext)
            VALUES (999, ?, ?, 2, 1)
        """, (team_id, opp_id))
        
        # Match 2: Opponent (Home) 0 - 3 TestTeam (Away)
        cursor.execute("""
            INSERT OR REPLACE INTO resultats (journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext)
            VALUES (1000, ?, ?, 0, 3)
        """, (opp_id, team_id))
        
        print(f"   [SETUP] Matchs inseres pour {test_team_name} (ID: {team_id})")
        print("   Attendu: Buts Pour = 2+3=5, Buts Contre = 1+0=1")

    # 2. Trigger insert_api_ranking (Simulate API update)
    # This should trigger the calculation logic we added
    dummy_ranking_data = [{
        'name': test_team_name,
        'position': 1,
        'points': 6,
        'history': ['Won', 'Won'],
        'won': 999, 'lost': 0, 'draw': 0 # Matches calculation sets journee = 999
    }]
    
    print("\n[ACTION] Execution insert_api_ranking...")
    insert_api_ranking(dummy_ranking_data)
    
    # 3. Verify 'classement' table
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM equipes WHERE nom = ?", (test_team_name,))
        team_id = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT buts_pour, buts_contre FROM classement 
            WHERE equipe_id = ? AND journee >= 999
        """, (team_id,))
        stats = cursor.fetchone()
        
        if stats:
            bp = stats[0]
            bc = stats[1]
            print(f"\n[RESULT] Buts Pour: {bp}, Buts Contre: {bc}")
            
            if bp == 5 and bc == 1:
                print("   [SUCCESS] Le calcul est CORRECT !")
            else:
                print(f"   [FAIL] Attendu (5, 1), Reçu ({bp}, {bc})")
        else:
            print("   [FAIL] Pas de données dans classement")

    # Cleanup
    with database.get_db_connection() as conn:
         cursor = conn.cursor()
         cursor.execute("DELETE FROM resultats WHERE journee IN (999, 1000)")
         # cursor.execute("DELETE FROM equipes WHERE nom LIKE '%Zeus%'") # Keep IDs valid for now
         print("\n[CLEANUP] Données de test nettoyées (partiellement)")

if __name__ == "__main__":
    test_goal_calculation()
