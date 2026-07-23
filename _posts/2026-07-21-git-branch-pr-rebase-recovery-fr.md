---
title: "Branches, PR, merge et rebase : un guide de reprise Git sans risque"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: Apprenez à choisir une stratégie d’intégration des PR à partir du graphe des branches et des commits, puis à corriger les erreurs sans perdre de données.
lang: fr-FR
translation_key: git-branch-pr-rebase-recovery
hidden: true
---

{% include language-switcher.html %}

## Problème : les incidents Git s’aggravent quand on oublie que l’historique est partagé, pas à cause d’une commande

La méthode de reprise change entièrement selon que la même erreur n’existe encore qu’en local ou qu’elle a déjà été publiée sur un dépôt distant. On peut réécrire assez librement des commits locaux, mais modifier par rebase ou push forcé des commits publics sur lesquels d’autres personnes ont fondé leur travail perturbe à la fois leur historique et les points de référence de la CI.

Trois questions suffisent pour prendre une décision sûre.

1. La modification à ne pas perdre se trouve-t-elle dans l’arbre de travail, la zone de staging ou un commit ?
2. Quelqu’un d’autre a-t-il déjà récupéré le commit concerné ?
3. Le résultat recherché consiste-t-il à le compenser par un nouvel historique ou à réécrire l’historique existant ?

Ne commencez pas par une commande de reprise. Capturez d’abord l’état et le graphe.

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Modèle mental : une branche est un nom qui pointe vers un commit

Voir une branche comme une « copie de dossier » complique la compréhension du merge et du rebase. Une branche est une référence légère qui pointe vers un identifiant de commit.

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature` pointe vers `F2`, tandis que `main` pointe vers `M3`. Trois méthodes principales permettent d’intégrer les deux branches.

| Méthode | Résultat | Situation adaptée | Point d’attention |
|---|---|---|---|
| commit de merge | Crée un commit d’intégration ayant deux parents | Préserver la structure des branches et les commits individuels | L’historique peut se complexifier |
| squash merge | Intègre les modifications de la PR dans un seul nouveau commit | Petites fonctionnalités et commits de travail non nettoyés | Les limites entre les commits de la PR disparaissent |
| rebase + fast-forward | Rejoue les commits de la fonctionnalité sur la base la plus récente | Conserver à la fois un historique linéaire et des commits porteurs de sens | Les identifiants de commit changent : prudence lors de la réécriture d’un historique public |

Avant le rebase :

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

Après avoir rebasé `feature` sur `main` :

```text
M1---M2---M3---F1'---F2'  feature
```

Même si `F1'` et `F2'` ont un contenu semblable, ce sont de nouveaux objets, avec d’autres parents et identifiants de commit. Le rebase ne « déplace » pas vraiment les commits : il **recrée les patchs** sur une nouvelle base.

### Une PR est une unité de contrôle des changements qui dépasse Git

Une pull request associe une comparaison de branches aux éléments suivants.

- Discussion et justification de la conception
- Tests automatisés et analyse statique
- Approbation des propriétaires du code
- Règles de protection de l’environnement de déploiement
- Décision d’intégration auditable

Une bonne PR n’est donc pas simplement « un endroit où déposer du code », mais un dossier réunissant les risques du changement, les preuves de validation et les méthodes de rollback.

## Modèle pratique : branches courtes, intégration explicite et instantané avant la reprise

### Flux de base pour une petite branche de fonctionnalité

```bash
git switch main
git fetch origin
git merge --ff-only origin/main

git switch -c feature/health-endpoint

# 편집과 테스트 후
git add --patch
git diff --staged
git commit -m "feat: add dependency-aware health endpoint"
git push --set-upstream origin feature/health-endpoint
```

Plus une branche vit peu de temps, plus la surface de conflit est réduite. Même une fonctionnalité importante peut être intégrée fréquemment à `main` en la découpant à l’aide de feature flags, de modifications d’interface préparatoires et du modèle expansion/contraction pour les migrations de données.

La description de la PR doit au minimum comporter les éléments suivants.

```markdown
## 왜 필요한가
<문제와 사용자 영향>

## 무엇이 바뀌는가
<핵심 설계와 범위 밖 항목>

## 어떻게 검증했는가
<테스트 명령, 관찰 결과, 수동 확인>

## 위험과 복구
<호환성, migration, feature flag, rollback>
```

### Deux façons de mettre une branche de fonctionnalité à jour par rapport à `main`

Si l’équipe suit un workflow fondé sur le merge :

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

Si elle suit un workflow fondé sur le rebase et que vous êtes, dans les faits, la seule personne à utiliser la branche de fonctionnalité :

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

Quand Git s’arrête sur un conflit, répétez la séquence suivante.

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

Si la résolution vous semble incertaine, revenez à l’état initial.

```bash
git rebase --abort
```

Si vous devez mettre à jour la branche de fonctionnalité distante existante après le rebase, utilisez la commande suivante plutôt qu’un simple `--force`.

```bash
git push --force-with-lease
```

`--force-with-lease` ne tente d’écraser la référence distante que si elle a encore la valeur observée en dernier. Cela ne garantit pas absolument la conservation de chaque nouveau push d’un collègue : les règles de protection des branches partagées et l’accord de l’équipe prévalent. N’autorisez pas les pushs forcés sur les branches protégées telles que `main`.

### Reprise sûre selon le type d’erreur

#### 1. Vous voulez supprimer une modification qui n’a pas été placée en staging

Lisez d’abord le diff et vérifiez qu’elle peut réellement être supprimée sans risque.

```bash
git diff -- <FILE>
git restore -- <FILE>
```

Comme `git restore` modifie le contenu de l’arbre de travail, il peut faire perdre des modifications non commitées. Indiquez précisément le nom du fichier ; en cas de doute, conservez d’abord la modification dans un fichier patch ou dans un commit sur une branche temporaire.

#### 2. Vous voulez seulement annuler `add` en conservant le contenu modifié

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

Cette opération retire seulement la modification du staging et laisse généralement intacte celle de l’arbre de travail.

#### 3. Vous voulez corriger le message du dernier commit local ou ajouter un fichier oublié

Vérifiez que le commit n’a pas encore été partagé.

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

Un amendement crée lui aussi un nouvel identifiant de commit. Si le commit a déjà été publié, il est généralement plus sûr d’ajouter un commit correctif.

#### 4. Vous voulez annuler l’effet d’un commit public erroné

Enregistrez la modification inverse dans un nouveau commit sans supprimer l’historique public.

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

Le revert d’un commit de merge exige de choisir le parent principal et peut influer sur de futurs merges. Dans ce cas, examinez le graphe et l’état du déploiement, puis suivez la procédure de l’équipe.

#### 5. Un commit semble avoir disparu après un reset ou un rebase

Dans la plupart des cas, l’objet n’a pas été supprimé immédiatement ; la branche a simplement cessé de pointer vers lui. Retrouvez le précédent `HEAD` dans le reflog.

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

Après avoir créé une branche de reprise, vérifiez les fichiers et les tests, puis effectuez un cherry-pick ou un merge dans la branche normale. Le reflog consigne les déplacements de références dans un dépôt local ; ce n’est pas une sauvegarde permanente. Les politiques de nettoyage et le passage du temps peuvent supprimer les objets.

#### 6. Vous avez travaillé sur une tout autre branche

Ne supprimez pas les modifications. Conservez-les dans un commit ou un stash à leur emplacement actuel, puis changez de branche. Un commit sur une branche temporaire est la méthode la plus facilement auditable.

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

Si vous ne voulez pas d’un commit WIP dans l’historique final, compressez-le lors de l’intégration de la PR ou nettoyez-le par rebase interactif avant sa publication.

### Les modes de `reset` se distinguent par la portée de leur action sur les trois zones

| Mode | Branche/HEAD | Zone de staging | Arbre de travail | Risque représentatif |
|---|---:|---:|---:|---|
| `--soft` | Déplacé | Conservée | Conservé | Choisir le mauvais point de l’historique |
| `--mixed` par défaut | Déplacé | Modifiée selon le commit cible | Conservé | L’état placé en staging est supprimé |
| `--hard` | Déplacé | Modifiée selon le commit cible | Modifié selon le commit cible | Perte du travail non commité |

`git reset --hard` n’est pas la première étape d’une reprise. S’il est nécessaire, conservez l’identifiant du commit courant et les modifications de l’arbre de travail en un point sûr distinct, vérifiez le commit cible avec `git show`, puis utilisez-le dans un périmètre limité. `revert` est le choix par défaut pour annuler un historique partagé.

### Intégrer les protections à la politique du dépôt

L’attention humaine ne peut pas protéger `main` à elle seule. Appliquez les règles suivantes dans les paramètres du dépôt.

- N’autoriser les modifications que par l’intermédiaire de PR
- Exiger la réussite des contrôles de statut
- Exiger un nombre minimal d’approbations et invalider les approbations devenues obsolètes
- Imposer l’examen du propriétaire via CODEOWNERS pour les chemins concernés
- Bloquer l’intégration tant que des conversations ne sont pas résolues
- Restreindre les pushs forcés et la suppression de branches
- Consigner les contournements par les administrateurs selon une procédure d’exception

## Liste de contrôle de validation

Avant d’intégrer une PR :

- [ ] Le périmètre de la modification vise un seul objectif.
- [ ] La branche de base est correcte et ne contient aucun commit ni fichier superflu.
- [ ] Les chemins d’échec et le rollback ont été examinés en plus des tests automatisés.
- [ ] La rétrocompatibilité des modifications de données, d’API et de configuration a été vérifiée.
- [ ] La méthode d’intégration — merge, squash ou rebase — respecte la politique du dépôt.
- [ ] Les métriques avant et après déploiement, ainsi que leurs responsables, sont clairement définis.

Avant d’exécuter une commande de reprise :

- [ ] `status`, `log --graph --all` et `reflog` ont été capturés.
- [ ] Vous avez déterminé si les modifications sont uniquement locales ou déjà partagées.
- [ ] Une branche ou un commit de conservation a été créé.
- [ ] Les identifiants de fichier, de branche et de commit ont été indiqués précisément.
- [ ] Si un secret a été exposé, les identifiants ont été révoqués et réémis avant toute manipulation Git.
- [ ] Le diff, les tests et le graphe distant ont été vérifiés de nouveau après la reprise.

## Cas d’échec et limites

### Intégrer en une seule fois une branche ayant vécu longtemps

Le problème des conflits tient à leur sens, pas au nombre de lignes. Sur une branche restée longtemps séparée, l’intention de conception évolue des deux côtés ; des conflits de comportement peuvent survenir même sans conflit textuel. Les petites PR et l’intégration continue réduisent le coût de reprise.

### Rebaser sans précaution une branche publique

Le rebase n’est pas dangereux en soi ; c’est le remplacement sans accord d’une base partagée qui l’est. Distinguez le nettoyage d’une branche de fonctionnalité personnelle de la modification de l’historique d’une branche partagée.

### Considérer un conflit comme résolu après avoir simplement supprimé ses marqueurs

La suppression de `<<<<<<<`, `=======` et `>>>>>>>` ne prouve pas que l’intention des deux côtés a été préservée. Après la résolution d’un conflit, relancez les tests pertinents, les vérifications de types et la validation des migrations de données.

### Penser que supprimer un secret de l’historique des commits met fin à l’incident

Une fois qu’un jeton ou une clé a été pushé, il peut déjà subsister dans des clones, des journaux de CI, des caches et des forks. Révoquez et remplacez d’abord le secret. Si un nettoyage de l’historique est nécessaire, traitez-le comme une réponse à incident distincte coordonnée par les administrateurs du dépôt et tous les utilisateurs. Un push forcé unilatéral peut briser l’historique collaboratif sans annuler l’exposition.

### Considérer le reflog comme une sauvegarde

Le reflog est extrêmement utile, mais il s’agit d’un mécanisme de reprise local et temporaire. Il ne remplace ni les pushs distants, ni les branches protégées, ni les tags, ni la conservation des artefacts, ni la politique de sauvegarde du dépôt.

Le but d’une bonne stratégie Git n’est pas d’obtenir un « joli graphe ». Il est de limiter la taille des modifications, de préserver les preuves d’examen et de permettre à chacun de déterminer vers quel commit revenir après une défaillance.
