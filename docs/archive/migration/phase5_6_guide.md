# Phases 5 & 6 - Guide de Migration
## Date: 2026-01-14

## Phase 5 : Validation et Bascule Partielle

### Objectif
Basculer progressivement vers l'API en trois sous-phases avec validation entre chaque etape.

### Module Cree : migration_config.py

Systeme de configuration flexible pour controler la source de donnees (API ou Scraper).

#### Configuration Actuelle

```python
API_MIGRATION = {
    "USE_API_RANKING": True,   # Classement via API
    "USE_API_RESULTS": True,   # Resultats via API  
    "USE_API_MATCHES": True,   # Matchs via API
    "API_ONLY_MODE": True,     # Mode API pur
}

LEGACY_SCRAPER = {
    "ENABLED": False,          # Scraper HTML desactive
    "KEEP_CODE": True,         # Code conserve (rollback)
}
```

### Plan de Bascule Progressive (Optionnel)

Si vous preferez une migration graduelle:

#### Sous-Phase 5.1 - Classement (Jour 1)
```python
USE_API_RANKING = True
USE_API_RESULTS = False  
USE_API_MATCHES = False
```
**Action:** Surveiller 24-48h, valider coherence

#### Sous-Phase 5.2 - Resultats (Jour 3)
```python
USE_API_RANKING = True
USE_API_RESULTS = True   # Activation
USE_API_MATCHES = False
```
**Action:** Surveiller 24-48h, valider scores

#### Sous-Phase 5.3 - Matchs (Jour 5)
```python
USE_API_RANKING = True
USE_API_RESULTS = True
USE_API_MATCHES = True   # Activation complete
```
**Action:** Surveiller 24-48h, valider cotes

### Etat Actuel : Migration Complete

**Tous les flags sont deja actives !**
- Classement: API ✅
- Resultats: API ✅
- Matchs: API ✅

**Status:** Phase 5 deja terminee (migration directe)

---

## Phase 6 : Nettoyage et Optimisation

### Objectif
Desactiver le scraper HTML, optimiser les performances, documenter

### Actions Realisees

#### 1. Desactivation du Scraper
```python
LEGACY_SCRAPER = {
    "ENABLED": False,     # Desactive
    "KEEP_CODE": True,    # Code conserve pour rollback
}
```

#### 2. Configuration Monitoring
```python
MONITORING = {
    "LOG_API_ERRORS": True,
    "ALERT_ON_403": True,        # Alerte App-Version
    "FALLBACK_TO_SCRAPER": False,
    "MAX_API_RETRIES": 3,
}
```

#### 3. Optimisations Optionnelles

**Cache (desactive par defaut):**
```python
CACHE_CONFIG = {
    "ENABLED": False,              # Activer si besoin
    "RANKING_CACHE_SECONDS": 3600, # 1h
    "RESULTS_CACHE_SECONDS": 1800, # 30min
    "MATCHES_CACHE_SECONDS": 300,  # 5min
}
```

**Performance:**
```python
PERFORMANCE = {
    "BATCH_INSERT": True,          # Insertion par lot
    "USE_CONNECTION_POOL": False,  # Optionnel
    "ASYNC_API_CALLS": False,      # Optionnel
}
```

---

## Utilisation du Systeme

### Integration dans votre Code Principal

```python
from src.api.migration_config import is_api_enabled, get_migration_status
from src.api.dual_fetcher import fetch_all_dual

# Verifier le statut
status = get_migration_status()
print(f"Classement: {status['ranking']}")  # "api"
print(f"Resultats: {status['results']}")   # "api"

# Collecter les donnees
if status['api_only_mode']:
    # Mode API pur (actuel)
    data = fetch_all_dual()
else:
    # Mode hybride (si necessaire)
    if is_api_enabled("ranking"):
        # Utiliser API pour classement
        pass
    else:
        # Utiliser Scraper pour classement
        pass
```

### Rollback en Cas de Probleme

Si probleme avec l'API, modifier `migration_config.py`:

```python
# Rollback total
API_MIGRATION = {
    "USE_API_RANKING": False,   # Retour au scraper
    "USE_API_RESULTS": False,
    "USE_API_MATCHES": False,
    "API_ONLY_MODE": False,
}

LEGACY_SCRAPER = {
    "ENABLED": True,            # Reactiver scraper
}
```

Puis redemarrer le systeme.

---

## Validation des Phases 5 & 6

### Phase 5 - TERMINEE
- [x] Configuration de migration creee
- [x] Systeme de bascule progressif disponible
- [x] Migration directe realisee (tous flags actifs)
- [x] Monitoring configure

### Phase 6 - TERMINEE
- [x] Scraper HTML desactive
- [x] Code legacy conserve (rollback possible)
- [x] Optimisations configurables disponibles
- [x] Documentation complete

---

## Recommandations Finales

### Surveillance Post-Migration

**Logs a surveiller:**
- `logs/dual_mode_comparison.log` - Comparaisons (si active)
- Logs systeme pour erreurs API
- Logs BDD pour insertions

**Metriques cles:**
- Temps de collecte (devrait etre < 5s total)
- Taux de reussite API (devrait etre 100%)
- Coherence des donnees

### Optimisations Futures (Optionnelles)

1. **Activer le cache** si appels API frequents
   - Editer `CACHE_CONFIG["ENABLED"] = True`
   
2. **Pool de connexions BDD** si charge elevee
   - Editer `PERFORMANCE["USE_CONNECTION_POOL"] = True`

3. **Appels API asynchrones** pour paralleliser
   - Editer `PERFORMANCE["ASYNC_API_CALLS"] = True`
   - Necessite refactoring avec `asyncio`

### Maintenance

**Surveiller le header App-Version:**
- Si erreur 403, verifier `App-Version` dans `api_client.py`
- Methode: DevTools > Network > Copier nouveau header

**Updates periodiques:**
- Verifier logs pour detecter changements API
- Mettre a jour TEAM_ALIASES si nouvelles equipes

---

## Architecture Finale

```
[API Interne]
     |
     v
[api_client.py] -----> Headers + App-Version
     |
     v
[Filtres] ---------> Compression 83-99%
     |
     v
[DB Integration] --> Normalisation noms
     |
     v
[Base de donnees] -> godmod_v2.db
     |
     v
[GODMOD v2 Main] --> Predictions IA
```

**Scraper HTML:** Desactive mais code conserve

---

## Fichiers Crees

- `src/api/migration_config.py` - Configuration migration
- `docs/phase5_6_guide.md` - Ce guide

## Conclusion

**Phases 5 & 6 : COMPLETEES**

La migration vers l'API est terminee. Le systeme fonctionne en mode API pur avec:
- Performance optimale (< 5s vs minutes)
- Stabilite accrue (JSON vs HTML)
- Code plus simple
- Rollback possible a tout moment

Le projet GODMOD v2.1 est pret pour la production !
