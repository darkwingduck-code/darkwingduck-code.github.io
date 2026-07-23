---
title: "Concevoir une CI/CD avec GitHub Actions : commencer par les frontières de confiance, pas par la vitesse de l’automatisation"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: Comprendre les frontières de confiance entre workflows, jobs et runners de GitHub Actions pour concevoir sûrement permissions, secrets, environments, matrices, caches et concurrence.
lang: fr-FR
translation_key: github-actions-ci-cd-design
hidden: true
---

{% include language-switcher.html %}

## Problème : un workflow qui passe n’est pas forcément un pipeline digne de confiance

La CI/CD réduit les tâches répétitives, mais une mauvaise conception peut relier les privilèges les plus puissants du dépôt à des entrées externes. Un workflow récupère le code source, télécharge des dépendances, exécute des tests et va parfois jusqu’à modifier l’environnement de production. Autrement dit, un petit fichier YAML est à la fois système de construction, courtier d’identifiants et plan de contrôle du déploiement.

S’arrêter à « les tests s’exécutent automatiquement » laisse subsister les problèmes suivants.

- Tous les jobs partagent un jeton par défaut doté de droits d’écriture.
- Le code non fiable d’une pull request issue d’un fork accède aux secrets.
- Un ancien déploiement d’une branche écrase un déploiement plus récent de la même branche.
- Caches et artefacts passent à l’étape d’exécution sans vérification de leur provenance.
- Une seule combinaison parmi toute la matrice fournit une validation réellement utile.
- La construction et le déploiement sont couplés, ce qui empêche de promouvoir le même artefact.

Le but d’un bon pipeline n’est pas seulement d’afficher une coche verte, mais d’assurer **un résultat reproductible pour une même entrée, le moindre privilège, la promotion cohérente d’un artefact validé et des points d’arrêt explicites en cas d’échec**.

## Modèle mental : un workflow est un graphe orienté acyclique qui transporte privilèges et données

Distinguons les principales unités de GitHub Actions.

- **event** : entrée externe, telle que `pull_request`, `push` ou `workflow_dispatch`, qui déclenche l’exécution
- **workflow** : fichier qui définit l’événement et le graphe des jobs
- **job** : ensemble d’étapes exécutées sur un même runner ; par défaut, les jobs ne partagent pas leur système de fichiers
- **step** : exécution unique d’une action ou d’une commande shell
- **runner** : ressource de calcul éphémère ou auto-hébergée qui exécute le code
- **artifact** : résultat explicitement transmis et conservé entre jobs et workflows
- **cache** : moyen d’optimisation qui restaure rapidement des dépendances reproductibles
- **environment** : frontière de contrôle regroupant cible de déploiement, approbations, règles de protection et secrets propres à l’environnement

À chaque frontière, il faut poser quatre questions.

1. Qui contrôle les entrées ?
2. Quel code est exécuté ?
3. Quels jetons et secrets sont exposés ?
4. Comment vérifier la provenance et l’intégrité des résultats ?

### Séparer la CI de la CD

La CI vérifie la qualité d’un commit et produit un artefact immuable. La CD promeut cet artefact déjà validé vers un environnement déterminé. Reconstruire dans chaque environnement peut rendre différents le « binaire testé » et le « binaire déployé en production ».

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

L’identifiant d’un déploiement doit être une valeur immuable, comme le SHA du commit, le digest de l’image ou celui de l’artefact, plutôt qu’un nom de branche.

## Patron pratique : valider les PR avec de faibles privilèges et déployer à travers une frontière distincte

### Workflow de CI au moindre privilège

L’exemple suivant présente l’ossature de base d’un projet Python. Il doit être adapté au fichier de verrouillage et aux commandes de test du dépôt.

{% raw %}
```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

# workflow 전체의 기본값은 읽기 전용이다.
permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: python-${{ matrix.python }} / ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.11", "3.12"]

    steps:
      - name: Check out source
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
          cache-dependency-path: requirements.lock

      - name: Install locked dependencies
        run: python -m pip install --require-hashes -r requirements.lock

      - name: Static checks
        run: python -m ruff check .

      - name: Unit tests
        run: python -m pytest -q --maxfail=1
```
{% endraw %}

Pour garder l’exemple lisible, les actions officielles utilisent ici leur balise majeure. Dans un dépôt exigeant un haut niveau d’assurance, il faut épingler les actions sur leur **SHA de commit complet** après examen, puis les mettre à jour avec un outil de gestion des dépendances. Pour une action tierce, mieux vaut examiner le code source, le mainteneur, la provenance des versions et les privilèges demandés que les étoiles du marketplace.

Une matrice n’est pas meilleure parce qu’elle contient davantage de combinaisons. Elle ne doit conserver que les axes effectivement garantis par le contrat de prise en charge.

- Bibliothèque : combinaisons des versions minimales et récentes des environnements d’exécution pris en charge
- Application : environnement principal identique à la production, plus ceux qui présentent un fort risque de compatibilité
- GPU et intégrations lourdes : séparer un test de fumée sur chaque PR de la suite complète planifiée

Avec `fail-fast: false`, l’échec d’une combinaison n’empêche pas de recueillir les résultats de compatibilité des autres. À l’inverse, pour les jobs coûteux, il vaut mieux faire précéder leur exécution de jobs rapides de lint et de tests unitaires, puis les bloquer avec `needs`.

### Distinguer cache et artefact

| Élément | cache | artefact |
|---|---|---|
| Finalité | accélérer des entrées reproductibles | transmettre et conserver résultats de construction et rapports |
| En cas d’absence | l’exécution doit rester correcte, même si elle ralentit | échec requis si l’étape suivante en dépend |
| Clé | système d’exploitation, environnement d’exécution, empreinte du fichier de verrouillage, etc. | SHA du commit, identifiant de construction, digest, etc. |
| Confiance | supposer une contamination possible et vérifier | gérer ensemble provenance et digest |

Même les dépendances restaurées depuis un cache doivent être vérifiées au moyen du fichier de verrouillage et de l’empreinte des paquets. Un cache ne doit contenir ni scripts arbitraires exécutables ni identifiants de longue durée. Il faut examiner les événements et les portées afin qu’un cache modifiable depuis une PR n’alimente pas un job hautement privilégié d’une branche protégée.

L’artefact construit une seule fois est promu entre les environnements. Sa durée de conservation doit être limitée au besoin métier et son digest vérifié avant le déploiement. Les rapports de test et la couverture sont des données d’observation ; ils ne remplacent pas le binaire à déployer.

### Pour le déploiement, employer un environment et des identifiants de courte durée

Le déploiement en production doit s’effectuer dans un workflow distinct exécuté depuis une branche ou une balise protégée, ou dans un job strictement isolé, jamais dans le workflow de PR. Le squelette suivant en montre la structure. Les valeurs `<...>` et les SHA d’actions doivent être remplacés selon la configuration du fournisseur cloud et du dépôt.

{% raw %}
```yaml
name: deploy

on:
  workflow_dispatch:
    inputs:
      artifact_digest:
        description: "검증된 artifact digest"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment: production

    steps:
      - uses: actions/checkout@<REVIEWED_FULL_COMMIT_SHA>
        with:
          persist-credentials: false

      - name: Exchange OIDC token for short-lived cloud credentials
        uses: <CLOUD_PROVIDER_LOGIN_ACTION>@<REVIEWED_FULL_COMMIT_SHA>
        with:
          role: <DEPLOYMENT_ROLE_IDENTIFIER>

      - name: Verify and deploy the immutable artifact
        env:
          ARTIFACT_DIGEST: ${{ inputs.artifact_digest }}
        run: ./scripts/deploy.sh --digest "$ARTIFACT_DIGEST"
```
{% endraw %}

Les points essentiels sont les suivants.

- N’accorder `id-token: write` qu’au job qui en a besoin pour l’échange OIDC.
- Restreindre la politique de confiance du cloud par dépôt, branche ou balise, et déclaration d’environnement.
- Émettre des identifiants de courte durée au lieu de stocker une clé d’accès permanente dans un secret du dépôt.
- Configurer sur l’environment `production` les approbateurs, les branches ou balises admises et les secrets propres à cet environnement.
- Pour un déploiement en production, utiliser `cancel-in-progress: false` et rendre l’outil de déploiement lui-même sûr en cas d’exécution répétée.

L’emploi d’OIDC ne rend pas le système sûr par magie. Si les conditions de confiance côté cloud sont trop larges, le workflow de n’importe quelle branche pourra obtenir le rôle de production.

### Gérer les chemins d’exposition des secrets, pas seulement leur valeur

Le simple stockage d’un secret dans l’interface GitHub ne clôt pas le sujet.

- Un argument de shell peut apparaître dans la liste des processus ou les journaux de débogage.
- Après transformation ou encodage d’un secret, le masquage risque de ne plus le reconnaître.
- Une valeur peut être copiée dans un objet d’erreur, un jeu de données de test ou un artefact.
- Le disque ou les processus d’un runner auto-hébergé peuvent laisser des traces pour le job suivant.

Il faut limiter le passage du secret à la variable d’environnement de l’étape qui en a besoin et ne jamais en afficher la valeur complète.

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

Par défaut, une PR provenant d’un fork ne doit recevoir aucun secret protégé. `pull_request_target`, en particulier, peut obtenir des privilèges dans le contexte de la branche de base ; il ne faut donc jamais l’associer à un patron qui récupère et exécute le code non fiable d’une PR. Le traitement de métadonnées, comme les labels et commentaires, doit être séparé de l’exécution du code dans des workflows différents.

### Séparer l’insertion d’expressions de la citation shell

Interpoler directement une entrée utilisateur, tel le titre d’une PR, dans un bloc `run` peut en faire du code shell. Il faut transmettre cette valeur par l’environnement et la citer dans le shell.

Forme dangereuse :

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

Forme plus sûre :

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

Dans la mesure du possible, il faut même limiter l’affichage des entrées utilisateur, valider leur format et employer une liste d’autorisation.

### Les politiques de concurrence diffèrent entre CI et CD

Dans la CI d’une PR, l’arrivée d’un nouveau commit réduit l’intérêt de l’exécution précédente ; l’annuler est donc efficace.

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

Lors d’un déploiement, interrompre brutalement une modification en cours peut laisser l’environnement dans un état intermédiaire. Les déploiements vers un même environnement doivent être sérialisés et mis en file d’attente plutôt qu’annulés. L’outil de déploiement de l’application doit assurer l’idempotence, les délais d’expiration ainsi que le retour arrière ou la progression corrective.

## Liste de contrôle de la validation

Points à vérifier dans une PR qui modifie un workflow :

- [ ] Le déclencheur ne répond qu’aux événements et branches nécessaires.
- [ ] Les `permissions` de premier niveau sont en lecture seule et les droits d’écriture sont limités aux jobs qui en ont besoin.
- [ ] Les PR provenant de forks et le code non fiable n’accèdent ni aux secrets ni aux identifiants de déploiement.
- [ ] Une politique impose d’épingler les actions d’une source fiable sur un SHA examiné.
- [ ] Les dépendances sont vérifiées au moyen du fichier de verrouillage et de leurs empreintes.
- [ ] La construction réussit correctement même en cas d’absence du cache.
- [ ] L’artefact est relié au commit ou à son digest et n’est pas reconstruit dans chaque environnement.
- [ ] Les approbations d’environment et la politique de confiance du cloud restreignent la portée aux branches ou balises prévues.
- [ ] La CI annule les exécutions obsolètes et la CD sérialise les modifications d’un même environnement.
- [ ] Tous les jobs définissent un `timeout-minutes` raisonnable.
- [ ] Les journaux d’échec et les artefacts ne contiennent ni secrets ni données personnelles.
- [ ] Le nom des vérifications exigées par la protection de branche reste valable après la modification du workflow.

L’analyse statique peut combiner validation du schéma du workflow, revue des dépendances, détection de secrets et contrôle des règles applicables aux actions. Toutefois, le passage du lint ne prouve pas la sûreté de la conception des privilèges : il faut également examiner un modèle de menace propre à chaque événement.

## Cas d’échec et limites

### Résoudre le problème avec `permissions: write-all`

Les erreurs d’autorisation disparaissent, mais l’impact d’une compromission s’étend. Il faut déterminer l’opération d’API nécessaire et n’ajouter que la portée correspondante au niveau du job.

### Croire qu’une balise suffit à figer complètement la chaîne d’approvisionnement

Une balise majeure ou de version peut être déplacée. Un SHA de commit complet constitue un ancrage plus fort, mais il faut aussi examiner le code source de ce commit et le processus de publication. L’épinglage doit s’accompagner d’une automatisation des mises à jour et d’une réponse aux vulnérabilités.

### Employer le cache comme résultat de construction fiable

Le cache est une optimisation : sa suppression ne doit pas compromettre l’exactitude. La cible du déploiement doit être transmise comme artefact explicite avec sa provenance.

### Voir le runner auto-hébergé comme un simple moyen de réduire les coûts

Un runner auto-hébergé peut présenter une surface d’attaque plus vaste, avec accès réseau, disque persistant ou métadonnées cloud. Les PR publiques ou issues de forks ne doivent pas s’exécuter sur un runner permanent. Il faut exploiter une isolation éphémère, réinitialiser les images, limiter les sorties réseau et appliquer les correctifs.

### Exécuter tous les tests sur chaque PR

Lorsque la validation ralentit trop, les développeurs la contournent ou regroupent de gros lots de modifications. Le portefeuille de tests doit être hiérarchisé entre contrôles obligatoires rapides, intégrations selon les chemins modifiés, régression complète planifiée et validation après déploiement. Les filtres de chemins doivent néanmoins rester prudents afin de n’omettre aucune dépendance réelle.

GitHub Actions n’est pas un problème de syntaxe YAML, mais de conception des frontières de confiance. En séparant événements, code, identifiants, artefacts et environnements, on détecte bien plus tôt les automatisations dangereuses.
