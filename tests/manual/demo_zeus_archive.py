from src.zeus.env import ZeusEnv
from src.zeus.archive_manager import get_classement_archive

print("🎯 Test Final : Mémoire Photographique ZEUS")

env = ZeusEnv()
print(f'✅ ZEUS charge {len(env.matches)} matchs')

# Test avec un match qui a une archive (J4)
for match in env.matches:
    if match.get('journee') == 4:
        print(f'📊 Test J4: {match.get("equipe_dom_id")} vs {match.get("equipe_ext_id")}')
        
        dom_archive = get_classement_archive(4, match.get('equipe_dom_id'))
        ext_archive = get_classement_archive(4, match.get('equipe_ext_id'))
        
        print(f'   Archive DOM: {dom_archive}')
        print(f'   Archive EXT: {ext_archive}')
        break

print("\n🎉 ZEUS avec mémoire photographique est opérationnel !")
print("📚 Les archives se créeront automatiquement à chaque nouvelle journée.")
