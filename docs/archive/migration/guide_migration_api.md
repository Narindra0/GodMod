# 🚀 Guide de Mise à Jour : Migration vers l'API Interne
## De Noob à Pro - GODMOD v2.1

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Pourquoi cette mise à jour ?](#pourquoi-cette-mise-à-jour)
3. [Étape 1 : Création du module API](#étape-1--création-du-module-api)
4. [Étape 2 : Filtrage des données](#étape-2--filtrage-des-données)
5. [Étape 3 : Intégration en base de données](#étape-3--intégration-en-base-de-données)
6. [Ressources et endpoints](#ressources-et-endpoints)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Introduction

Ce document explique comment **remplacer l'ancien système de scraping HTML** (lent et fragile) par une **communication directe avec l'API HTTP interne** du site.

### Ancien système vs Nouveau système

| Aspect | Ancien (Scraping HTML) | Nouveau (API) |
|--------|------------------------|---------------|
| **Vitesse** | Plusieurs secondes | < 100ms |
| **Stabilité** | Fragile (HTML change souvent) | Très stable (JSON stable) |
| **Ressources** | Lourd (Playwright, navigateur) | Ultra léger (requête HTTP simple) |
| **Données** | Parsing HTML complexe | JSON structuré prêt à l'emploi |
| **Maintenance** | Haute (mise à jour fréquente) | Basse (peu de changements) |

---

## 🧠 Pourquoi cette mise à jour ?

### Avantages

✅ **Performance améliorée** : Temps de réponse divisé par 10+  
✅ **Stabilité accrue** : Le format JSON change rarement  
✅ **Code plus simple** : Pas de parsing HTML complexe  
✅ **Moins de ressources** : Pas besoin de navigateur headless  
✅ **Données structurées** : JSON directement exploitable  

### Inconvénients potentiels

⚠️ **Dépendance à l'API** : Si l'API change, il faut adapter  
⚠️ **Headers critiques** : Nécessite les bons headers pour éviter les erreurs 403  

---

## 🛠 Étape 1 : Création du module API

### 1.1 Créer le fichier `api_client.py`

Ce nouveau fichier remplace vos anciens scripts Playwright. Il simule un navigateur pour obtenir les données de l'API.

```python
"""
Module de communication avec l'API interne du site
Remplace le scraping HTML par des appels API directs
"""

import requests
import json
from typing import List, Dict, Optional

# ==================== CONFIGURATION ====================

# Headers HTTP cruciaux pour ne pas être bloqué (Erreur 403)
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr",
    "App-Version": "31358",  # ⚠️ À surveiller si le site se met à jour
    "Origin": "https://bet261.mg",
    "Referer": "https://bet261.mg/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

BASE_URL = "https://hg-event-api-prod.sporty-tech.net/api"
LEAGUE_ID = 8035  # ID de la ligue par défaut

# ==================== FONCTIONS API ====================

def get_ranking(league_id: int = LEAGUE_ID) -> List[Dict]:
    """
    Récupère le classement complet de la ligue en JSON
    
    Args:
        league_id: ID de la ligue (par défaut: 8035)
    
    Returns:
        Liste des équipes avec leurs statistiques
    """
    url = f"{BASE_URL}/instantleagues/{league_id}/ranking"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Lève une exception si status != 200
        
        # Le site renvoie un objet avec une clé 'teams'
        data = response.json()
        return data.get("teams", [])
    
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout lors de la récupération du classement")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API Ranking : {e}")
        return []


def get_recent_results(league_id: int = LEAGUE_ID, skip: int = 0, take: int = 5) -> Dict:
    """
    Récupère les résultats récents de la ligue
    
    Args:
        league_id: ID de la ligue
        skip: Nombre de résultats à sauter (pagination)
        take: Nombre de résultats à récupérer
    
    Returns:
        Dictionnaire contenant les rounds et matchs
    """
    url = f"{BASE_URL}/instantleagues/{league_id}/results"
    params = {"skip": skip, "take": take}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API Results : {e}")
        return {"rounds": []}


def get_upcoming_matches(league_id: int = LEAGUE_ID) -> Dict:
    """
    Récupère les matchs à venir de la ligue
    
    Args:
        league_id: ID de la ligue
    
    Returns:
        Dictionnaire contenant les rounds et matchs avec cotes
    """
    url = f"{BASE_URL}/instantleagues/{league_id}/matches"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API Matches : {e}")
        return {"rounds": []}


# ==================== UTILITAIRES ====================

def save_to_json(data: Dict, filename: str):
    """Sauvegarde les données dans un fichier JSON"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Données sauvegardées dans {filename}")


# ==================== TESTS ====================

if __name__ == "__main__":
    print("🧪 Test du module API Client\n")
    
    # Test 1: Classement
    print("1️⃣ Récupération du classement...")
    ranking = get_ranking()
    print(f"   ✅ {len(ranking)} équipes récupérées\n")
    
    # Test 2: Résultats
    print("2️⃣ Récupération des résultats...")
    results = get_recent_results(take=3)
    print(f"   ✅ {len(results.get('rounds', []))} journées récupérées\n")
    
    # Test 3: Matchs à venir
    print("3️⃣ Récupération des matchs à venir...")
    matches = get_upcoming_matches()
    print(f"   ✅ {len(matches.get('rounds', []))} journées à venir\n")
```

### 1.2 Installation des dépendances

```bash
pip install requests
```

---

## 🔍 Étape 2 : Filtrage des données

### 2.1 Pourquoi filtrer ?

> **Important** : Pour éviter de saturer la base de données avec des informations non essentielles, nous filtrons les données pour ne garder que ce qui est vraiment utile.

### 2.2 Filtre pour les résultats (`results_filter.py`)

```python
"""
Filtre pour extraire uniquement les données essentielles des résultats
Garde : équipes, score final, journée
"""

import requests
import json
from typing import List, Dict

# ==================== CONFIG ====================

URL = "https://hg-event-api-prod.sporty-tech.net/api/instantleagues/8035/results"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr",
    "App-Version": "31358",
    "Origin": "https://bet261.mg",
    "Referer": "https://bet261.mg/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ==================== FONCTION DE FILTRAGE ====================

def extract_results_minimal(data: Dict) -> List[Dict]:
    """
    Extrait uniquement les informations essentielles des résultats
    
    Structure de sortie:
    [
        {
            "roundNumber": 1,
            "matches": [
                {
                    "id": "match_123",
                    "homeTeam": "Équipe A",
                    "awayTeam": "Équipe B",
                    "score": "2-1"
                }
            ]
        }
    ]
    
    Args:
        data: Données brutes de l'API
    
    Returns:
        Liste filtrée des résultats
    """
    output = []
    rounds = data.get("rounds", [])
    
    for round_item in rounds:
        clean_round = {
            "roundNumber": round_item.get("roundNumber"),
            "matches": []
        }
        
        for match in round_item.get("matches", []):
            clean_match = {
                "id": match.get("id"),
                "homeTeam": match.get("homeTeam", {}).get("name"),
                "awayTeam": match.get("awayTeam", {}).get("name"),
                "score": match.get("score"),
            }
            
            clean_round["matches"].append(clean_match)
        
        output.append(clean_round)
    
    return output


# ==================== TEST ====================

if __name__ == "__main__":
    params = {"skip": 0, "take": 4}
    response = requests.get(URL, headers=HEADERS, params=params, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        raw_data = response.json()
        clean_data = extract_results_minimal(raw_data)
        
        print("\n===== DONNÉES FILTRÉES =====\n")
        print(json.dumps(clean_data, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Erreur : {response.text}")
```

### 2.3 Filtre pour les matchs à venir (`matches_filter.py`)

```python
"""
Filtre pour extraire les matchs à venir avec ID local et cotes
Garde : équipes, journée, cotes 1X2, ID local
"""

import requests
import json
from typing import List, Dict

# ==================== CONFIG ====================

URL = "https://hg-event-api-prod.sporty-tech.net/api/instantleagues/8035/matches"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr",
    "App-Version": "31358",
    "Origin": "https://bet261.mg",
    "Referer": "https://bet261.mg/",
    "User-Agent": "Mozilla/5.0"
}

ROUND_LIMIT = 1  # Nombre de journées à récupérer

# ==================== FONCTION D'EXTRACTION ====================

def extract_matches_with_local_ids(data: Dict, limit: int = 1) -> List[Dict]:
    """
    Extrait les matchs avec un ID local par journée
    
    Structure de sortie:
    [
        {
            "roundNumber": 1,
            "expectedStart": "2025-01-15T14:00:00Z",
            "matches": [
                {
                    "matchId": 1,  # ID local (1 → N)
                    "name": "Équipe A vs Équipe B",
                    "homeTeam": "Équipe A",
                    "awayTeam": "Équipe B",
                    "round": "1",
                    "odds": [
                        {"type": "1", "odds": 2.50},
                        {"type": "X", "odds": 3.20},
                        {"type": "2", "odds": 2.80}
                    ]
                }
            ]
        }
    ]
    
    Args:
        data: Données brutes de l'API
        limit: Nombre de journées à extraire
    
    Returns:
        Liste filtrée des matchs
    """
    # Trier les rounds par numéro et limiter
    rounds = sorted(
        data.get("rounds", []),
        key=lambda r: r.get("roundNumber", 0)
    )[:limit]
    
    output = []
    
    for r in rounds:
        clean_round = {
            "roundNumber": r.get("roundNumber"),
            "expectedStart": r.get("expectedStart"),
            "matches": []
        }
        
        # 🔹 Création d'ID LOCAL par journée (1 → N)
        for local_id, m in enumerate(r.get("matches", []), start=1):
            odds = []
            
            # Extraction des cotes 1X2
            for bet_type in m.get("eventBetTypes", []):
                if bet_type.get("name") == "1X2":
                    for item in bet_type.get("eventBetTypeItems", []):
                        odds.append({
                            "type": item.get("shortName"),
                            "odds": item.get("odds")
                        })
            
            clean_match = {
                "matchId": local_id,   # ✅ ID LOCAL
                "name": m.get("name"),
                "homeTeam": m.get("homeTeam", {}).get("name"),
                "awayTeam": m.get("awayTeam", {}).get("name"),
                "round": str(r.get("roundNumber")),
                "odds": odds
            }
            
            clean_round["matches"].append(clean_match)
        
        output.append(clean_round)
    
    return output


# ==================== TEST ====================

if __name__ == "__main__":
    response = requests.get(URL, headers=HEADERS, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        raw = response.json()
        clean = extract_matches_with_local_ids(raw, ROUND_LIMIT)
        
        print("\n===== DONNÉES FILTRÉES =====\n")
        print(json.dumps(clean, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Erreur API : {response.text}")
```

---

## 💾 Étape 3 : Intégration en base de données

### 3.1 Structure de base de données recommandée

```python
"""
Exemple d'intégration SQLite
Peut être adapté pour PostgreSQL, MySQL, etc.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict
import json

class FootballDB:
    def __init__(self, db_path: str = "football.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Crée les tables nécessaires"""
        cursor = self.conn.cursor()
        
        # Table des équipes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                points INTEGER DEFAULT 0,
                matches_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                goals_for INTEGER DEFAULT 0,
                goals_against INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table des matchs joués
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE,
                round_number INTEGER NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                score TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table des matchs à venir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upcoming_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                odds_1 REAL,
                odds_x REAL,
                odds_2 REAL,
                expected_start TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(round_number, match_id)
            )
        """)
        
        self.conn.commit()
    
    def insert_results(self, results_data: List[Dict]):
        """Insère les résultats filtrés en base"""
        cursor = self.conn.cursor()
        
        for round_data in results_data:
            round_number = round_data["roundNumber"]
            
            for match in round_data["matches"]:
                cursor.execute("""
                    INSERT OR REPLACE INTO results 
                    (match_id, round_number, home_team, away_team, score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    match["id"],
                    round_number,
                    match["homeTeam"],
                    match["awayTeam"],
                    match["score"]
                ))
        
        self.conn.commit()
        print(f"✅ Résultats insérés en base")
    
    def insert_upcoming_matches(self, matches_data: List[Dict]):
        """Insère les matchs à venir en base"""
        cursor = self.conn.cursor()
        
        for round_data in matches_data:
            round_number = round_data["roundNumber"]
            expected_start = round_data.get("expectedStart")
            
            for match in round_data["matches"]:
                # Extraire les cotes
                odds_dict = {o["type"]: o["odds"] for o in match["odds"]}
                
                cursor.execute("""
                    INSERT OR REPLACE INTO upcoming_matches 
                    (match_id, round_number, home_team, away_team, 
                     odds_1, odds_x, odds_2, expected_start)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match["matchId"],
                    round_number,
                    match["homeTeam"],
                    match["awayTeam"],
                    odds_dict.get("1"),
                    odds_dict.get("X"),
                    odds_dict.get("2"),
                    expected_start
                ))
        
        self.conn.commit()
        print(f"✅ Matchs à venir insérés en base")
    
    def get_latest_results(self, limit: int = 5):
        """Récupère les derniers résultats"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM results 
            ORDER BY round_number DESC, id DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    
    def close(self):
        """Ferme la connexion"""
        self.conn.close()


# ==================== EXEMPLE D'UTILISATION ====================

if __name__ == "__main__":
    from api_client import get_recent_results, get_upcoming_matches
    from results_filter import extract_results_minimal
    from matches_filter import extract_matches_with_local_ids
    
    # Initialisation
    db = FootballDB()
    
    # Récupération et insertion des résultats
    print("📥 Récupération des résultats...")
    results_raw = get_recent_results(take=5)
    results_clean = extract_results_minimal(results_raw)
    db.insert_results(results_clean)
    
    # Récupération et insertion des matchs à venir
    print("📥 Récupération des matchs à venir...")
    matches_raw = get_upcoming_matches()
    matches_clean = extract_matches_with_local_ids(matches_raw, limit=1)
    db.insert_upcoming_matches(matches_clean)
    
    # Affichage des derniers résultats
    print("\n📊 Derniers résultats :")
    for result in db.get_latest_results():
        print(result)
    
    db.close()
```

---

## 🌐 Ressources et endpoints

### Endpoints disponibles

| Endpoint | URL | Description |
|----------|-----|-------------|
| **Classement** | `GET /instantleagues/8035/ranking` | Classement complet de la ligue |
| **Résultats** | `GET /instantleagues/8035/results?skip=0&take=5` | Résultats récents (paginés) |
| **Matchs à venir** | `GET /instantleagues/8035/matches` | Matchs à venir avec cotes |

### URL complètes

```
# Classement
https://hg-event-api-prod.sporty-tech.net/api/instantleagues/8035/ranking

# Résultats (avec pagination)
https://hg-event-api-prod.sporty-tech.net/api/instantleagues/8035/results?skip=0&take=5

# Matchs à venir
https://hg-event-api-prod.sporty-tech.net/api/instantleagues/8035/matches
```

---

## 🔧 Troubleshooting

### Erreur 403 Forbidden

**Problème** : L'API refuse la connexion

**Solutions** :
```python
# ✅ Vérifier les headers (surtout App-Version)
HEADERS = {
    "App-Version": "31358",  # Peut changer avec les mises à jour du site
    "Origin": "https://bet261.mg",
    "Referer": "https://bet261.mg/",
}

# ✅ Vérifier la User-Agent
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

### Timeout

**Problème** : La requête prend trop de temps

**Solutions** :
```python
# Augmenter le timeout
response = requests.get(url, headers=HEADERS, timeout=30)

# Ajouter des retries
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

### Données manquantes dans le JSON

**Problème** : Certaines clés n'existent pas

**Solutions** :
```python
# ✅ Utiliser .get() avec valeur par défaut
team_name = match.get("homeTeam", {}).get("name", "Unknown")

# ✅ Vérifier avant d'accéder
if "homeTeam" in match and "name" in match["homeTeam"]:
    team_name = match["homeTeam"]["name"]
```

### App-Version obsolète

**Problème** : Le site a été mis à jour

**Solutions** :
1. Ouvrir le site dans un navigateur
2. Ouvrir les DevTools (F12)
3. Aller dans l'onglet Network
4. Rafraîchir la page
5. Chercher une requête vers l'API
6. Copier le nouveau `App-Version` dans les headers

---

## 📚 Ressources supplémentaires

### Documentation Python

- [Requests](https://docs.python-requests.org/) - Librairie HTTP
- [SQLite3](https://docs.python.org/3/library/sqlite3.html) - Base de données
- [JSON](https://docs.python.org/3/library/json.html) - Manipulation JSON

### Outils utiles

- [JSONLint](https://jsonlint.com/) - Validation JSON
- [Postman](https://www.postman.com/) - Test d'API
- [DB Browser for SQLite](https://sqlitebrowser.org/) - Interface SQLite

---

## ✅ Checklist de migration

- [ ] Installer `requests` (`pip install requests`)
- [ ] Créer `api_client.py`
- [ ] Créer `results_filter.py`
- [ ] Créer `matches_filter.py`
- [ ] Tester chaque endpoint individuellement
- [ ] Créer la structure de base de données
- [ ] Intégrer les filtres avec la BDD
- [ ] Supprimer l'ancien code de scraping HTML
- [ ] Tester le système complet
- [ ] Mettre en production

---

## 📝 Notes finales

### Avantages de cette approche

1. **Performance** : 10x plus rapide que le scraping
2. **Maintenabilité** : Code plus simple et lisible
3. **Fiabilité** : Moins de risques de pannes
4. **Scalabilité** : Facile d'ajouter de nouvelles fonctionnalités

### Points d'attention

⚠️ **Surveiller** : Le `App-Version` peut changer lors des mises à jour du site  
⚠️ **Respecter** : Ne pas spammer l'API (ajouter des délais si nécessaire)  
⚠️ **Sauvegarder** : Toujours garder une copie de vos données  

---

**Version** : 2.1  
**Date** : Janvier 2025  
**Auteur** : GODMOD Team  

🎉 **Félicitations ! Vous êtes passé de Noob à Pro !** 🎉
