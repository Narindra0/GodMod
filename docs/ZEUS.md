⚡ Projet ZEUS : L'Intelligence Artificielle Autonome

📖 Introduction

Le module Zeus représente l'évolution ultime du projet GODMOD. Il s'agit d'un moteur d'apprentissage par renforcement (Reinforcement Learning) conçu pour s'affranchir des formules humaines et développer ses propres stratégies de pronostics en fonction des résultats réels constatés en base de données.

🏗️ 1. Architecture du Modèle Zeus

Zeus ne suit plus de "Poids" (ex: 40% classement). Il utilise un cycle de rétroaction (feedback loop) basé sur quatre éléments fondamentaux :

A. L'Agent (Le Cerveau)

L'algorithme de Machine Learning (ex: Deep Q-Network ou PPO) qui prend les décisions.

B. L'Environnement (Les Données)

Toutes vos archives SQLite. Zeus "voit" le championnat comme une suite d'états (State).

C. L'Action

Pour chaque match, Zeus peut choisir :

Action 0 : Parier sur le Favori (1)

Action 1 : Parier sur le Nul (X)

Action 2 : Parier sur l'Outsider (2)

Action 3 : S'abstenir (Passer)

D. La Récompense (Reward)

C'est le seul guide de Zeus. On le "punit" en cas de perte et on le "récompense" en cas de gain.

Gain : + 10

Perte : - 15 (Pénalité plus forte pour favoriser la prudence)

Abstention pertinente : +2 (Récompense pour avoir évité un piège)

🧠 2. Le Vecteur d'État (Ce que Zeus analyse)

Au lieu de calculer un score, nous fournissons à Zeus un "Vecteur" (une liste de nombres bruts) pour chaque match :

Différentiel de Classement : (Pos_Dom - Pos_Ext) / 20

Vitesse de Forme : Évolution de la forme sur les 3 derniers matchs.

Puissance d'Attaque : Moyenne de buts marqués (Dom/Ext).

Fragilité Défensive : Moyenne de buts encaissés.

Cotes du Marché : Les trois cotes brutes du site.

Cycle de la Session : Numéro de la journée (J1 à J38).

🚀 3. Avantages par rapport au Système Classique

Détection de Patterns non-linéaires : Zeus peut comprendre que "l'avantage domicile" ne vaut rien après la J30, ou que certaines équipes "lâchent" après 3 défaites consécutives.

Adaptabilité Totale : Si l'algorithme du site de paris est mis à jour, Zeus le détectera via la chute de ses récompenses et ajustera sa stratégie sans intervention humaine.

Gestion de l'Incertitude : Zeus apprendra naturellement à "passer" son tour sur les matchs où la probabilité de gain est inférieure au risque de perte.

🛠️ 4. Plan d'Implémentation (Roadmap)

Phase A : Préparation des données (Data Engineering)

Normaliser les données (mettre toutes les valeurs entre 0 et 1).

Phase B : Entraînement à froid (Offline Training)

Entraîner le modèle sur les 1match qui se fait au moment et de le faire au donne actuelle si y a pas d archives.

Objectif : Atteindre un taux de réussite stable en simulation.

Phase C : Mode "Ombre" (Shadow Mode)

Intégrer Zeus dans le programme principal, mais sans afficher ses choix.

Comparer ses résultats avec ceux de l'IA Classique (Phase 3) pendant 5 sessions.

Phase D : Déploiement (Live)

Activer Zeus comme moteur principal.

Conserver l'IA Classique comme "système de secours" (Fail-safe).

📉 5. Exemple de Logique Zeus

Scénario : Match entre le 1er et le 18ème. Cote du 1er : 1.25.

IA Classique : "Score de confiance élevé (18.5), je parie sur le 1er."

Module Zeus : "J'ai remarqué qu'historiquement, les favoris à 1.25 perdent 25% du temps après une série de 5 victoires. La récompense attendue est négative. Action choisie : Passer."

Ce document sert de base pour le développement du futur module zeus_engine.py.

