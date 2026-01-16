"""
Script de diagnostic complet pour Zeus en mode shadow
"""
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import get_db_connection
from src.zeus import inference
from src.zeus.archive_manager import lister_journees_archivees

print("="*60)
print("   DIAGNOSTIC ZEUS - MODE SHADOW")
print("="*60)

# TEST 1 : Vérification de la base de données
print("\n[TEST 1] Vérification des données en base")
print("-" * 60)

try:
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Compter les données
        resultats = c.execute('SELECT COUNT(*) FROM resultats').fetchone()[0]
        cotes = c.execute('SELECT COUNT(*) FROM cotes').fetchone()[0]
        classement = c.execute('SELECT COUNT(*) FROM classement').fetchone()[0]
        zeus_predictions = c.execute('SELECT COUNT(*) FROM zeus_predictions').fetchone()[0]
        zeus_archives = c.execute('SELECT COUNT(*) FROM zeus_classement_archive').fetchone()[0]
        
        print(f"✓ Résultats : {resultats}")
        print(f"✓ Cotes : {cotes}")
        print(f"✓ Classement : {classement}")
        print(f"✓ Zeus predictions : {zeus_predictions}")
        print(f"✓ Zeus archives : {zeus_archives}")
        
        # Journée maximum
        journee_max = c.execute('SELECT MAX(journee) FROM resultats').fetchone()[0]
        print(f"✓ Journée maximum : {journee_max if journee_max else 'Aucune'}")
        
        # Vérifier le classement pour la journée max
        if journee_max:
            classement_journee = c.execute('SELECT COUNT(*) FROM classement WHERE journee = ?', (journee_max,)).fetchone()[0]
            print(f"✓ Classement pour J{journee_max} : {classement_journee} équipes")
            
            # Afficher un échantillon de classement
            if classement_journee > 0:
                sample = c.execute('''
                    SELECT e.nom, cl.position, cl.points, cl.forme 
                    FROM classement cl 
                    JOIN equipes e ON cl.equipe_id = e.id 
                    WHERE cl.journee = ? 
                    LIMIT 3
                ''', (journee_max,)).fetchall()
                print("\n  Échantillon du classement J{}:".format(journee_max))
                for nom, pos, pts, forme in sample:
                    print(f"    {pos}. {nom} - {pts} pts (Forme: {forme})")
        
        # Vérifier les cotes disponibles
        if journee_max:
            cotes_journee = c.execute('SELECT COUNT(*) FROM cotes WHERE journee = ?', (journee_max + 1,)).fetchone()[0]
            print(f"\n✓ Cotes disponibles pour J{journee_max + 1} : {cotes_journee} matchs")
            
            if cotes_journee > 0:
                sample_cotes = c.execute('''
                    SELECT e1.nom, e2.nom, c.cote_1, c.cote_x, c.cote_2
                    FROM cotes c
                    JOIN equipes e1 ON c.equipe_dom_id = e1.id
                    JOIN equipes e2 ON c.equipe_ext_id = e2.id
                    WHERE c.journee = ?
                    LIMIT 2
                ''', (journee_max + 1,)).fetchall()
                print(f"\n  Échantillon des cotes pour J{journee_max + 1}:")
                for dom, ext, c1, cx, c2 in sample_cotes:
                    print(f"    {dom} vs {ext} : {c1} / {cx} / {c2}")
    
    print("\n✅ TEST 1 RÉUSSI")
    
except Exception as e:
    print(f"\n❌ ERREUR TEST 1 : {e}")
    import traceback
    traceback.print_exc()

# TEST 2 : Chargement de l'agent Zeus
print("\n" + "="*60)
print("[TEST 2] Chargement du modèle Zeus")
print("-" * 60)

try:
    agent = inference.get_agent()
    if agent:
        print("✅ Agent Zeus chargé avec succès")
        print(f"   Type d'agent : {type(agent).__name__}")
    else:
        print("❌ Échec du chargement de l'agent Zeus")
        print("   Le modèle zeus_v1.zip n'a pas pu être chargé")
        
except Exception as e:
    print(f"❌ ERREUR TEST 2 : {e}")
    import traceback
    traceback.print_exc()

# TEST 3 : Test de prédiction Zeus
print("\n" + "="*60)
print("[TEST 3] Test de prédiction Zeus")
print("-" * 60)

try:
    # Données de test
    match_data = {
        'pos_dom': 5,
        'pos_ext': 10,
        'forme_dom': 'VVVDN',
        'forme_ext': 'DDDNV',
        'cote_1': 2.1,
        'cote_x': 3.2,
        'cote_2': 3.5,
        'journee': 10
    }
    
    print("Match de test :")
    print(f"  Position DOM: {match_data['pos_dom']}, Forme: {match_data['forme_dom']}")
    print(f"  Position EXT: {match_data['pos_ext']}, Forme: {match_data['forme_ext']}")
    print(f"  Cotes: {match_data['cote_1']} / {match_data['cote_x']} / {match_data['cote_2']}")
    
    action = inference.predire_match(match_data)
    
    labels = {0: "1 (Victoire DOM)", 1: "X (Match Nul)", 2: "2 (Victoire EXT)", 3: "SKIP (Passer)"}
    prediction = labels.get(action, "INCONNU")
    
    print(f"\n✅ Zeus prédit : {prediction}")
    
except Exception as e:
    print(f"\n❌ ERREUR TEST 3 : {e}")
    import traceback
    traceback.print_exc()

# TEST 4 : Vérifier les archives Zeus
print("\n" + "="*60)
print("[TEST 4] Archives Zeus (Mémoire Photographique)")
print("-" * 60)

try:
    journees_archivees = lister_journees_archivees()
    if journees_archivees:
        print(f"✅ Journées archivées : {journees_archivees}")
    else:
        print("⚠️  Aucune archive Zeus trouvée")
        print("   Les archives se créeront automatiquement lors du prochain cycle")
    
except Exception as e:
    print(f"❌ ERREUR TEST 4 : {e}")
    import traceback
    traceback.print_exc()

# RÉSUMÉ
print("\n" + "="*60)
print("   RÉSUMÉ DU DIAGNOSTIC")
print("="*60)

print("\n✅ = Fonctionne correctement")
print("⚠️  = Attention requise")
print("❌ = Problème détecté")

print("\n" + "="*60)
print("Diagnostic terminé.")
print("="*60)
