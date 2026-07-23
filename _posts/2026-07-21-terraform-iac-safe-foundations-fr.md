---
title: "Concevoir une IaC Terraform sûre : limites des modules, environnements, états et secrets"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Comprendre Terraform comme un système de changement déclaratif et concevoir les contrats de modules, l’isolation des environnements, l’état distant, la gestion des secrets ainsi que les procédures de vérification de planification et d’application.
lang: fr-FR
translation_key: terraform-iac-safe-foundations
hidden: true
---

{% include language-switcher.html %}

## Le problème : convertir l’infrastructure en code ne la rend pas automatiquement sûre

Terraform remplace les clics manuels par du code reproductible, mais concentre en même temps les autorisations de modification de l’infrastructure et l’état réel des ressources dans un seul flux de travail. Sans structure initiale, un petit module racine finit par porter tous les environnements, toutes les autorisations, tous les secrets et toutes les configurations de fournisseurs.

Les défaillances courantes sont les suivantes.

- Le développement et la production partagent le même état et les mêmes identifiants.
- Un module expose tant de choix qu’il devient pratiquement une autre plateforme.
- L’état local est perdu, ou plusieurs exécutants le modifient simultanément.
- `sensitive = true` est confondu avec du chiffrement, si bien que des secrets restent dans l’état.
- Le code, les fournisseurs ou l’état changent entre le plan examiné et l’application réelle.
- `-target` et les modifications manuelles dans la console deviennent des pratiques d’exploitation ordinaires.

L’objectif de l’IaC n’est pas de multiplier les fichiers. Il consiste à **réunir dans un flux auditable l’intention de changement, l’état réel, les limites d’autorisation et les résultats de vérification**.

## Modèle mental : réconcilier configuration, état, fournisseurs et infrastructure réelle

Une exécution Terraform comporte quatre éléments.

- **configuration** : le HCL qui exprime l’état souhaité
- **état** : les informations de correspondance entre les adresses Terraform et les identifiants et attributs des objets distants réels
- **fournisseur** : une extension qui lit et modifie des API
- **infrastructure réelle** : les ressources effectives dans le cloud, les systèmes SaaS et les environnements sur site

`terraform plan` n’est pas une simple comparaison de fichiers. Il produit un plan d’exécution en comparant la configuration, l’état précédent et l’état réel lu par les fournisseurs. `apply` appelle les API selon le graphe de dépendances et inscrit dans l’état les résultats obtenus.

L’état n’est donc pas un cache. C’est une donnée d’exploitation critique qui contient notamment :

- les identifiants réels des ressources ;
- les dépendances et instantanés d’attributs ;
- les sorties et certaines valeurs renvoyées par les fournisseurs ;
- des entrées et résultats calculés susceptibles d’être secrets.

La perte de l’état ne fait pas disparaître l’infrastructure réelle, mais Terraform perd la correspondance de propriété. Inversement, une personne ne disposant que du fichier d’état peut tout de même découvrir des informations sensibles et la structure de l’infrastructure.

### Déclaratif ne signifie pas « sans ordre »

Une référence à une ressource crée une arête de dépendance. Terraform parallélise les opérations lorsque c’est possible tout en respectant l’ordre du graphe. Multiplier les déclarations `depends_on` sans nécessité crée un couplage caché et ralentit les plans. Exprimez le flux de données par des références et n’utilisez `depends_on` que lorsqu’une API impose une contrainte implicite.

### Un module est davantage un contrat de politique qu’un mécanisme de réutilisation du code

Un bon module restreint les choix autorisés par l’organisation.

- entrée : ce que les appelants sont autorisés à décider
- valeur locale : les noms, étiquettes et politiques normalisés par le module
- ressource : les détails d’implémentation
- sortie : les contrats stables dont peuvent dépendre d’autres composants

Une « enveloppe mince » qui réexpose tel quel chaque argument du fournisseur sous forme de variable n’apporte guère d’abstraction. À l’autre extrême, si un même module possède le réseau, la base de données, l’application et la supervision, le rayon d’impact de ses modifications devient très large.

## Modèle pratique : petites racines, modules stables et état indépendant par environnement

### Une structure de départ recommandée

```text
infrastructure/
├── modules/
│   └── service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── live/
    ├── development/
    │   ├── backend.hcl
    │   ├── main.tf
    │   └── terraform.tfvars.example
    └── production/
        ├── backend.hcl
        ├── main.tf
        └── terraform.tfvars.example
```

Dupliquer un répertoire d’environnement n’est pas l’unique bonne réponse. Des dépôts séparés, une couche d’orchestration ou des pipelines par compte sont également possibles. Les invariants importants sont les suivants :

- Chaque environnement possède une clé d’état et des autorisations d’application indépendantes.
- La production utilise un compte ou projet distinct et une limite d’approbation indépendante.
- La version ou le commit du module partagé est explicitement épinglé.
- Les différences entre environnements sont des entrées explicites, pas une forêt de conditions.

Les espaces de travail Terraform facilitent la gestion de plusieurs états à partir d’une même configuration, mais ils n’assurent pas automatiquement une forte isolation de sécurité ni des structures d’environnement très différentes. Si vous avez besoin de frontières d’identifiants et de comptes, séparez aussi les identités d’exécution, et pas seulement les répertoires et les états.

### Donner aux modules des contrats étroits et vérifiables

Exemple de `variables.tf` :

```hcl
variable "name" {
  description = "서비스를 식별하는 짧은 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name은 소문자로 시작하고 소문자, 숫자, 하이픈만 사용해야 합니다."
  }
}

variable "environment" {
  description = "배포 환경"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "허용된 environment 값을 사용해야 합니다."
  }
}

variable "labels" {
  description = "추가 공통 label"
  type        = map(string)
  default     = {}
}
```

Conservez les valeurs normalisées dans le module, dans `main.tf`.

```hcl
locals {
  required_labels = {
    managed-by  = "terraform"
    environment = var.environment
    service     = var.name
  }

  labels = merge(var.labels, local.required_labels)
}

# provider에 독립적인 예시를 위해 실제 resource는 생략했다.
# 각 resource는 local.labels를 사용해 소유권과 환경을 표시한다.
```

Comme les tables placées plus tard dans `merge` remplacent les précédentes, mettre les étiquettes obligatoires en dernier empêche les appelants de les modifier. Ce petit exemple illustre la manière dont un module encapsule une politique.

N’exposez par les sorties que le contrat minimal requis.

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

Renvoyer l’objet ressource complet couple les appelants aux détails d’implémentation. Ne renvoyez que ce dont les consommateurs ont réellement besoin, par exemple un identifiant, un point de terminaison ou un identifiant de rôle.

### Gérer ensemble les contraintes de version et le verrouillage des fournisseurs

```hcl
terraform {
  required_version = ">= 1.8, < 2.0"

  required_providers {
    <PROVIDER_NAME> = {
      source  = "<PROVIDER_NAMESPACE>/<PROVIDER_NAME>"
      version = "~> <REVIEWED_MAJOR.MINOR>"
    }
  }
}
```

Remplacez les espaces réservés de cet exemple par le fournisseur réel. Définissez les contraintes de version dans le module racine et validez dans le dépôt le fichier `.terraform.lock.hcl` produit par `terraform init`. Un module doit déclarer la version minimale du fournisseur dont il a besoin, tandis que la racine assume généralement la sélection finale et son verrouillage.

Le fichier de verrouillage épingle le binaire du fournisseur sélectionné ainsi que ses sommes de contrôle. Si l’exécution couvre plusieurs systèmes d’exploitation ou architectures, gérez délibérément les sommes de contrôle de plateforme nécessaires aux environnements de CI et de développement.

### Séparer l’accès au backend et à l’état de l’accès au code

N’inscrivez pas de secrets directement dans le bloc de backend.

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

Vous pouvez fournir les paramètres non sensibles propres à chaque environnement dans un fichier distinct.

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

Ces arguments varient selon le type de backend et la version de Terraform ; consultez donc la documentation officielle et les capacités réelles du backend. Les exigences essentielles sont :

- le chiffrement en transit et au repos ;
- un verrouillage empêchant les applications simultanées ;
- le versionnement et une politique de récupération ;
- une identité dotée des moindres privilèges ;
- des clés et politiques d’accès distinctes pour chaque environnement ;
- des journaux d’audit et alertes en cas d’accès anormal.

Lancez explicitement l’initialisation depuis le répertoire de l’environnement.

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

Ne placez pas les identifiants du backend dans des fichiers ; délivrez des identifiants de courte durée via OIDC dans la CI ou au moyen d’une chaîne d’identifiants standard. Écrire une clé d’accès dans `backend.hcl` peut la laisser dans plusieurs endroits, notamment les métadonnées `.terraform` et l’historique de l’interpréteur de commandes.

### Lier planification et application en un changement unique et examinable

Le flux de vérification de base est :

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

Exécutez un plan qui utilise l’état distant réel et les API des fournisseurs, avec une identité et un environnement approuvés.

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

Un fichier de plan enregistré est binaire et peut contenir des valeurs sensibles. Ne le conservez pas indéfiniment comme artefact public de CI ; appliquez chiffrement, contrôle d’accès et courte durée de rétention. N’appliquez qu’un plan produit à partir du même commit, du même fichier de verrouillage et de la même lignée d’état.

```bash
terraform apply -input=false tfplan
```

Si une personne approuve un plan textuel et que le pipeline applique automatiquement un nouveau plan issu d’un autre commit, cette approbation n’a plus de sens. Le pipeline doit lier le SHA de la source à l’empreinte de l’artefact de plan.

### Transmettre des références de secrets plutôt que leurs valeurs

La déclaration suivante masque la valeur dans l’interface et certaines sorties, mais elle ne chiffre pas l’état.

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

Si une API de fournisseur accepte la valeur comme attribut de ressource, celle-ci peut être stockée dans l’état. Une conception possible est la suivante :

1. Créer le secret dans un gestionnaire de secrets selon un cycle de vie distinct.
2. Faire en sorte que Terraform ne relie que l’identifiant ou le chemin du secret et les autorisations de lecture.
3. Faire lire la valeur au workload depuis le gestionnaire de secrets au moyen de son identité d’exécution.
4. Ne pas transmettre le secret en clair aux plans, sorties ou journaux.

Si Terraform doit aussi créer le secret, reconnaissez que l’état est devenu un magasin de secrets et gérez son accès, son chiffrement et sa rotation selon les exigences correspondantes. Retirer le marqueur avec `nonsensitive()` ne constitue pas une solution de sécurité.

### La détection de dérive ne s’arrête pas à un plan nocturne

Détectez la dérive provoquée par les modifications dans la console et les automatisations externes au moyen de plans réguliers en lecture seule. Lorsqu’une dérive est découverte, choisissez explicitement l’une des trois réponses suivantes.

- La modification réelle était erronée : restaurez avec Terraform l’état déclaré à l’origine.
- La modification réelle était légitime : reportez-la dans la configuration et appliquez-la par le processus habituel de demande de fusion.
- La propriété était incorrecte : examinez `import`, `moved` et les opérations d’état afin de corriger la limite de responsabilité.

Lorsque vous modifiez l’adresse d’une ressource, utilisez un bloc `moved` afin que Terraform ne prenne pas le changement pour une suppression suivie d’une recréation.

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

Les importations et les commandes d’état changent la compréhension qu’a Terraform de la propriété, même lorsqu’elles ne modifient pas la ressource réelle. Vérifiez le versionnement de l’état avant l’opération ; après celle-ci, assurez-vous toujours que le plan est vide comme prévu ou ne contient que la différence voulue.

## Liste de vérification

Examen du module :

- [ ] Le module possède un cycle de vie cohérent et un responsable unique.
- [ ] Les types, descriptions, validations et valeurs par défaut des entrées sont clairs.
- [ ] Les appelants ne peuvent contourner les étiquettes obligatoires de sécurité et de propriété.
- [ ] Les sorties forment un contrat minimal stable au lieu d’exposer toute l’implémentation.
- [ ] Les plages de versions du fournisseur et de Terraform sont précisées.
- [ ] Les mises à niveau et changements d’adresse disposent de blocs `moved` et d’une documentation de migration.

Examen de l’environnement et de l’état :

- [ ] Les états et identités d’exécution du développement, de la préproduction et de la production sont séparés.
- [ ] Le backend distant fournit chiffrement, verrouillage, versionnement et audit.
- [ ] L’accès à l’état et aux artefacts de plan est plus restreint que l’autorisation de lire le code.
- [ ] `.terraform/`, `*.tfstate*`, les véritables `*.tfvars` et les fichiers de plan ne sont pas validés dans le dépôt.
- [ ] `.terraform.lock.hcl` est validé dans le dépôt après examen.
- [ ] Les applications en production ne s’exécutent que dans un environnement protégé et un pipeline approuvé.

Examen des changements :

- [ ] `fmt`, `validate`, l’analyse statique et les contrôles de politique réussissent.
- [ ] Les actions d’ajout, de modification, de destruction et de remplacement du plan ont été lues ressource par ressource.
- [ ] Les remplacements forcés, pertes de données et interruptions réseau possibles ont été examinés.
- [ ] Le plan examiné et le plan binaire à appliquer proviennent de la même source et du même état.
- [ ] Il existe un moyen de vérifier les fonctions critiques et les métriques d’observabilité après l’application.
- [ ] Pour les changements impossibles à annuler, la procédure de correction vers l’avant et la restauration des sauvegardes ont été testées.

## Cas d’échec et limites

### Un état gigantesque

Les références sont pratiques, mais la moindre modification impose d’actualiser tout le graphe et exige des autorisations étendues. Regroupez dans le même état les ressources qui changent ensemble, ont le même responsable et doivent partager le même rayon d’impact. Inversement, une fragmentation excessive de l’état alourdit la gestion des sorties entre états, de l’ordre et de l’orchestration.

### Absorber toutes les différences entre environnements dans des conditions

Réunir tous les environnements dans une seule racine avec `count`, `for_each` et des expressions ternaires rend les plans difficiles à lire. Placez les politiques communes dans les modules et la composition propre à chaque environnement dans de petites racines.

### Utiliser `-target` comme outil de déploiement quotidien

`-target` est un outil limité destiné à la récupération et aux situations particulières. N’appliquer qu’une partie du graphe peut rompre la cohérence entre la configuration complète et l’état réel. Exécutez toujours un plan complet après l’avoir utilisé.

### Prendre `prevent_destroy` pour une sauvegarde

Une garde de cycle de vie évite certaines erreurs, mais un utilisateur privilégié peut la supprimer et elle ne peut empêcher une suppression effectuée hors du fournisseur. Les ressources de données nécessitent des sauvegardes distinctes, des exercices de récupération, une politique de rétention et une protection contre la suppression.

### Confondre application réussie et service sain

Le fait qu’une API ait créé une ressource ne signifie pas que l’application est saine. Après le déploiement, vérifiez le DNS, les autorisations, la connectivité, l’état de santé et les métriques de SLO. L’IaC ne remplace ni la vérification opérationnelle ni la réponse aux incidents.

### Tout gérer avec Terraform

Terraform excelle pour les ressources déclaratives à longue durée de vie. Y contraindre les déploiements applicatifs fréquents, les migrations de données impératives et les initialisations ponctuelles peut déstabiliser l’état et le graphe. Choisissez des outils adaptés au cycle de vie et aux possibilités d’annulation de chaque changement.

La sûreté de Terraform vient de la conception des limites, pas d’un HCL astucieux. Traitez les modules comme des limites de politique, l’état comme un actif de sécurité, les plans comme des contrats de changement et les identités de pipeline comme l’autorité d’exécution.
