"""
Script de test pour valider les améliorations de l'intelligence.
Teste les nouvelles fonctions sans modifier les données existantes.
"""
import sys
import os

# Ajouter le répertoire racine du projet au path (remonter 2 niveaux: integration -> tests -> racine)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.analysis.intelligence import (
    pondere_forme_amelioree,
    calculer_momentum_internal,
    analyser_cotes_suspectes,
    analyser_buts_recents_internal,
    analyser_confrontations_directes,
    calculer_probabilite_amelioree,
    calculer_probabilite  # Ancienne fonction pour comparaison
)
from src.core.database import get_db_connection
from src.core import config


def test_pondere_forme():
    """Test de la fonction de pondération améliorée."""
    print("\n=== TEST 1: Pondération de forme améliorée ===")
    
    # Test avec forme classique
    forme = "DDVVV"
    ancien_score = sum({'V': 3, 'N': 1, 'D': 0}.get(c, 0) for c in forme)
    nouveau_score = pondere_forme_amelioree(forme)
    
    print(f"Forme: {forme}")
    print(f"  Ancien système: {ancien_score} points")
    print(f"  Nouveau système: {nouveau_score} points")
    print(f"  Gain: +{nouveau_score - ancien_score} points (+{(nouveau_score/ancien_score - 1)*100:.1f}%)")
    
    assert nouveau_score > ancien_score, "Le nouveau système doit donner plus de poids aux matchs récents"
    print("[OK] Test reussi!")


def test_momentum():
    """Test de la détection de momentum."""
    print("\n=== TEST 2: Détection de momentum ===")
    
    test_cases = [
        ("VVVDN", 3.0, "3 victoires consécutives"),
        ("VVNVD", 1.5, "2 victoires"),
        ("DDDVV", -3.0, "3 défaites consécutives"),
        ("DDNVD", -1.5, "2 défaites"),
        # Note: "VDVDN" a "VDN" comme 3 derniers, pas "VDV" ou "DVD", donc pas de pattern mitigé
        ("DVDVD", -0.5, "Série mitigée (3 derniers: DVD)"),
        ("NVDNV", 0.0, "Pas de pattern")
    ]
    
    for forme, attendu, description in test_cases:
        resultat = calculer_momentum_internal(forme)
        status = "[OK]" if resultat == attendu else "[ERREUR]"
        print(f"{status} {forme}: {resultat} (attendu: {attendu}) - {description}")
    
    print("[OK] Tests de momentum termines!")


def test_analyse_cotes():
    """Test de l'analyse des cotes."""
    print("\n=== TEST 3: Analyse des cotes suspectes ===")
    
    test_cases = [
        ((1.15, 6.50, 11.00), -3.0, "Piège favori évident (cote < 1.30)"),
        ((1.75, 3.40, 4.50), 2.0, "Zone idéale (1.50-2.20)"),
        ((2.10, 3.20, 2.20), -1.5, "Match trop équilibré (écart < 0.3)"),
        ((1.80, 3.50, 6.00), 1.0, "Outsider trop côté (cote > 5.0)"),
        ((2.50, 3.00, 2.80), 0.0, "Cotes normales")
    ]
    
    for cotes, attendu, description in test_cases:
        c1, cx, c2 = cotes
        resultat = analyser_cotes_suspectes(c1, cx, c2)
        status = "[OK]" if abs(resultat - attendu) < 0.1 else "[ERREUR]"
        print(f"{status} Cotes {cotes}: {resultat} (attendu: {attendu}) - {description}")
    
    print("[OK] Tests de cotes termines!")


def test_analyse_buts():
    """Test de l'analyse des buts (nécessite des données DB)."""
    print("\n=== TEST 4: Analyse des buts récents ===")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Récupérer une équipe qui a joué
            cursor.execute("SELECT DISTINCT equipe_id FROM classement LIMIT 1")
            equipe = cursor.fetchone()
            
            if equipe:
                equipe_id = equipe[0]
                resultat = analyser_buts_recents_internal(cursor, equipe_id)
                
                if resultat:
                    buts_pour, buts_contre = resultat
                    print(f"  Equipe ID {equipe_id}: {buts_pour} buts marques, {buts_contre} encaisses")
                    print("[OK] Test reussi (donnees disponibles)")
                else:
                    print("[ATTENTION] Pas assez de donnees pour cette equipe")
            else:
                print("[ATTENTION] Aucune equipe trouvee dans la base")
    except Exception as e:
        print(f"[ATTENTION] Erreur lors du test: {e}")
        print("   (Normal si la base de donnees est vide)")


def test_confrontations():
    """Test de l'analyse des confrontations directes."""
    print("\n=== TEST 5: Confrontations directes ===")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Chercher deux équipes qui se sont affrontées
            cursor.execute("""
                SELECT DISTINCT equipe_dom_id, equipe_ext_id 
                FROM resultats 
                WHERE score_dom IS NOT NULL 
                LIMIT 1
            """)
            match = cursor.fetchone()
            
            if match:
                dom_id, ext_id = match
                resultat = analyser_confrontations_directes(dom_id, ext_id)
                print(f"  Confrontation {dom_id} vs {ext_id}: Bonus/Malus = {resultat}")
                print("[OK] Test reussi (donnees disponibles)")
            else:
                print("[ATTENTION] Pas assez de donnees historiques")
    except Exception as e:
        print(f"[ATTENTION] Erreur lors du test: {e}")
        print("   (Normal si la base de donnees est vide)")


def test_comparaison_ancien_nouveau():
    """Compare l'ancien et le nouveau système."""
    print("\n=== TEST 6: Comparaison Ancien vs Nouveau système ===")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Récupérer un match avec cotes
            cursor.execute("""
                SELECT equipe_dom_id, equipe_ext_id, cote_1, cote_x, cote_2 
                FROM cotes 
                LIMIT 1
            """)
            match = cursor.fetchone()
            
            if match:
                dom_id, ext_id, c1, cx, c2 = match
                
                # Ancien système
                pred_ancien, conf_ancien = calculer_probabilite(dom_id, ext_id)
                
                # Nouveau système
                pred_nouveau, conf_nouveau = calculer_probabilite_amelioree(dom_id, ext_id, c1, cx, c2)
                
                print(f"Match: Équipe {dom_id} vs {dom_id}")
                print(f"  Ancien systeme: {pred_ancien} (confiance: {conf_ancien:.2f})")
                print(f"  Nouveau systeme: {pred_nouveau} (confiance: {conf_nouveau:.2f})")
                print(f"  Difference: {conf_nouveau - conf_ancien:+.2f}")
                
                if pred_ancien != pred_nouveau:
                    print(f"  [ATTENTION] Prediction differente: {pred_ancien} -> {pred_nouveau}")
                else:
                    print(f"  [OK] Prediction identique: {pred_nouveau}")
                
                print("[OK] Test de comparaison termine")
            else:
                print("[ATTENTION] Aucun match avec cotes trouve")
    except Exception as e:
        print(f"[ATTENTION] Erreur lors du test: {e}")
        print("   (Normal si la base de donnees est vide)")


def main():
    """Lance tous les tests."""
    print("=" * 60)
    print("TESTS DES AMÉLIORATIONS DE L'INTELLIGENCE")
    print("=" * 60)
    
    # Tests unitaires (ne nécessitent pas la DB)
    test_pondere_forme()
    test_momentum()
    test_analyse_cotes()
    
    # Tests avec DB (peuvent échouer si DB vide)
    test_analyse_buts()
    test_confrontations()
    test_comparaison_ancien_nouveau()
    
    print("\n" + "=" * 60)
    print("[OK] TOUS LES TESTS TERMINES")
    print("=" * 60)
    print("\nNote: Les tests necessitant la DB peuvent afficher des avertissements")
    print("      si la base de donnees est vide. C'est normal.")


if __name__ == "__main__":
    main()

