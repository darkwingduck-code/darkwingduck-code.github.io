---
title: "Concevoir un déploiement sans interruption : feature flags, canaris, compatibilité des schémas et rollback"
date: 2026-07-21 12:08:00 +0900
categories: [DevOps, Deployment]
tags: [zero-downtime, canary, feature-flags, rollback, schema-migration]
description: Concevoir le déploiement sans interruption comme un problème de coexistence des versions, de migration de base de données, de feature flags, de seuils d’arrêt automatiques et de reprise, au-delà du simple basculement du trafic.
lang: fr-FR
translation_key: zero-downtime-deployment-feature-flags-canary
mermaid: true
hidden: true
---
{% include language-switcher.html %}

## Problème : une nouvelle instance saine ne garantit pas un déploiement sûr

Le déploiement sans interruption ne se résume pas au déplacement progressif du trafic dans un équilibreur de charge.

Au moins deux versions coexistent pendant le déploiement.

La base de données, le cache, les files d’attente et les clients coexistent eux aussi dans des versions différentes.

Ignorer cette réalité entraîne les problèmes suivants.

- Le nouveau code échoue en lisant un champ avant la migration qui l’ajoute.
- L’ancien code ne sait pas analyser le message produit par le nouveau.
- Un rollback a lieu alors que le schéma et les données ont déjà changé de manière irréversible.
- Après le passage de la readiness, un cache froid fait exploser la latence.
- La faible proportion du canari ne révèle pas les erreurs des chemins rares.
- Le feature flag devient une branche permanente et le nombre de combinaisons de test explose.
- Les métriques de santé sont normales, mais le taux de conversion d’un parcours essentiel diminue.

## Modèle mental : une release est la somme de plusieurs transitions indépendantes

```mermaid
flowchart LR
    A[Déploiement de l'artefact] --> B[Readiness de l'instance]
    B --> C[Basculement du trafic]
    C --> D[Exposition de la fonctionnalité]
    D --> E[Nettoyage du schéma]
    E --> F[Release terminée]
```

Chaque étape doit pouvoir être interrompue et annulée séparément.

### Séparer déploiement et release

- **déploiement** : installer l’artefact de code dans l’environnement d’exécution ;
- **release** : exposer la fonctionnalité aux utilisateurs.

Un feature flag permet de déployer d’abord le code et de contrôler plus tard son exposition.

Mais les pannes du système de flags et les configurations obsolètes deviennent de nouvelles dépendances.

### Distinguer rollback et roll-forward

Lorsque seul l’artefact doit être annulé, le rollback est rapide.

Si une migration de données ou des effets externes se sont déjà produits, déployer une version corrective vers l’avant peut être plus sûr.

Déterminez avant le déploiement les conditions qui déclenchent chaque stratégie.

## Workflow : rendre les changements compatibles

### Étape 1. Rendre l’unité de déploiement immuable

Associez à l’artefact un condensat de contenu et la provenance du build.

Une même étiquette de version ne doit jamais désigner des octets différents.

Suivez ensemble les versions de la configuration, des feature flags et des migrations.

### Étape 2. Rendre l’API compatible dans les deux sens

Pendant le rollout, testez les couples ancien client/nouveau serveur et nouveau client/ancien serveur.

Commencez par rendre tout nouveau champ facultatif.

Ignorez sans danger les champs inconnus.

Ne modifiez pas le sens d’un champ existant.

Si un nouveau comportement est nécessaire, envisagez une version explicite ou une négociation des capacités.

### Étape 3. Appliquer la stratégie expand-and-contract à la base de données

1. Déployer d’abord un schéma additif.
2. Vérifier que l’ancien code fonctionne toujours avec le nouveau schéma.
3. Déployer le nouveau code de façon qu’il traite les anciens et nouveaux champs.
4. Si nécessaire, effectuer une double écriture et une réconciliation.
5. Réaliser le backfill en limitant son débit.
6. Basculer le chemin de lecture vers le nouveau champ.
7. Supprimer l’ancien champ une fois toutes les anciennes versions disparues.

Testez les verrous DDL et les risques de réécriture de table avec un volume de données proche de la production.

### Étape 4. Faire de la readiness une condition de sécurité du trafic

Le simple démarrage du processus ne signifie pas qu’il est prêt.

- chargement de la configuration terminé ;
- initialisation locale indispensable terminée ;
- écouteur prêt ;
- dépendances indispensables joignables ;
- version du schéma compatible ;
- préchauffage terminé ou non.

Ne transformez pas une panne temporaire d’une dépendance externe en redémarrage de liveness.

### Étape 5. Choisir une cohorte canari représentative

Un pourcentage aléatoire de requêtes peut être insuffisant.

Tenez compte du tenant, de la région, de l’appareil, de l’endpoint et de la forme des données.

Il est possible de commencer par une cohorte interne ou à faible risque.

Avec des sessions persistantes et des workflows avec état, examinez le risque qu’un même utilisateur passe d’une version à l’autre.

### Étape 6. Fixer à l’avance les métriques d’arrêt automatique

Choisir pendant le déploiement les métriques à observer crée un biais de confirmation.

Comparez au minimum :

- le taux d’erreurs des requêtes ;
- les percentiles de latence ;
- la saturation ;
- les erreurs des dépendances ;
- le taux de nouvelles tentatives ;
- l’âge des messages en file ;
- le taux de réussite des processus métier essentiels ;
- les invariants de qualité des données.

Comparez le canari et la baseline sur la même plage horaire et avec des caractéristiques de trafic similaires.

### Étape 7. Concevoir le cycle de vie des feature flags

Les métadonnées du flag doivent contenir :

- le propriétaire ;
- l’objectif et le risque ;
- les dates de création et d’expiration ;
- la valeur par défaut ;
- le comportement fail-open ou fail-closed ;
- la cohorte ciblée ;
- l’issue de suppression ;
- l’historique d’audit.

Ne confiez pas uniquement à un flag côté client une décision de sécurité telle que l’autorisation ou le paiement.

Le serveur doit appliquer la politique finale.

### Étape 8. Répéter réellement le rollback

Vérifiez que l’artefact précédent démarre avec le schéma actuel.

Vérifiez la compatibilité du cache et des messages en file.

Consignez dans un runbook l’ordre du basculement du trafic, de la désactivation du flag, du rollback de l’artefact et de celui de la configuration.

Incluez aussi la durée du rollback dans le RTO.

### Étape 9. Prévoir une fenêtre d’observation suffisante

Un canari trop court laisse passer les workflows rares, les limites de batch et les fuites mémoire.

Fixez la durée de chaque étape en fonction du volume de trafic et de la puissance de détection des défaillances.

Pour les fonctions à cycle long, comme un batch quotidien ou un renouvellement, complétez avec un mode fantôme ou un test par rejeu.

### Étape 10. Déclarer la release terminée

Atteindre 100 % du trafic n’est pas la fin.

- budget d’erreur revenu à la normale ;
- migration et réconciliation terminées ;
- anciennes instances supprimées ;
- utilisation de l’ancien schéma à zéro ;
- plan de suppression des flags temporaires confirmé ;
- runbook et documentation mis à jour ;
- résultats et motifs des décisions consignés.

La release n’est terminée qu’une fois ces conditions remplies.

## Exemple pratique : basculer les lectures vers une nouvelle colonne

### Phase A : expansion

Ajoutez une nouvelle colonne nullable.

L’ancienne application ignore cette colonne.

### Phase B : double écriture

La nouvelle application écrit dans l’ancienne et la nouvelle colonne.

Comparez les résultats des écritures au moyen de métriques et de requêtes échantillonnées.

### Phase C : backfill

Mettez à jour les lignes historiques par petits lots.

Surveillez le retard des réplicas, l’attente des verrous, le journal des transactions et la latence utilisateur.

Prévoyez un curseur pour interrompre et reprendre l’opération.

### Phase D : basculement des lectures

À l’aide d’un feature flag, faites lire la nouvelle colonne à une partie des cohortes.

Comparez les différences de résultat et la réussite métier.

### Phase E : contraction

Supprimez l’ancienne colonne après le basculement de tous les lecteurs et l’expiration de la fenêtre de rollback.

Réalisez la migration de suppression dans un changement distinct.

## Comparaison des stratégies de déploiement

### Rolling

Le coût d’environnements supplémentaires est faible.

La coexistence des versions étant la règle, la compatibilité est indispensable.

### Blue/Green

Le basculement par environnement et le rollback rapide du trafic sont faciles.

Si le magasin de données est partagé, les risques liés aux changements de base de données demeurent.

### Canary

Une faible exposition permet de mesurer les risques dans l’environnement réel.

Un trafic représentatif et un échantillon suffisant sont nécessaires.

### Shadow

Les requêtes réelles sont dupliquées, sans renvoyer la réponse aux utilisateurs.

Les effets secondaires des écritures doivent être supprimés ou isolés.

### Feature flag

L’exposition de la fonctionnalité est séparée du déploiement.

La dette des flags et la complexité des combinaisons doivent être gérées activement.

## Checklist de validation

### Compatibilité

- [ ] Les couples ancien/nouveau client et serveur ont-ils été testés ?
- [ ] Le changement de schéma commence-t-il par une étape additive ?
- [ ] La compatibilité des anciens et nouveaux consommateurs de messages a-t-elle été vérifiée ?
- [ ] L’artefact précédent fonctionne-t-il avec le schéma actuel ?
- [ ] Les changements irréversibles font-ils l’objet d’une approbation distincte ?

### Rollout

- [ ] La cohorte canari est-elle représentative ?
- [ ] Le pourcentage de trafic et la durée d’observation sont-ils définis pour chaque étape ?
- [ ] Le seuil d’abandon est-il fixé avant le déploiement ?
- [ ] Les SLI métier et techniques sont-ils examinés ensemble ?
- [ ] Existe-t-il un chemin d’arrêt manuel en cas d’échec de l’automatisation ?

### Feature flag

- [ ] Le propriétaire et la date d’expiration sont-ils définis ?
- [ ] La valeur par défaut et le comportement en cas de panne sont-ils sûrs ?
- [ ] Le contrôle des autorisations côté serveur est-il maintenu ?
- [ ] Les tests de combinaisons de flags couvrent-ils les chemins risqués ?
- [ ] Le travail de suppression après rollout est-il suivi ?

### Récupération

- [ ] Le rollback du trafic a-t-il été répété ?
- [ ] Les versions de la configuration et des secrets peuvent-elles être restaurées ?
- [ ] La migration peut-elle être interrompue et reprise ?
- [ ] Existe-t-il des procédures de correction et de compensation des données ?
- [ ] Les fonctions utilisateur sont-elles vérifiées après la récupération ?

## Échecs fréquents et limites

### Promettre une disponibilité absolue de 100 %

Imposer l’absence totale d’interruption à chaque changement peut ajouter une complexité dangereuse.

Lorsque l’activité le permet, une courte interruption planifiée peut être plus sûre.

### Juger le canari avec le seul taux d’erreurs

La latence, l’exactitude des données et la dégradation des résultats métier constituent des signaux distincts.

### Considérer le rollback comme universel

Un e-mail externe, un paiement ou une mutation irréversible des données ne sont pas annulés par le rollback d’un artefact.

Une compensation et un roll-forward sont nécessaires.

### Détourner les flags en système de gestion de configuration

Distinguez les paramètres permanents des contrôles temporaires de release.

### Regrouper la migration et le déploiement de l’application

La surface de défaillance s’agrandit et il devient difficile d’isoler l’étape fautive.

## Références officielles

- [Mise à jour progressive des Deployment Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment)
- [Documentation d’Argo Rollouts](https://argo-rollouts.readthedocs.io/)
- [Spécification OpenFeature](https://openfeature.dev/specification/)
- [AWS Builders' Library : garantir la sûreté des rollbacks](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/)
- [Google SRE Workbook : releases canaris](https://sre.google/workbook/canarying-releases/)

## Conclusion

Le déploiement sans interruption ressemble davantage à un contrat de coexistence des versions qu’à un simple basculement de trafic.

Faites de l’artefact, de l’API, du schéma, des messages, des flags et de l’exposition utilisateur des étapes indépendantes, puis validez les conditions d’arrêt de chacune.

Une release sûre exige non seulement de savoir déployer rapidement, mais aussi de détecter tôt un changement erroné et de récupérer dans un périmètre limité.
