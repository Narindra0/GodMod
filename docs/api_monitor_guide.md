# Guide : Systeme de Surveillance API

## Vue d'Ensemble

Le module `api_monitor.py` surveille continuellement l'API pour detecter automatiquement les nouvelles journees et declencher les collectes de donnees.

## Fonctionnement

### Principe

```
Boucle Infinie (toutes les 30s)
  |
  ├─> Recuperer journee MAX depuis API
  ├─> Recuperer journee MAX depuis BDD
  |
  ├─> Comparer
  |     |
  |     ├─ API > BDD ? 
  |     |   └─> OUI : NOUVELLE JOURNEE !
  |     |         |
  |     |         ├─> Collecter Resultats
  |     |         ├─> Collecter Classement
  |     |         ├─> Collecter Cotes J+1
  |     |         └─> Callback utilisateur
  |     |
  |     └─ API = BDD ?
  |         └─> Continuer surveillance
  |
  └─> Sleep 30s
```

### Exemple de Flux

**Etat Initial :**
- BDD : J12, J13, J14
- API : J12, J13, J14
- **Action** : Rien (surveillance continue)

**Nouvelle Journee Detectee :**
- BDD : J14
- API : **J15** (nouveau !)
- **Action** :
  1. Collecter resultats J15
  2. Collecter classement apres J15
  3. Collecter cotes pour J16
  4. Appeler callback (pour predictions IA)

## Utilisation

### Mode Standalone (Test)

```bash
python src/api/api_monitor.py
```

Demarre la surveillance avec callback de test.

### Integration dans main.py

```python
from src.api.api_monitor import start_monitoring
from src.analysis import intelligence

def on_new_journee(journee):
    """Callback appele quand nouvelle journee detectee"""
    print(f"Nouvelle journee {journee} traitee !")
    
    # Mettre a jour scoring IA
    intelligence.mettre_a_jour_scoring()
    
    # Generer predictions pour J+1
    journee_next = journee + 1
    selections = intelligence.selectionner_meilleurs_matchs_ameliore(journee_next)
    
    print(f"{len(selections)} predictions generees pour J{journee_next}")

# Demarrer surveillance
start_monitoring(callback_on_new_journee=on_new_journee)
```

## Configuration

Editer `MONITOR_CONFIG` dans `api_monitor.py` :

```python
MONITOR_CONFIG = {
    "POLL_INTERVAL": 30,      # Verifier toutes les 30s (ajuster selon besoin)
    "MAX_RETRIES": 3,         # Tentatives si erreur
    "RETRY_DELAY": 10,        # Delai entre tentatives
    "LOG_ACTIVITY": True,     # Logger activite
}
```

**Recommandations :**
- **POLL_INTERVAL** : 
  - 30s : Bon compromis (detection rapide + peu de charge)
  - 60s : Moins de charge, detection plus lente
  - 15s : Detection ultra-rapide, plus de requetes API

## Avantages vs Scraper HTML

| Aspect | Scraper HTML | API Monitor |
|--------|--------------|-------------|
| Detection | Timer visible | Automatique |
| Precision | ~5s apres LIVE | Immediat |
| Fiabilite | Depend HTML | JSON stable |
| Charge | Browser lourd | Requetes legeres |
| Flexibilite | Rigide | Configurable |

## Gestion Transition Saison (Nouveau ✅)

Le système gère automatiquement le passage d'une saison à l'autre :

1. **Fin de Saison (J37 -> J38)**
   - Si la BDD est à **J37** et l'API annonce **J38**
   - **Action :** Le système **IGNORE** J38 (selon demande utilisateur) et reste en attente.
   - **Log :** `[INFO] Fin de saison (J38) detectee. En attente de J1...`

2. **Nouvelle Saison (Detection J1)**
   - Si la BDD est en fin de saison (>=37) et l'API annonce **J1**
   - **Action Automatique :**
     1. **Archivage :** Création d'un backup CSV dans `data/archives/`
     2. **Réinitialisation :** Reset des tables (Résultats, Matchs, Cotes, Classement)
     3. **Redémarrage :** Collecte des données pour J1
   - **Log :** `[NEW] NOUVELLE SAISON DETECTEE (J1) !`

## Fonctions Principales

### `get_max_journee_in_db()`
Recupere la derniere journee en BDD.

### `get_max_journee_from_api()`
Recupere la derniere journee depuis l'API.

### `collect_full_data(journee)`
Collecte complete quand nouvelle journee detectee :
1. Resultats
2. Classement
3. Cotes J+1

### `start_monitoring(callback_on_new_journee, verbose)`
Demarre la surveillance continue.

**Parametres :**
- `callback_on_new_journee` : Fonction a appeler apres collecte
- `verbose` : Afficher messages de surveillance

## Gestion des Erreurs

Le systeme gere automatiquement :
- **Erreurs API temporaires** : Retry avec delai
- **Erreurs consecutives** : Arret apres 3 echecs
- **Interruption utilisateur** : Arret propre (CTRL+C)

## Logs

Les logs sont sauvegardes dans :
- `logs/` (si configure)
- Sortie console

**Niveaux :**
- `INFO` : Detection journees, collectes
- `WARNING` : Erreurs temporaires
- `ERROR` : Erreurs critiques

## Integration Complete dans main.py

Remplacer la boucle actuelle par :

```python
def main():
    print("GODMOD V2 - Mode API Monitor")
    
    # Initialiser BDD
    database.initialiser_db()
    
    # Callback pour IA
    def callback_ia(journee):
        # Mettre a jour scoring
        intelligence.mettre_a_jour_scoring()
        
        # Predictions J+1
        journee_next = journee + 1
        if journee_next >= config.JOURNEE_DEPART_PREDICTION:
            selections = intelligence.selectionner_meilleurs_matchs_ameliore(journee_next)
            if selections:
                print(f"✅ {len(selections)} predictions pour J{journee_next}")
    
    # Demarrer surveillance
    start_monitoring(callback_on_new_journee=callback_ia)

if __name__ == "__main__":
    main()
```

## Recommandations

1. **Tester d'abord** en standalone
2. **Surveiller logs** pendant 24h
3. **Ajuster POLL_INTERVAL** selon besoin
4. **Utiliser callback** pour automatisation complete

## Avantages Cles

- ✅ Detection automatique (pas de timer HTML)
- ✅ Leger (pas de browser)
- ✅ Temps reel (30s max de latence)
- ✅ Flexible (callback personnalisable)
- ✅ Robuste (gestion erreurs)
- ✅ Simple (1 fonction pour tout)
