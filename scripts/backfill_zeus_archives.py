import sqlite3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core import database

def calculate_points(score_dom, score_ext):
    if score_dom > score_ext: return 3, 0
    if score_dom < score_ext: return 0, 3
    return 1, 1

def generate_history():
    print("[HISTORY] Reconstruction complète de l'historique Zeus...")
    
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Nettoyer l'archive (optionnel, mais propre)
        # cursor.execute("DELETE FROM zeus_classement_archive") 
        # print("   [INFO] Archives existantes purgées.")
        
        # 2. Récupérer TOUS les résultats ordonnés
        cursor.execute("SELECT journee, equipe_dom_id, equipe_ext_id, score_dom, score_ext FROM resultats WHERE score_dom IS NOT NULL ORDER BY journee ASC")
        matchs = cursor.fetchall()
        
        if not matchs:
            print("   [WARN] Aucun match trouvé.")
            return

        # 3. Rejouer la saison match par match
        # Structure: teams[id] = {'pts': 0, 'bp': 0, 'bc': 0, 'forme': []}
        teams = {}
        
        # On groupe par journee
        from collections import defaultdict
        matchs_par_journee = defaultdict(list)
        for m in matchs:
            matchs_par_journee[m[0]].append(m)
            
        sorted_journees = sorted(matchs_par_journee.keys())
        print(f"   [INFO] {len(sorted_journees)} journées à reconstruire ({sorted_journees[0]} à {sorted_journees[-1]}).")
        
        for journee in sorted_journees:
            # Traiter les matchs de la journée
            for _, d_id, e_id, s_d, s_e in matchs_par_journee[journee]:
                # Init teams if needed
                if d_id not in teams: teams[d_id] = {'pts': 0, 'bp': 0, 'bc': 0, 'forme': []}
                if e_id not in teams: teams[e_id] = {'pts': 0, 'bp': 0, 'bc': 0, 'forme': []}
                
                # Update Stats
                teams[d_id]['bp'] += s_d
                teams[d_id]['bc'] += s_e
                teams[e_id]['bp'] += s_e
                teams[e_id]['bc'] += s_d
                
                p_d, p_e = calculate_points(s_d, s_e)
                teams[d_id]['pts'] += p_d
                teams[e_id]['pts'] += p_e
                
                # Forme (V, N, D)
                res_d = 'V' if s_d > s_e else ('N' if s_d == s_e else 'D')
                res_e = 'V' if s_e > s_d else ('N' if s_e == s_d else 'D')
                teams[d_id]['forme'].append(res_d)
                teams[e_id]['forme'].append(res_e)
            
            # Fin de journée : Calcul du classement et Snapshot
            # On trie par Pts DESC, puis Diff DESC, puis BP DESC
            sorted_teams = sorted(teams.items(), key=lambda x: (
                x[1]['pts'], 
                x[1]['bp'] - x[1]['bc'], 
                x[1]['bp']
            ), reverse=True)
            
            # Insert Snapshot
            count_inserted = 0
            for position, (tid, stats) in enumerate(sorted_teams, 1):
                forme_str = "".join(stats['forme'][-5:]) # 5 derniers
                
                # UPSERT
                cursor.execute("""
                    INSERT OR REPLACE INTO zeus_classement_archive 
                    (journee, equipe_id, position, points, forme, buts_pour, buts_contre)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (journee, tid, position, stats['pts'], forme_str, stats['bp'], stats['bc']))
                count_inserted += 1
            
            print(f"   [PROGRESS] Journée {journee} archivée ({count_inserted} équipes).", end='\r')

    print(f"\n[SUCCESS] Historique reconstruit avec succès !")

if __name__ == "__main__":
    generate_history()

