---
title: "Démarrer un projet de machine learning : cadrage du problème, contrats de données, prévention des fuites et baselines"
date: 2026-07-21 08:00:00 +0900
categories: [AI, Machine Learning]
tags: [machine-learning, problem-framing, data-contract, data-leakage, baseline]
description: Un workflow reproductible pour fixer le problème de décision, l’instant d’observation, le contrat de données, les contrôles de fuite et la conception des baselines avant de choisir un modèle.
math: true
mermaid: true
lang: fr-FR
translation_key: ml-problem-framing-data-contract-baseline
hidden: true
---

{% include language-switcher.html %}

Un bon système de machine learning ne commence pas par un modèle complexe. Il commence par préciser **qui utilisera quelles informations, à quel moment, pour mieux choisir quelle action**. Si cette question reste floue, même un score de validation élevé ne se traduira pas en valeur réelle.

Cet article se concentre sur les problèmes de prédiction tabulaire, mais les mêmes principes s’appliquent aux séries temporelles, à la détection d’anomalies, à la recommandation et au Scientific ML.

## 1. Problème : où les projets échouent avant même le modèle

Un projet de machine learning courant échoue selon la séquence suivante.

1. La question métier est directement traduite en problème de classification ou de régression.
2. Toutes les colonnes faciles à obtenir depuis la base de données actuelle sont utilisées comme features.
3. Les données d’entraînement et de validation sont séparées aléatoirement.
4. Le modèle au score le plus élevé est sélectionné.
5. Au déploiement, les informations disponibles pendant l’entraînement sont absentes, la prédiction arrive trop tard ou l’action coûte plus cher que son bénéfice.

La cause profonde est que **la cible de prédiction, les informations observables, l’instant de décision et le résultat de l’action** n’ont jamais été fixés dans un contrat unique.

### Cadrer un problème de décision, pas un problème de prédiction

La phrase « prédire un événement » ne suffit pas. Il faut au minimum répondre aux questions suivantes.

| Élément | Question indispensable |
|---|---|
| Unité de prédiction | Une ligne représente-t-elle une personne, une machine, une transaction, un intervalle ou une session ? |
| Instant de référence | À quel instant précis le modèle est-il appelé ? |
| Fenêtre d’observation | Jusqu’à quelle période les informations peuvent-elles être utilisées ? |
| Horizon de prédiction | Combien de temps après l’instant de référence le résultat est-il prédit ? |
| Action | Qu’est-ce qui change réellement lorsque le score est élevé ou faible ? |
| Coût | Quels sont les coûts respectifs des faux positifs, des faux négatifs, de la latence et de l’examen ? |
| Contraintes | Quelles sont les limites de temps de réponse, d’explicabilité, de personnel disponible et de réglementation ? |

Même avec des données identiques, passer d’un horizon de prédiction de dix minutes à trente jours modifie le label, les features, la méthode de validation et les actions possibles.

### La fuite de données dépasse « l’inclusion accidentelle de la colonne de réponse »

Une fuite de données désigne tout cas où une information indisponible au moment du déploiement entre dans l’entraînement ou l’évaluation.

- **Fuite de cible** : utilisation d’un code d’état ou d’un enregistrement de suivi créé après la survenue du résultat
- **Fuite temporelle** : rattachement à une ligne historique de statistiques sur toute la période, de corrections futures ou de valeurs finalisées ultérieurement
- **Fuite de séparation** : placement de lignes issues de la même entité ou du même événement à la fois dans l’entraînement et la validation
- **Fuite de prétraitement** : ajustement préalable de l’imputation, de la mise à l’échelle ou de la sélection de features sur l’ensemble des données
- **Fuite de label** : définition du label par une règle pratiquement identique à une feature d’entrée
- **Fuite opérationnelle** : utilisation d’une colonne disponible hors ligne, mais qui arrive trop tard sur le chemin d’inférence en ligne

Une fuite ne peut pas être jugée à partir des seuls noms de colonnes. Il faut savoir **quand une valeur est générée, quand elle est finalisée et quand elle devient interrogeable**.

## 2. Modèle mental : contrats et minimisation du risque sur une chronologie

### Attribuer à chaque ligne un « instant de référence »

Chaque ligne de prédiction possède un instant de référence \(t_0\). Les features ne sont calculées qu’à partir des informations observables jusqu’à \(t_0\), tandis que le label est défini sur l’intervalle qui suit.

\[
X_i = g\left(\mathcal{H}_i(t \le t_0)\right), \qquad
y_i = h\left(\mathcal{H}_i(t_0 < t \le t_0 + H)\right)
\]

- \(\mathcal{H}_i\) : historique des événements du sujet \(i\)
- \(t_0\) : instant de référence de la prédiction
- \(H\) : horizon de prédiction
- \(g\) : fonction qui construit les features à partir des informations passées
- \(h\) : fonction qui construit le label à partir de l’intervalle futur

Rendre cette notation explicite prévient à l’avance de nombreuses formes de fuite.

```mermaid
flowchart LR
    A["Fenêtre d’observation passée"] --> B["Instant de référence t0"]
    B --> C["Score du modèle"]
    C --> D["Action ou examen"]
    B --> E["Fenêtre future du label"]
    D --> F["Coûts et bénéfices"]
    E --> F
```

### Le score d’un modèle est une entrée de la décision, pas l’objectif lui-même

Un modèle produit généralement \(s(x)\) ou une probabilité \(p(y=1\mid x)\). L’objectif réel n’est pas seulement de réduire la loss du modèle, mais de réduire le coût attendu de la politique de décision \(a(s)\).

\[
R(a) = \mathbb{E}\left[C\bigl(Y, a(s(X))\bigr)\right]
\]

Un modèle à l’AUC plus élevée ne produit donc pas nécessairement une meilleure politique opérationnelle. La calibration des probabilités, les seuils, la capacité d’examen et les effets des actions doivent être considérés ensemble.

### Un contrat de données est un contrat sémantique, pas seulement un schéma

Un schéma définit des noms et des types de données. Un contrat de données ajoute les éléments suivants.

- Signification d’une ligne et clé unique
- Instant de l’événement et instant d’ingestion
- Plages autorisées, unités et signification des valeurs manquantes
- Producteur des données et fréquence de mise à jour
- Disponibilité au moment du déploiement
- Possibilité de corrections et d’arrivées tardives
- Traitement des violations de qualité

Le code du modèle suppose implicitement un contrat de données. La reproductibilité et la maintenabilité exigent que ces hypothèses soient explicitées dans la documentation et la validation automatisée.

## 3. Workflow pratique

### Étape 1. Commencer par rédiger une fiche de décision

Avant la modélisation, fixez les éléments suivants sur une page.

```yaml
decision:
  unit: "한 번의 평가 대상"
  as_of_time: "모델 호출 직전 시각"
  observation_window: "t0 이전의 고정 길이 구간"
  prediction_horizon: "t0 이후의 결과 관측 구간"
  action: "점수 구간별 검토 또는 개입"
  capacity: "단위 시간당 처리 가능한 최대 건수"

label:
  definition: "미래 구간에서 관측되는 객관적 조건"
  maturity_delay: "레이블이 최종 확정되기까지의 시간"
  exclusions: "판정 불가능하거나 중도 절단된 사례"

constraints:
  max_latency_ms: 200
  explainability: "개별 판단 근거 제공"
  fallback: "모델 또는 특징 장애 시 기본 정책"
```

Choisissez les valeurs en fonction des exigences du système, mais placez-les toujours sous contrôle de version. Modifier la définition du label n’est pas une simple édition du code : cela change le problème lui-même.

### Étape 2. Vérifier la validité du label et le biais d’observation

Un label n’est généralement pas la vérité du monde, mais **le résultat d’une procédure de mesure**. Il faut poser les questions suivantes.

- Le résultat est-il observé de la même manière pour chaque sujet ?
- Le statut positif ou négatif n’est-il connu que pour les sujets testés ?
- Une politique existante a-t-elle déterminé qui serait testé et introduit un biais de sélection ?
- Les labels négatifs récents sont-ils encore immatures à cause du délai de finalisation ?
- Les arbitres humains sont-ils en désaccord ?
- Les cas « non observés » ont-ils été traités à tort comme « négatifs » ?

Avec des labels de mauvaise qualité, un modèle plus complexe ne fait qu’apprendre leur incertitude avec davantage de finesse. Il faut d’abord mettre en place des procédures telles que l’examen des échantillons contestés, les arbitrages multiples, des flags de labels faibles et l’exclusion des intervalles dont les labels sont incomplets.

### Étape 3. Enregistrer la provenance de chaque colonne et son instant de disponibilité

Il faut gérer un catalogue de features comme le suivant.

| Feature | Source | Version de la formule | Instant de l’événement | Délai de disponibilité | Unité | Signification de l’absence |
|---|---|---|---|---|---|---|
| Nombre récent | Journal d’événements | v2 | Instant de l’événement source | Minutes | count | Distinguer l’absence d’historique d’un échec de collecte |
| Statistique mobile | Agrégation de capteurs | v1 | Fin de la fenêtre | Secondes | Unité standard | Peut être exclue par un filtre de qualité |
| État catégoriel | Système opérationnel | v3 | Instant du changement d’état | Minutes | category | Distinguer une valeur non saisie d’un cas non applicable |

Une jointure point-in-time pour l’entraînement n’est pas une simple jointure de clés. Elle doit récupérer la valeur la plus récente disponible au plus tard à l’instant de chaque prédiction.

```sql
-- 개념 예시: 실제 문법은 데이터 엔진에 맞게 조정한다.
SELECT p.entity_id, p.as_of_time, f.feature_value
FROM prediction_points p
LEFT JOIN feature_history f
  ON p.entity_id = f.entity_id
 AND f.available_at <= p.as_of_time
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY p.entity_id, p.as_of_time
  ORDER BY f.available_at DESC
) = 1;
```

`event_time <= as_of_time` peut ne pas suffire. Si un événement s’est produit dans le passé mais est entré tardivement dans le système, utilisez `available_at` comme critère.

### Étape 4. Fixer la stratégie de séparation avant le modèle

La séparation doit simuler l’environnement de déploiement.

- Utilisez une séparation chronologique lorsque vous prédisez l’avenir.
- Utilisez une séparation par groupe lorsque vous généralisez à de nouveaux utilisateurs ou de nouvelles machines.
- Utilisez une séparation par domaine lors d’un transfert entre sites ou institutions.
- Séparez par ID d’événement lorsque plusieurs lignes proviennent du même événement.
- En cas de tuning répété, conservez l’intervalle de test final scellé jusqu’à la fin.

Le prétraitement doit être ajusté uniquement dans chaque fold d’entraînement.

```python
# 실행 가능한 특정 라이브러리 코드가 아니라 구조를 보여 주는 의사코드다.
for train_idx, valid_idx in splitter.split(rows, groups=entity_ids, time=as_of_time):
    preprocess = Preprocessor().fit(rows[train_idx])
    X_train = preprocess.transform(rows[train_idx])
    X_valid = preprocess.transform(rows[valid_idx])

    model = Model(config).fit(X_train, y[train_idx])
    predictions[valid_idx] = model.predict_proba(X_valid)
```

### Étape 5. Construire une échelle de baselines

Une baseline n’est pas une formalité destinée à produire un score faible. Elle sert de référence pour décider si une nouvelle complexité crée une valeur réelle.

1. **Baseline de politique** : la règle actuelle ou une politique consistant à ne rien faire
2. **Baseline constante** : moyenne globale, médiane, dernière valeur ou classe majoritaire
3. **Règle à une seule feature** : un ou deux signaux supposés être les plus forts
4. **Modèle statistique simple** : modèle linéaire ou logistique régularisé
5. **Modèle non linéaire** : famille d’arbres ou de réseaux neuronaux qui apprend les interactions
6. **Ensemble** : seulement si le gain justifie la complexité opérationnelle et le coût de calcul

Comparez chaque étape avec la même séparation, les mêmes métriques et les mêmes hypothèses de coût. Si l’amélioration moyenne d’un modèle complexe est faible et sa variance élevée, un modèle simple peut être préférable.

### Étape 6. Enregistrer complètement chaque unité d’expérience

Une expérience doit au minimum être identifiée par le tuple suivant.

\[
E = (D, L, S, F, M, H, C, R)
\]

- \(D\) : snapshot des données
- \(L\) : version de la définition du label
- \(S\) : spécification de la séparation
- \(F\) : code et liste des features
- \(M\) : version de l’implémentation du modèle
- \(H\) : hyperparamètres
- \(C\) : environnement d’exécution
- \(R\) : seeds aléatoires et informations de répétition

Les scores seuls ne permettent pas de reproduire un résultat. Enregistrer les expériences échouées avec leur motif de rejet évite de reprendre le même chemin.

### Étape 7. Traduire les métriques hors ligne en politique opérationnelle

Pour un problème de classification, il ne faut pas rapporter un seul seuil ; il faut examiner ensemble les éléments suivants.

- ROC-AUC et PR-AUC
- Précision, rappel et spécificité selon le seuil
- Calibration des probabilités et courbes de fiabilité
- Taux de succès et taux de capture dans les \(k\) % supérieurs
- Performances selon le temps, le groupe et les sous-groupes importants
- Coût attendu reflétant la capacité de traitement
- Performances lorsque les entrées sont absentes ou retardées

Pour la régression, examinez la direction des résidus, les plages extrêmes, la couverture des intervalles de prédiction et les erreurs près des frontières de décision, en plus de la MAE ou de la RMSE.

## 4. Checklist d’évaluation et de vérification

### Définition du problème

- [ ] L’unité de prédiction, l’instant de référence, la fenêtre d’observation et l’horizon de prédiction sont précisés.
- [ ] L’action produite par un score du modèle est définie.
- [ ] Les coûts des faux positifs, des faux négatifs, de la latence et de l’examen sont distingués.
- [ ] Le délai de finalisation du label et les règles de censure sont définis.

### Contrats de données et fuites

- [ ] L’instant de génération et l’instant de disponibilité opérationnelle de chaque feature sont connus.
- [ ] Des jointures point-in-time correctes sont utilisées.
- [ ] Les lignes issues de la même entité ou du même événement ne franchissent pas les frontières de séparation.
- [ ] Le prétraitement et la sélection de features sont ajustés uniquement dans les folds d’entraînement.
- [ ] Les agrégats sur toute la période, les états postérieurs au résultat et les valeurs finales corrigées ont été vérifiés.
- [ ] Les valeurs manquantes distinguent les cas « aucun », « non mesuré » et « échec de collecte ».

### Baselines et validation

- [ ] Des baselines existent pour la politique actuelle, les constantes et les modèles simples.
- [ ] Les séparations temporelles, par groupe ou par domaine simulent l’environnement de déploiement.
- [ ] La variabilité a été vérifiée sur plusieurs seeds ou fenêtres temporelles.
- [ ] Les intervalles d’incertitude et le sous-groupe le moins performant sont rapportés, et pas seulement les moyennes.
- [ ] Les données de test finales sont restées scellées jusqu’à la fin de la prise de décision.

### Faisabilité opérationnelle

- [ ] Le calcul des features à l’entraînement et au service possède une signification identique.
- [ ] La latence, la mémoire, le débit et la fraîcheur des features ont été mesurés.
- [ ] Un fallback est défini en cas de panne du modèle ou de features manquantes.
- [ ] Les métriques de monitoring ainsi que les critères de réentraînement et de rollback sont définis.

## 5. Limites et précautions

Premièrement, un contrat de données complet ne garantit pas la véracité des données. Les erreurs de capteurs, les biais d’arbitrage et les changements de pratique d’enregistrement exigent des enquêtes de qualité et des connaissances métier distinctes.

Deuxièmement, une bonne validation hors ligne ne démontre pas automatiquement l’effet causal d’une intervention. Prédire avec précision et améliorer les résultats en agissant sur les prédictions sont deux questions différentes. Il faut vérifier les effets réels de la politique par des méthodes comme un déploiement progressif, des expériences randomisées ou des plans quasi expérimentaux.

Troisièmement, les labels et les environnements évoluent. La définition initiale du problème est une hypothèse versionnée, et non un contrat permanent. Lorsqu’elle change, il faut enregistrer ce qui a changé et pourquoi afin que les résultats passés restent comparables.

Enfin, le modèle le plus précis n’est pas toujours le meilleur. En pratique, le meilleur modèle peut être celui dont le **risque système total** est le plus faible, en tenant compte de la fraîcheur des données, de l’explicabilité, de la reprise après défaillance et du coût de maintenance.
