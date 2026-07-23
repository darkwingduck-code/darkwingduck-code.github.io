---
title: "Fondamentaux du diagnostic Linux : lire processus, fichiers, signaux et systemd comme des preuves"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: Une démarche pratique pour circonscrire les incidents Linux à partir des preuves fournies par les processus, descripteurs, systèmes de fichiers, signaux, ressources et le journal systemd, sans commencer par un redémarrage.
lang: fr-FR
translation_key: linux-diagnostics-processes-files-signals-systemd
hidden: true
---
{% include language-switcher.html %}

## Problème : redémarrer efface les symptômes sans expliquer la cause

Lorsqu'un service Linux est lent ou ne répond plus, le redémarrer immédiatement peut le rétablir temporairement.

Mais les preuves présentes dans la mémoire, les descripteurs, les sockets, les processus enfants, le système de fichiers et les dépendances peuvent disparaître avec lui.

Les idées reçues suivantes retardent le diagnostic.

- Une faible utilisation du CPU signifie que le processus est sain.
- Une faible quantité de mémoire libre indique nécessairement un manque de mémoire.
- Si un fichier existe, il doit être lisible.
- `kill` signifie une terminaison forcée.
- Si l'état du service est active, les fonctions destinées aux utilisateurs sont nécessairement saines.
- La dernière ligne du journal est forcément la cause.
- L'exécution en tant que root est une manière acceptable de contourner les problèmes d'autorisation.

Le diagnostic opérationnel doit suivre l'ordre `observation -> hypothèse -> vérification minimale -> atténuation sûre -> validation`.

## Modèle mental : un processus est un ensemble de ressources du kernel

Un processus n'est pas un simple fichier exécutable.

Il possède les éléments suivants.

- PID et PID du parent
- Identité de l'utilisateur et du groupe
- Carte de mémoire virtuelle
- Table de descripteurs de fichiers ouverts
- Répertoire de travail courant
- Environnement
- Disposition des signaux
- Appartenance aux namespaces et aux cgroups
- Threads et état d'ordonnancement

Remplacer un fichier exécutable ne modifie pas automatiquement le mapping mémoire d'un processus déjà lancé.

Un fichier supprimé peut continuer à occuper des blocs de disque tant qu'un descripteur vers celui-ci reste ouvert.

### `/proc` est une fenêtre d'observation sur le kernel en cours d'exécution

`/proc/<pid>/status` présente une vue d'ensemble de l'état et de la mémoire.

`/proc/<pid>/fd` présente les descripteurs ouverts.

`/proc/<pid>/maps` présente les mappings mémoire.

`/proc/<pid>/limits` présente les limites de ressources.

Les frontières d'autorisation et de namespace s'appliquent même à la lecture.

### Les descripteurs de fichiers ne désignent pas seulement des fichiers

Les fichiers ordinaires, répertoires, sockets, pipes, périphériques et objets d'événement peuvent tous être représentés par des descripteurs.

Une fuite de descripteurs peut se manifester non seulement par l'échec d'ouverture de fichiers, mais aussi par l'impossibilité d'établir de nouvelles connexions.

Examiner à la fois les limites du processus et celles de l'ensemble du système.

### Un signal est une notification asynchrone

`SIGTERM` est un signal interceptable qui demande un arrêt normal.

`SIGKILL` ne peut être ni traité ni ignoré par un processus.

Historiquement, `SIGHUP` indique la déconnexion d'un terminal ; certains daemons l'emploient pour demander un rechargement, mais il faut vérifier le contrat de l'application.

La transmission réussie du signal et le nettoyage réussi par l'application sont deux choses différentes.

## Workflow : l'ordre à suivre pour circonscrire un incident

### Étape 1. Fixer le symptôme visible par l'utilisateur

- Quand a-t-il commencé ?
- Affecte-t-il toutes les requêtes ou seulement un endpoint précis ?
- S'agit-il d'un timeout ou d'une erreur immédiate ?
- Un seul host ou toute la fleet est-elle touchée ?
- Un déploiement ou un changement récent de configuration, certificat ou dépendance a-t-il eu lieu ?

Relever un timestamp UTC et un correlation ID.

### Étape 2. Vérifier l'état du gestionnaire de services

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)` signifie essentiellement que le processus principal est vivant.

Cela ne garantit pas la réussite des requêtes métier.

Examiner aussi les propriétés `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile` et la politique de redémarrage de l'unit.

### Étape 3. Examiner l'arbre et l'état des processus

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

Les principaux indices fournis par `STAT` sont les suivants.

- `R` : en cours d'exécution ou runnable
- `S` : sommeil interruptible
- `D` : sommeil non interruptible, généralement dans l'attente d'une E/S
- `T` : arrêté ou tracé
- `Z` : zombie

Un zombie est un processus enfant déjà terminé, mais dont le parent n'a pas récupéré le statut de sortie.

Un zombie lui-même ne consomme presque pas de mémoire, mais une augmentation persistante révèle un probable bug du parent.

### Étape 4. Distinguer le CPU du comportement du scheduler

Le load average n'est pas identique au taux d'utilisation du CPU.

Il peut inclure des tâches runnable et certaines tâches non interruptibles.

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

Examiner ensemble le CPU utilisateur, le CPU système, l'attente d'E/S et les changements de contexte.

Dans un container, un quota de cgroup peut provoquer du throttling.

Même si le host dispose encore de CPU, la workload peut rester limitée.

### Étape 5. Examiner la mémoire par composant

Linux utilise la mémoire disponible comme page cache.

Examiner également l'estimation `available` fournie par `free`.

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

Distinguer la RSS, la taille virtuelle, la mémoire anonyme, les mappings adossés à des fichiers et la mémoire partagée.

Rechercher la trace d'un OOM kill dans le journal du kernel et les événements du cgroup.

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Étape 6. Vérifier les descripteurs et les sockets

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

Comparer la tendance du nombre de descripteurs à la limite correspondante.

Observer si les états de connexion se concentrent dans `SYN-SENT`, `CLOSE-WAIT` ou `TIME-WAIT`.

Une accumulation de connexions `CLOSE-WAIT` peut indiquer que l'application ne ferme pas les sockets après la déconnexion du pair.

### Étape 7. Distinguer la capacité en octets de celle en inodes

```bash
df -h
df -i
findmnt
```

Les inodes peuvent être épuisés alors qu'il reste de l'espace en octets.

Un fichier ouvert puis supprimé n'apparaît plus dans la liste du répertoire, mais continue d'occuper de l'espace.

```bash
lsof +L1
```

Vérifier aussi les options de montage, les remontages en lecture seule et la latence du système de fichiers réseau.

### Étape 8. Examiner les autorisations sur la totalité du chemin

Le mode du fichier ne suffit pas.

Une autorisation de traversée est nécessaire sur chaque répertoire parent.

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

Si SELinux ou AppArmor est utilisé, rechercher également les refus de la politique MAC.

L'exécution en tant que root peut masquer la cause et rompre les frontières d'autorisation.

### Étape 9. Observer les E/S et les syscalls dans un périmètre minimal

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace` peut introduire un overhead et exposer des données sensibles.

L'utiliser brièvement, ne filtrer que les syscalls nécessaires et respecter la politique d'exploitation.

Appliquer les mêmes principes de sécurité à `perf` et aux outils eBPF.

### Étape 10. Arrêter le service en sécurité

Commencer par arrêter le service via son gestionnaire.

```bash
systemctl stop example.service
```

Si nécessaire, envoyer SIGTERM et observer l'état pendant le délai de grâce.

SIGKILL ne doit intervenir qu'en dernier recours.

Avant une terminaison forcée, recueillir les preuves nécessaires : stacks, journaux, descripteurs ou politique de core dump, par exemple.

## Comment lire une unit systemd

### Dépendance et ordre sont deux notions différentes

`After=` définit l'ordre de démarrage, mais n'ajoute pas automatiquement une exigence de dépendance.

`Requires=` et `Wants=` expriment des relations de dépendance.

Le fait que le réseau soit `online` ne signifie pas qu'une dépendance applicative soit réellement prête.

### La politique de redémarrage peut masquer les défaillances

`Restart=on-failure` aide à récupérer après des crashs transitoires.

Cependant, une boucle rapide de crashs peut exercer une pression sur les dépendances.

Vérifier la limite du taux de démarrage et le backoff.

Déclencher une alerte sur les redémarrages répétés et sur la dernière cause de sortie.

### L'environnement d'exécution diffère d'un shell interactif

Le PATH, le répertoire de travail, l'environnement, l'umask et les limites peuvent différer.

Ne pas supposer qu'un profil shell est automatiquement chargé.

Indiquer les chemins nécessaires dans le fichier de l'unit.

Ne pas exposer de secrets dans la source de l'unit ni sur la ligne de commande.

## Exemple pratique : le service est active, mais l'API expire

1. Utiliser une requête synthétique pour fixer l'endpoint et le timestamp.
2. Examiner le MainPID et l'historique des redémarrages avec `systemctl show`.
3. Rechercher dans le journal les timeouts et erreurs de dépendance au même instant.
4. Examiner avec `ss` les états des connexions sortantes.
5. Comparer le nombre de `/proc/<pid>/fd` à sa limite.
6. Examiner le CPU de chaque thread et les états bloqués.
7. Envoyer une requête de diagnostic bornée à l'endpoint en aval.
8. Tester l'hypothèse d'un épuisement du pool de threads ou de connexions.
9. Décider d'un éventuel redémarrage après le drainage du trafic.
10. Après récupération, vérifier le SLI utilisateur et les métriques de ressources.

Après un redémarrage, ne pas l'enregistrer comme une résolution de la cause racine.

Consigner séparément `symptômes atténués par le redémarrage ; cause non confirmée`.

## Checklist de vérification

### Conservation des preuves

- [ ] Le timestamp du symptôme et l'étendue de l'impact ont été consignés.
- [ ] Les changements récents et la version de l'artifact ont été vérifiés.
- [ ] Le journal et l'état des processus ont été recueillis avant le redémarrage.
- [ ] Les politiques relatives aux core dumps et aux informations sensibles ont été vérifiées.
- [ ] La sortie des commandes ne contient aucun secret.

### Processus et ressources

- [ ] L'arbre et le propriétaire des processus ont été vérifiés.
- [ ] Le CPU, la charge et l'attente d'E/S ont été distingués.
- [ ] Les limites du host et du cgroup ont été vérifiées ensemble.
- [ ] La composition de la mémoire et les événements OOM ont été vérifiés.
- [ ] Les descripteurs et l'état des sockets ont été vérifiés.
- [ ] Les octets et les inodes du disque ont tous deux été vérifiés.

### Exploitation du service

- [ ] L'utilisateur d'exécution et l'environnement de l'unit sont explicites.
- [ ] L'arrêt gracieux par SIGTERM a été testé.
- [ ] Les tempêtes de redémarrages sont limitées.
- [ ] La readiness est distinguée de la survie du processus.
- [ ] La conservation du journal et la synchronisation temporelle ont été vérifiées.
- [ ] Les fonctions destinées aux utilisateurs ont été validées après la récupération.

## Échecs fréquents et limites

### Commencer par `kill -9`

Cette commande contourne à la fois le nettoyage et les hooks de diagnostic.

Il faut également tenir compte d'une possible corruption de l'état partagé.

### N'examiner que les métriques du host

Les containers et services systemd peuvent épuiser leurs ressources à l'intérieur des limites du cgroup.

### Supposer qu'une absence de journal signifie qu'aucun événement n'a eu lieu

Des journaux peuvent être perdus à cause d'un crash avant le flush du buffer, de l'échantillonnage, de limites de fréquence ou d'un stockage plein.

Recouper les métriques, événements du kernel et traces.

### Essayer de supprimer immédiatement par un signal un processus à l'état `D`

Le traitement du signal peut être retardé jusqu'à la fin de l'attente non interruptible dans le kernel.

Examiner les E/S sous-jacentes et l'état du périphérique.

### Exécuter un tracing sans limite en production

L'outil de diagnostic lui-même peut créer des problèmes de latence et de disque.

Définir le périmètre, la durée, les filtres et le rollback avant de l'utiliser.

## Références officielles

- [Linux man-pages Project](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [The Linux Kernel cgroup v2 Documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## Conclusion

Le diagnostic Linux ne consiste pas à mémoriser des commandes, mais à lire aux bonnes frontières les preuves exposées par le kernel.

Testons les hypothèses en reliant processus, descripteurs, mémoire, systèmes de fichiers, signaux, cgroups et gestionnaire de services.

Même lorsqu'un redémarrage est nécessaire, il faut d'abord conserver les preuves puis vérifier la récupération au moyen des fonctions destinées aux utilisateurs afin de réduire les incidents récurrents.
