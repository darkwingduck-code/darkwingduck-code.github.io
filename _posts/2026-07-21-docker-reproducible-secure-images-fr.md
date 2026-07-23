---
title: "Images Docker reproductibles et sûres : du contexte de build à l’exécution non-root"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Concevoir les builds multi-stage, le verrouillage des dépendances, les health checks, l’exécution non-root et la vérification des images autour des layers Docker et du contexte de build.
lang: fr-FR
translation_key: docker-reproducible-secure-images
hidden: true
---

{% include language-switcher.html %}

## Problème : on peut déplacer « ça marche sur ma machine » dans une image

Les conteneurs empaquettent un environnement d’exécution, mais ne garantissent pas automatiquement la reproductibilité ni la sécurité. Conserver une image de base `latest`, des dépendances non verrouillées, un contexte de build surdimensionné, l’utilisateur root ou des secrets copiés dans l’image revient à empaqueter avec l’application les différences d’environnement et la surface d’attaque.

Deux images peuvent différer même si elles sont construites à partir du même Dockerfile.

- Au moment du build, le tag de base pointait vers un autre digest.
- L’index des paquets a sélectionné une nouvelle dépendance.
- Un fichier temporaire local est entré dans le contexte de build.
- Une autre wheel native a été téléchargée pour une architecture CPU différente.
- Les métadonnées et les horodatages du build différaient.

Il faut donc distinguer les objectifs.

1. **Reproductibilité fonctionnelle** : la même source et le même lock produisent le même comportement.
2. **Reproductibilité des dépendances** : la même base et les mêmes artefacts de paquets sont sélectionnés.
3. **Reproductibilité bit à bit** : même le digest de l’image générée est identique.

Un service ordinaire doit d’abord atteindre les deux premiers objectifs, puis s’étendre aux builds déterministes et à la provenance lorsque les exigences de supply chain sont plus strictes.

## Modèle mental : une image est faite de layers immuables, un conteneur est un état d’exécution

Les composants essentiels d’un build Docker sont les suivants.

- **Contexte de build** : ensemble des fichiers envoyés au builder
- **Instruction Dockerfile** : étape qui crée un layer et des métadonnées d’image
- **Image** : ensemble immuable de layers adressés par contenu et de configuration
- **Conteneur** : instance en cours d’exécution qui combine une image avec un layer inscriptible, un processus, des namespaces et des limites de ressources
- **Registry** : stockage qui conserve et distribue les manifests et blobs des images

Chaque étape du Dockerfile crée une clé de cache à partir de l’état précédent, de l’instruction et des fichiers qu’elle utilise. Si le code source, fréquemment modifié, est copié avant l’installation des dépendances, même une petite modification du code invalide le layer des dépendances.

Les tags et les digests sont également différents.

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

Une combinaison utile consiste à permettre aux humains de retrouver les versions par tag, tandis que les systèmes de déploiement utilisent des digests vérifiés.

### L’isolation des conteneurs n’est qu’une couche de la frontière de sécurité

En général, les conteneurs ne disposent pas d’un kernel distinct comme les VM. Il faut combiner runtimes rootless, seccomp/AppArmor/SELinux, suppression des capabilities, systèmes de fichiers en lecture seule, politiques réseau et mise à jour de l’hôte. Définir `USER` sur un compte non-root dans l’image est un défaut important, mais ce n’est pas une sandbox complète.

## Modèle pratique : contexte réduit, entrées verrouillées, plusieurs stages et privilèges minimaux au runtime

### Commencer par restreindre le contexte de build

Exemple de `.dockerignore` :

```dockerignore
.git
.github
.env
.env.*
!.env.example
.venv
__pycache__/
*.pyc
*.log
.pytest_cache/
.mypy_cache/
tests/
docs/
dist/
build/
```

`.dockerignore` n’est pas seulement un outil pour réduire la taille de l’image. Il limite ce qui est envoyé au builder et empêche l’inclusion de secrets et de fichiers inutiles par `COPY . .`. Si le projet a réellement besoin des tests ou de la documentation au runtime, il ne faut pas les exclure sans discernement ; il faut concevoir un contexte pour chaque objectif de build.

Même si `.env` est exclu, son contenu peut être exposé s’il a déjà été commité dans Git ou passé comme argument de build. Le secret scanning et la rotation des identifiants restent nécessaires séparément.

### Dockerfile multi-stage pour un service Python

L’exemple suivant est le squelette d’un service qui emploie des wheels binaires verrouillées par hash sans nécessiter de compilateur.

```dockerfile
# syntax=docker/dockerfile:1.7

# 로컬에서는 tag로 실행할 수 있지만, CI에서는 검토한 digest로 덮어쓴다.
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS dependencies

WORKDIR /build
COPY requirements.lock ./requirements.lock

RUN python -m pip download \
      --require-hashes \
      --only-binary=:all: \
      --destination /wheelhouse \
      --requirement requirements.lock

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent app

WORKDIR /app

COPY --from=dependencies /wheelhouse /wheelhouse
COPY requirements.lock ./requirements.lock
RUN python -m pip install \
      --no-index \
      --find-links=/wheelhouse \
      --require-hashes \
      --requirement requirements.lock \
    && rm -rf /wheelhouse requirements.lock

COPY --chown=10001:10001 app/ ./app/

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "app"]
```

Ce modèle vise les objectifs suivants.

- Copier le lock des dépendances avant la source pour stabiliser la frontière du cache.
- Rejeter avec `--require-hashes` les artefacts de paquets absents du lock.
- Séparer le stage de téléchargement utilisé au build du runtime.
- Réduire les différences de résolution de l’utilisateur au runtime avec des UID et GID numériques.
- Utiliser la forme exec de `CMD` plutôt que la forme shell afin de simplifier la transmission des signaux.
- Faire vérifier une réponse HTTP par le health check, et non la simple existence du processus de service.

Dans la CI, il faut épingler la base par digest.

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Il faut remplacer les placeholders `<...>` par des valeurs réellement examinées. Épingler un digest n’empêche pas les mises à jour ; cela rend les changements visibles dans les pull requests. Lorsqu’un correctif de vulnérabilité de l’image de base est publié, il faut examiner une pull request automatisée de mise à jour du digest, puis reconstruire.

Si des extensions natives doivent être compilées depuis leur source, installez le compilateur et les headers dans un stage de build, puis ne copiez que les wheels obtenues dans le runtime. La toolchain de compilation et les versions des paquets de l’OS font elles aussi partie des entrées ; elles doivent donc entrer dans le périmètre du verrouillage et de la provenance.

### Un lock file décrit des artefacts exacts, pas des plages

Un fichier ne contenant que des plages comme les suivantes peut produire des résolutions différentes au fil du temps.

```text
framework>=1.0
client-library
```

Un lock de production épingle versions et hashes jusque dans les dépendances transitives, et un outil de mise à jour automatisé crée un nouveau lock qui est ensuite testé. Modifier manuellement une seule partie de l’arbre de dépendances peut produire une résolution incohérente.

Le même principe s’applique aux paquets de l’OS. Exécuter `apt-get upgrade` à chaque build permet éventuellement de rester à jour, mais ne constitue pas une entrée reproductible. Il faut choisir une politique adaptée aux exigences du système.

- Inclure l’ensemble des paquets de l’OS dans le digest d’une image de base de confiance et mettre fréquemment cette base à jour.
- Utiliser un dépôt de snapshots de paquets et des versions exactes.
- Utiliser le pipeline d’images de base durcies de l’organisation.

La réponse aux vulnérabilités n’est pas un choix entre « toujours la dernière version » et « épinglé pour toujours ». C’est un **processus de mise à jour et de validation périodiques des entrées épinglées**.

### Ne pas laisser les secrets de build dans les layers et l’historique

Il faut éviter cette forme :

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

Les arguments et environnements de build peuvent apparaître dans l’historique de l’image, les métadonnées, les logs et les chemins de cache. Il faut utiliser un montage de secret BuildKit et ne pas afficher sa valeur dans l’instruction.

```dockerfile
RUN --mount=type=secret,id=package_token \
    PACKAGE_TOKEN="$(cat /run/secrets/package_token)" \
    python scripts/fetch_private_dependency.py
```

```bash
docker build \
  --secret id=package_token,src='<LOCAL_SECRET_FILE>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Le script d’exemple doit lui aussi éviter de laisser le token dans des URL, des exceptions ou des logs de debug. Lorsque c’est possible, il faut utiliser un identifiant de courte durée émis par le service de build plutôt qu’un token de longue durée.

### Exécuter avec un système de fichiers en lecture seule et un minimum de capabilities

Il faut compléter le défaut non-root de l’image par une politique de runtime.

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --memory 512m \
  --cpus 1.0 \
  --publish 127.0.0.1:8080:8080 \
  'service:<SOURCE_REVISION>'
```

Si le service doit écrire des fichiers, il ne faut pas ouvrir tout le système de fichiers racine. Montez explicitement uniquement les emplacements nécessaires, par exemple `/tmp`, les uploads et les caches. `--privileged`, les montages du socket de l’hôte et le réseau de l’hôte affaiblissent considérablement le modèle d’isolation et ne doivent pas servir de simples options de commodité.

Il ne faut incorporer les identifiants ni dans une image ni dans un fichier d’environnement ordinaire. Utilisez le secret store et l’identité de workload de la plateforme de déploiement, puis fournissez les secrets uniquement au processus qui en a besoin, en mémoire ou par un montage restreint.

### Distinguer liveness et readiness dans les health checks

Le `HEALTHCHECK` d’un Dockerfile ne représente qu’un seul état. Un orchestrateur sépare généralement les éléments suivants.

- **Startup** : l’initialisation est-elle terminée ?
- **Liveness** : le processus est-il bloqué au point de devoir être redémarré ?
- **Readiness** : peut-il accepter du nouveau trafic maintenant ?

Coupler fortement la readiness à chaque dépendance externe peut retirer tous les réplicas du trafic lors d’une défaillance transitoire en aval et amplifier une panne en cascade. L’endpoint doit refléter la capacité à traiter le trafic réel, mais une défaillance externe qu’un redémarrage ne peut pas corriger ne doit pas devenir un échec de liveness.

### Conserver les preuves après le build d’une image

La sortie du pipeline de vérification comprend non seulement l’image, mais aussi les éléments suivants.

- Révision de la source et invocation du build
- Digests de l’image de base et de l’image finale
- SBOM
- Résultats du scan de vulnérabilités et dates d’expiration des exceptions
- Résultats des tests
- Provenance du build et signatures ou attestations

Au déploiement, il ne faut pas résoudre de nouveau le tag ; utilisez le digest approuvé. La politique de rétention du registry doit être alignée afin que les blobs référencés par le digest ne soient pas supprimés avant la fin de la période de déploiement.

## Checklist de vérification

Avant le build :

- [ ] `.dockerignore` exclut les données Git, les secrets, les caches locaux et les artefacts inutiles.
- [ ] Les images de base et les dépendances du langage sont verrouillées sur des versions examinées, ou sur des digests et des hashes.
- [ ] Les mises à jour du lock font l’objet de tests automatisés et d’un examen des vulnérabilités.
- [ ] Les secrets de build sont absents de `ARG`, `ENV`, des URL et des logs.
- [ ] Les manifests de dépendances sont copiés avant le code source afin d’établir la frontière du cache.

Examen de l’image :

- [ ] L’image de runtime ne contient ni compilateur, ni cache de gestionnaire de paquets, ni identifiants de test.
- [ ] `USER` est non-root et utilise des valeurs UID et GID fixes.
- [ ] L’entrypoint peut recevoir les signaux et s’arrêter proprement.
- [ ] Le health check est rapide, possède un timeout et n’entraîne aucun effet secondaire.
- [ ] Le contenu des layers, le SBOM et les vulnérabilités ont été examinés, et pas seulement la taille de l’image.
- [ ] Les images multi-architecture ont été testées sur chacune des architectures cibles réelles.

Examen du runtime :

- [ ] Le déploiement utilise un digest immuable.
- [ ] Le système de fichiers racine est en lecture seule et les montages inscriptibles sont réduits au minimum.
- [ ] La suppression des capabilities, no-new-privileges et une couche seccomp sont appliqués.
- [ ] Les limites CPU, mémoire et PID ainsi qu’une période d’arrêt propre sont définies.
- [ ] Les secrets sont fournis depuis une identité de runtime ou un secret store.
- [ ] Les significations des probes de readiness, de liveness et de startup sont distinctes.

## Cas d’échec et limites

### Choisir Alpine d’après la seule taille de l’image

Une taille réduite ne signifie pas toujours un risque moindre ou une exploitation plus rapide. Il faut comparer les différences de libc, l’absence de wheels natives, le comportement du DNS et des fuseaux horaires, ainsi que les difficultés de debug. Choisissez la plus petite base dont la compatibilité opérationnelle a été validée.

### Supposer qu’un build multi-stage est automatiquement sûr

Copier un système de fichiers entier dans le stage final avec une commande comme `COPY --from=builder / /` réintroduit les secrets de build et la toolchain. Il faut copier uniquement les chemins des artefacts nécessaires.

### Effectuer une authentification, des écritures ou des requêtes lourdes dans un health check

Les probes s’exécutent fréquemment. Une probe lente ou qui modifie l’état devient elle-même une source de panne. Il faut vérifier uniquement la readiness essentielle dans un temps limité.

### Traiter les résultats d’un scanner comme des jugements absolus

Les scanners dépendent des inventaires de paquets et de la qualité des avis de sécurité. Des faux positifs comme des vulnérabilités non découvertes sont possibles. Il faut examiner le code atteignable, l’exploitabilité et les contrôles compensatoires, tout en attribuant à chaque exception un responsable et une date d’expiration.

### Chercher à obtenir toute la reproductibilité par les seuls conteneurs

Les schémas de bases de données externes, les feature flags, les versions de secrets, les pilotes matériels, les kernels et les dépendances réseau restent hors de l’image. Il faut également suivre les manifests de déploiement, les migrations, l’IaC, les versions de configuration et les contrats de données.

Un bon Dockerfile n’est pas simplement un fichier court. C’est un contrat de build qui explique quelles entrées ont produit quel résultat, ce qui est inutile au runtime et avec quels privilèges le résultat s’exécute.
