# 🧠 GODMOD  
### Système Intelligent de Prédiction pour Matchs Virtuels de Football

---

## 📌 Présentation Générale

**GODMOD** est un système d’analyse statistique et prédictive dédié aux **matchs de football virtuel (English League)**.  
Il collecte automatiquement les données depuis **Bet261**, les analyse, puis sélectionne les **paris les plus fiables** selon des critères statistiques.

> 🎯 Objectif principal : **réduire le hasard** et **augmenter la fiabilité** des prédictions grâce aux données.

---

## 🎯 Objectifs du Projet

- Extraire automatiquement les données des matchs virtuels
- Stocker l’historique complet d’une session
- Analyser les performances des équipes
- Identifier les matchs les plus fiables
- Évaluer les performances du système
- Mettre en place une logique d’amélioration continue

---

## 🌐 Source des Données (Web Scraping)

Le projet ne repose sur **aucune API officielle**.  
Les données sont extraites via **web scraping** depuis le site Bet261.

### 🔗 URLs utilisées
- 📊 Résultats :  
  https://bet261.mg/virtual/category/instant-league/8035/results
- 🎰 Matchs & cotes :  
  https://bet261.mg/virtual/category/instant-league/8035/matches
- 🏆 Classement :  
  https://bet261.mg/virtual/category/instant-league/8035/ranking

---

## 🏆 League Analysée – English Virtual League

### ⚽ Équipes (20)

London Reds, Manchester Blue, Manchester Red, Wolverhampton, N. Forest, Fulham, West Ham, Spurs, London Blues, Brighton, Brentford, Everton, Aston Villa, Leeds, Sunderland, Crystal Palace, Liverpool, Newcastle, Burnley, Bournemouth

---

## ⏱️ Structure Temporelle des Matchs

- **1 session** : 38 journées  
- **1 journée** : 10 matchs  
- **Durée d’une journée** : 45 secondes  
- **Reset** : nouvelle session = nouvelles données

---

## 📊 Analyse & Prédiction

Le moteur GODMOD analyse :
- Cotes (1 / X / 2)
- Classement
- Points
- Forme récente (5 derniers matchs)

---

## 🎰 Sélection des Paris

- Analyse à partir de la journée 10
- Sélection de 2 à 3 matchs maximum
- Exclusion des matchs à faible fiabilité

---

## 📈 Système de Points

- ✅ Bonne prédiction : +5 points  
- ❌ Mauvaise prédiction : -8 points  

---

## ⚠️ Avertissement

Projet à but éducatif et analytique uniquement.

