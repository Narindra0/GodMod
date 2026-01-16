from src.zeus.env import ZeusEnv
from src.zeus.archive_manager import get_classement_archive, lister_journees_archivees

try:
    print("🔍 Test du système ZEUS avec mémoire photographique")
    
    # Vérifier les archives disponibles
    journees = lister_journees_archivees()
    print(f"📚 Journées archivées : {journees}")
    
    env = ZeusEnv()
    print(f'✅ ZeusEnv charge {len(env.matches)} matchs')
    
    if env.matches:
        first_match = env.matches[0]
        print(f'📊 Premier match : J{first_match.get("journee")}')
        print(f'   Equipes : {first_match.get("equipe_dom_id")} vs {first_match.get("equipe_ext_id")}')
        print(f'   Cotes : {first_match.get("cote_1")} / {first_match.get("cote_x")} / {first_match.get("cote_2")}')
        
        # Test de récupération du classement archivé
        journee = first_match.get("journee")
        dom_id = first_match.get("equipe_dom_id")
        ext_id = first_match.get("equipe_ext_id")
        
        classement_dom = get_classement_archive(journee, dom_id)
        classement_ext = get_classement_archive(journee, ext_id)
        
        print(f'   Classement DOM (archive J{journee}) : {classement_dom}')
        print(f'   Classement EXT (archive J{journee}) : {classement_ext}')
        
        # Test feature engineering
        from src.zeus.feature_engineering import construire_vecteur_etat
        vecteur = construire_vecteur_etat(first_match)
        print(f'   Vecteur : {len(vecteur)} features')
        print(f'   Valeurs : {[round(f, 3) for f in vecteur[:5]]}...')
    else:
        print('❌ Aucun match charge')
        
except Exception as e:
    print(f'❌ Erreur : {e}')
    import traceback
    traceback.print_exc()
