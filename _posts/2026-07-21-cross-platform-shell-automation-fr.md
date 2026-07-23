---
title: "Automatisation multiplateforme et diagnostic avec PowerShell, Bash, Windows et WSL"
date: 2026-07-21 09:50:00 +0900
categories: [Platform Engineering, Automation]
tags: [powershell, bash, windows, wsl, scripting, troubleshooting]
description: Distinguer les différences de shells, processus, chemins et encodages, puis concevoir une automatisation Bash et PowerShell qui échoue immédiatement et peut être relancée sans risque.
lang: fr-FR
hidden: true
translation_key: cross-platform-shell-automation
---

{% include language-switcher.html %}

## Le problème : des commandes qui se ressemblent ont des exécuteurs et des règles de données différents

Lorsqu'on passe de Windows à WSL puis à une CI Linux, l'idée selon laquelle « seul le chemin doit changer » s'effondre souvent. La cause se trouve généralement dans l'une de ces quatre couches.

- Quel shell interprète la syntaxe ?
- Quel exécutable est réellement sélectionné ?
- Comment une chaîne est-elle découpée en arguments et protégée par des guillemets ?
- En quoi les systèmes de fichiers, les encodages, les fins de ligne et les autorisations diffèrent-ils ?

Par exemple, un pipeline PowerShell transmet des objets, tandis qu'un pipeline Bash transmet des flux d'octets. La signification de l'alias PowerShell `curl` a également varié selon les versions, et `/mnt/c/...` sous WSL présente des caractéristiques de performances et d'autorisations différentes de celles d'un système de fichiers Linux.

Le but de l'automatisation multiplateforme n'est pas de forcer un même fichier à s'exécuter dans tous les shells. Il est de **définir un contrat de commande commun et de l'implémenter précisément dans chaque shell**.

## Modèle mental : un shell est à la fois un lanceur de processus et un langage

Une ligne de commande traverse les étapes suivantes.

```text
source text
  -> shell parsing/expansion
  -> executable resolution
  -> argument vector + environment + working directory
  -> process exit code + stdout + stderr
```

Lors du diagnostic d'un échec, isolez l'étape incorrecte.

### Bash est centré sur les flux de texte

```bash
producer | filter | consumer
```

Chaque processus envoie normalement un flux d'octets sur stdout vers stdin du processus suivant. L'analyse peut changer selon les espaces, les sauts de ligne, les caractères NUL et les paramètres régionaux. Considérer les noms de fichiers comme du texte organisé en lignes peut altérer les noms qui contiennent des sauts de ligne.

### PowerShell est centré sur les pipelines d'objets

```powershell
Get-Process | Where-Object CPU -gt 10 | Select-Object Name, CPU
```

Entre les cmdlets, contrairement aux commandes natives, des objets .NET structurés circulent dans le pipeline. Les convertir trop tôt en sortie `Format-Table` ou en chaînes complique le filtrage et la sérialisation qui suivent. Placez la mise en forme de la sortie à la fin du pipeline.

### Rendre explicite le contrat de réussite et d'échec

Une commande automatisable a besoin au minimum du contrat suivant.

- Code de sortie `0` en cas de réussite et différent de zéro en cas d'échec
- Résultats normaux sur stdout et diagnostics sur stderr
- Sortie lisible par machine avec un schéma stable, par exemple JSON
- Opérations destructrices soumises à un indicateur explicite et à une cible validée
- Idempotence pour qu'une nouvelle exécution produise le même état final
- Comportement de nettoyage en cas d'expiration ou d'annulation

Utilisez le code de sortie au lieu de rechercher la chaîne « ERROR » dans les journaux. À l'inverse, une interface en ligne de commande qui renvoie `0` tout en consignant seulement les échecs partiels est difficile à automatiser.

## Patrons pratiques : modes stricts propres à chaque shell et contrat de commande commun

### Squelette de base d'un script Bash

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_NAME="${0##*/}"

usage() {
  printf 'Usage: %s --workspace <directory>\n' "$SCRIPT_NAME" >&2
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

workspace=''
while (($# > 0)); do
  case "$1" in
    --workspace)
      (($# >= 2)) || die '--workspace requires a value'
      workspace="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$workspace" ]] || { usage; exit 2; }
[[ -d "$workspace" ]] || die "workspace is not a directory: $workspace"

workspace="$(cd -- "$workspace" && pwd -P)"
printf 'workspace=%s\n' "$workspace"

python -m pytest -- "$workspace/tests"
```

Signification de chaque option stricte :

- `-e` : quitte lors de l'échec non géré d'une commande simple. Ce comportement n'est pas universel, car les expressions conditionnelles et d'autres contextes font exception.
- `-u` : traite la référence à une variable non définie comme une erreur.
- `-o pipefail` : propage l'échec d'une commande intermédiaire comme échec du pipeline.
- `-E` : aide les fonctions et sous-shells à hériter du gestionnaire `ERR`.

Par défaut, placez les variables entre guillemets doubles et utilisez `--` avec les commandes qui le prennent en charge afin de distinguer les options des chemins. Utilisez un tableau au lieu de construire une commande shell sous forme de chaîne puis de la transmettre à `eval`.

```bash
command=(python -m pytest -q)
if [[ "${RUN_SLOW_TESTS:-0}" == '1' ]]; then
  command+=(--runslow)
fi
command+=(-- "$workspace/tests")

"${command[@]}"
```

Un tableau préserve les frontières entre arguments, même lorsque les chemins contiennent des espaces ou des caractères génériques.

### Squelette de base d'un script PowerShell

```powershell
#requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string] $Workspace
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

try {
    $resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
    Write-Information "workspace=$resolvedWorkspace" -InformationAction Continue

    & python -m pytest -- (Join-Path $resolvedWorkspace 'tests')
}
catch {
    Write-Error -ErrorRecord $_
    exit 1
}
```

Différences principales :

- `Set-StrictMode` détecte les variables non définies et certains accès invalides aux propriétés.
- `$ErrorActionPreference = 'Stop'` transforme les erreurs PowerShell non terminales en erreurs terminales.
- La variable `$PSNativeCommandUseErrorActionPreference` de PowerShell 7.3 et versions ultérieures relie le code de sortie non nul d'une commande native au flux d'erreurs PowerShell.
- `-LiteralPath` traite les caractères tels que `[` et `*` comme des caractères littéraux du chemin plutôt que comme des caractères génériques.
- Exécutez un processus externe avec l'opérateur d'appel `&` et transmettez les arguments comme des valeurs distinctes.

Si des versions plus anciennes de PowerShell doivent être prises en charge, inspectez explicitement le code de sortie immédiatement après une commande native.

```powershell
& <NATIVE_COMMAND> <ARGUMENT_1> <ARGUMENT_2>
if ($LASTEXITCODE -ne 0) {
    throw "native command failed with exit code $LASTEXITCODE"
}
```

Remplacez `<...>` par la commande et les arguments réels. `$?` et `$LASTEXITCODE` n'ont pas la même signification et leur comportement varie selon les versions ; fixez donc la version PowerShell cible et testez-la pour l'automatisation native.

### Donner un contrat JSON à l'interface en ligne de commande commune

Si les enveloppes Bash et PowerShell implémentent chacune une logique métier complexe, elles divergeront rapidement. Placez la logique centrale dans une interface testable écrite en Python, Go, .NET ou un autre langage généraliste, et laissez au shell uniquement la préparation de l'environnement et l'invocation.

```text
tool inspect --workspace <PATH> --format json
```

Exemple de sortie réussie :

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [
    {"name": "configuration", "passed": true}
  ]
}
```

Analysez-la comme un objet dans PowerShell.

```powershell
$result = & tool inspect --workspace $resolvedWorkspace --format json |
    ConvertFrom-Json

if ($result.schema_version -ne 1 -or $result.status -ne 'ok') {
    throw 'inspection failed or returned an unsupported schema'
}
```

Si Bash doit lire un champ, utilisez un analyseur JSON validé. N'analysez pas JSON avec `grep` et `sed`.

### Convertir les chemins Windows et WSL uniquement à la frontière

| Signification | Windows | WSL |
|---|---|---|
| Exemple de projet utilisateur | `C:\work\project` | `/mnt/c/work/project` |
| Projet dans le dossier personnel Linux | Sans objet | `/home/<USER>/project` |
| Séparateur de chemin | `\` ou, selon l'API, `/` | `/` |
| Exemple d'exécutable | `tool.exe` | ELF Linux `tool` |

Lorsqu'un chemin Windows est nécessaire sous WSL, utilisez `wslpath` plutôt qu'un remplacement manuel de chaîne.

```bash
windows_path='C:\work\project'
linux_path="$(wslpath -u -- "$windows_path")"
printf '%s\n' "$linux_path"
```

Dans l'autre sens :

```bash
windows_path="$(wslpath -w -- "$PWD")"
printf '%s\n' "$windows_path"
```

Ne convertissez pas continuellement les chemins dans les deux sens. Effectuez une seule conversion à la frontière de l'adaptateur où un processus Windows est appelé. Les charges Linux comportant de nombreuses compilations, installations de paquets et opérations Git sont généralement plus stables en matière d'E/S de métadonnées et d'autorisations lorsqu'elles s'exécutent dans le système de fichiers Linux de WSL. Validez séparément l'accès depuis les IDE Windows et les politiques de sauvegarde.

### Définir les fins de ligne et les bits d'exécution dans le dépôt

Exemple de `.gitattributes` :

```gitattributes
* text=auto
*.sh text eol=lf
*.bash text eol=lf
*.ps1 text eol=crlf
*.psm1 text eol=crlf
*.yml text eol=lf
*.yaml text eol=lf
Dockerfile text eol=lf
```

PowerShell 7 peut également traiter les fins de ligne LF ; choisissez donc CRLF pour les fichiers `.ps1` selon leur compatibilité avec les outils de l'équipe. L'essentiel est de définir une politique de dépôt cohérente au lieu de s'en remettre au réglage `core.autocrlf` de chaque développeur.

Le bit d'exécution d'un script sous Linux est lui aussi une métadonnée Git.

```bash
git update-index --chmod=+x scripts/check.sh
git diff --summary
```

Comme le bit d'exécution est moins visible dans les systèmes de fichiers Windows, vérifiez l'exécution réelle dans la CI Linux. Tester uniquement avec `bash script.sh` peut masquer les problèmes de shebang ou de bit d'exécution.

### Préciser l'encodage et les paramètres régionaux

Utilisez UTF-8 par défaut pour les fichiers structurés et précisez l'encodage chez le producteur comme chez le consommateur. Ne dépendez pas des différences d'encodage de sortie par défaut entre versions de PowerShell.

```powershell
$data | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
```

Les paramètres régionaux peuvent modifier le tri et les expressions régulières dans les outils Bash. Limitez-les à la portée de la commande lorsque l'ordre des octets est requis pour une comparaison automatisée.

```bash
LC_ALL=C sort -- input.txt > output.txt
```

Forcer toutes les sorties destinées à l'utilisateur dans les paramètres régionaux `C` peut modifier la gestion d'Unicode et les messages ; ne l'appliquez donc qu'aux commandes qui en ont besoin.

### Construire une automatisation relançable

Un script idempotent traite l'état « existe déjà » comme une réussite, compare l'état actuel à l'état souhaité et n'effectue que les changements nécessaires.

Exemple PowerShell :

```powershell
$directory = Join-Path $resolvedWorkspace 'reports'
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
```

Exemple Bash :

```bash
install -d -- "$workspace/reports"
```

Une opération de création via une API externe nécessite une clé d'idempotence, la comparaison de l'état souhaité à l'état actuel et une classification des erreurs autorisant une nouvelle tentative. Réessayer sans condition répète les erreurs d'authentification ou de validation et ne fait qu'épuiser le quota. Le délai exponentiel doit inclure une part aléatoire et une échéance globale.

## Séquence de diagnostic

Constituez un petit faisceau de preuves avant de formuler des hypothèses. N'affichez pas les valeurs secrètes.

### 1. Identifier l'environnement d'exécution

Bash :

```bash
printf 'shell=%s\n' "${BASH_VERSION:-not-bash}"
printf 'cwd=%s\n' "$PWD"
command -V git
git --version
uname -a
```

PowerShell :

```powershell
$PSVersionTable
Get-Location
Get-Command git -All | Select-Object CommandType, Name, Source, Version
git --version
```

### 2. Vérifier les entrées et les frontières

- Répertoire de travail et base utilisée pour découvrir la configuration
- Chemin réel et version de l'exécutable
- Nombre d'arguments et guillemets
- Vérifier seulement si les variables d'environnement existent ; ne pas afficher leur valeur
- Existence, taille, autorisations, fins de ligne et encodage des fichiers
- Nature Windows ou WSL du processus

### 3. Créer une reproduction minimale

N'essayez pas de corriger simultanément l'enveloppe, la tâche de l'IDE et la CI. Exécutez le même programme avec les mêmes arguments dans un petit répertoire temporaire. Si la reproduction minimale réussit, réintroduisez l'environnement et l'enveloppe une couche à la fois.

### 4. Utiliser le traçage avec parcimonie

`set -x` de Bash et `Set-PSDebug -Trace 1` de PowerShell peuvent exposer des secrets en affichant les arguments développés. Activez-les seulement pour la plus petite section possible, dans un environnement local protégé, et désactivez-les avant les commandes contenant des identifiants. N'activez pas la journalisation de débogage de la CI en présence de secrets de production.

### 5. Préserver les codes de sortie et stderr

N'avalez pas les échecs avec `|| true` à la fin d'un pipeline ou un vaste bloc PowerShell `catch {}`. Ne classez que les erreurs précises qui sont acceptables, et propagez toutes les autres à l'appelant en préservant le code de sortie et le contexte d'origine.

## Liste de vérification

- [ ] Les systèmes d'exploitation, shells et versions de shell pris en charge sont-ils précisés ?
- [ ] Le mode strict de Bash et la politique d'erreurs terminales de PowerShell sont-ils appliqués ?
- [ ] Le code de sortie non nul d'une commande native se propage-t-il comme échec du pipeline ?
- [ ] Les chemins et entrées utilisateur restent-ils hors des commandes construites par concaténation et de `eval` ?
- [ ] Les résultats sur stdout sont-ils séparés des diagnostics sur stderr ?
- [ ] La sortie machine utilise-t-elle JSON avec une version de schéma ?
- [ ] Les fins de ligne sont-elles définies dans `.gitattributes` et le bit d'exécution vérifié dans la CI Linux ?
- [ ] L'encodage UTF-8 et la portée des éventuels paramètres régionaux requis sont-ils précisés ?
- [ ] La conversion des chemins Windows/WSL s'effectue-t-elle à une seule frontière d'adaptateur ?
- [ ] Le script peut-il être relancé et valide-t-il précisément les cibles destructrices ?
- [ ] Les nouvelles tentatives comportent-elles une classification des erreurs, un délai progressif, une part aléatoire et une échéance ?
- [ ] Les journaux et traces sont-ils exempts de jetons, d'identifiants et d'informations personnelles ?

Définissez la matrice de test minimale selon le véritable contrat de prise en charge. Testez par exemple Linux+Bash et Windows+PowerShell, et n'ajoutez l'intégration WSL que si nécessaire. Séparez les frontières d'échec au lieu d'imbriquer toutes les combinaisons dans une même tâche.

## Cas d'échec et limites

### Supposer que `set -e` détecte tous les échecs Bash

Son comportement peut surprendre dans des contextes tels que `if`, `while`, `&&` et la substitution de commande. Rendez explicites les conditions et la gestion des erreurs pour les commandes importantes, et utilisez un analyseur statique de shell ainsi que des tests.

### Dépendre de l'analyse de chaînes dans PowerShell

Si la sortie d'une cmdlet est rendue sous forme de texte d'affichage puis relue avec une expression régulière, les paramètres régionaux et la mise en forme la feront échouer. Préservez les propriétés des objets et sérialisez en JSON à la frontière avec un système externe.

### Mélanger au hasard les outils WSL et Windows dans le même arbre de travail

La configuration Git, les observateurs de fichiers, les autorisations, la casse des chemins et les fichiers de verrouillage peuvent entrer en conflit. Choisissez l'environnement d'exécution principal et le propriétaire Git du dépôt, puis accédez-y depuis les autres environnements au moyen d'adaptateurs explicites.

### Implémenter toute la logique dans le shell

Les shells excellent dans l'orchestration courte, mais passez à une interface en ligne de commande généraliste lorsque l'analyse, la concurrence, la validation du domaine et les tests unitaires deviennent complexes. Gardez le shell comme couche de liaison.

### Définir le multiplateforme comme « la même commande »

Ce qui compte n'est pas une syntaxe identique, mais un contrat de résultat identique. Même lorsque les adaptateurs diffèrent selon le système d'exploitation, le système est plus facile à maintenir si les codes de sortie, schémas JSON, règles d'idempotence et de sécurité restent les mêmes.

Le même principe s'applique au diagnostic. Vérifier le shell, l'exécutable, les arguments, le système de fichiers et le résultat du processus, une couche à la fois, transforme la catégorie vague du « problème d'environnement » en une cause reproductible.
