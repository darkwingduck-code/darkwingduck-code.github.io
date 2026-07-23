---
title: "Tester les simulations déterministes : invariants, tests fondés sur les propriétés et rejeu"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "Découvrez comment valider des simulateurs déterministes à l'aide d'invariants, de tests génératifs fondés sur les propriétés, d'empreintes d'état et du rejeu d'événements, plutôt qu'avec une poignée d'exemples."
math: true
lang: fr-FR
hidden: true
translation_key: deterministic-simulation-testing-invariants-replay
---

{% include language-switcher.html %}

Si les tests d'une simulation se limitent à « exécuter une entrée représentative et vérifier si le graphique ressemble au précédent », il est difficile de savoir quelle loi une petite modification a enfreinte. À l'inverse, figer un fichier de sortie entier comme fichier de référence fait échouer les tests pour des différences bénignes d'arrondi flottant et peut pérenniser indéfiniment un ancien résultat erroné.

Une stratégie plus robuste combine trois niveaux.

1. **Invariants et relations** que toute exécution correcte doit respecter
2. **Tests fondés sur les propriétés** qui explorent automatiquement un vaste espace d'entrées
3. **Rejeu des graines, événements et états** qui reproduit exactement une défaillance

## 1. Distinguer d'abord trois notions

### Déterminisme

Propriété selon laquelle le même état initial, la même entrée, la même configuration et le même environnement d'exécution produisent les mêmes transitions d'état.

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

doit produire le même \(s_{t+1}\) pour les mêmes \(s_t,u_t,\theta\).

### Reproductibilité

Capacité à recréer ultérieurement, ou dans un autre environnement, un résultat situé dans une plage admise. Elle est plus large que le déterminisme bit à bit et exige des informations sur le code source, les dépendances, la configuration, les données, le compilateur et le matériel.

### Robustesse

Propriété selon laquelle une conclusion reste stable face à des variations acceptables de l'entrée ou de l'environnement. Un programme qui donne toujours la même mauvaise réponse pour une entrée donnée est déterministe, mais il n'est ni robuste ni correct.

## 2. Les entrées cachées qui brisent le déterminisme

Les arguments des fonctions dans le code ne sont pas les seules entrées. Les éléments suivants peuvent également influer sur les transitions d'état.

- graine et algorithme du générateur pseudo-aléatoire
- heure murale et paramètres régionaux
- ordre d'itération des tables de hachage
- ordonnancement des threads et ordre des réductions
- opérations atomiques dans les noyaux GPU
- options du compilateur et calcul rapide
- BLAS, environnement d'exécution et pilote
- ordre d'énumération des fichiers
- variables d'environnement et valeurs de configuration par défaut
- réponses des services externes
- mémoire non initialisée

Par conséquent, « nous avons fixé la graine » ne suffit pas à garantir le déterminisme. Il vaut mieux séparer les flux aléatoires par sous-système afin qu'un changement d'ordre d'exécution ne modifie pas la consommation de nombres aléatoires d'un autre sous-système.

## 3. Un treillis de tests plutôt qu'une pyramide

Un simulateur nécessite plusieurs sortes d'oracles.

| Type de test | Question | Défaillances bien révélées |
|---|---|---|
| test unitaire | Une petite opération se comporte-t-elle comme défini ? | signes, unités, indices, traitement des limites |
| test analytique/de référence | Converge-t-il vers une solution connue ? | implémentation d'une équation ou d'un schéma |
| test d'invariant | Respecte-t-il les lois qui doivent être préservées ? | dérive cumulative, sources manquantes |
| test fondé sur les propriétés | Les propriétés tiennent-elles sur un large domaine d'entrées valides ? | cas limites inattendus |
| test métamorphique | Les relations entre sorties restent-elles correctes après transformation des entrées ? | erreurs logiques dans les problèmes sans oracle |
| test différentiel | Concorde-t-il avec une implémentation indépendante ? | divergence propre à une implémentation |
| test de régression/de référence | Le comportement approuvé est-il resté inchangé ? | changements involontaires |
| test de rejeu | Une défaillance passée peut-elle être reproduite exactement ? | non-déterminisme, état omis |

Aucun de ces types ne remplace les autres. Un test de conservation peut réussir alors que la distribution spatiale est fausse, et une sortie peut correspondre au fichier de référence alors que cette référence est elle-même erronée.

## 4. Transformer les invariants en spécifications exécutables

Un invariant ne doit pas rester une simple phrase dans la documentation : il doit devenir une assertion évaluée à chaque exécution.

### Équation de conservation

Étant donné le bilan général

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

le défaut

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

doit rester dans la tolérance numérique.

### Bornes et positivité

Les états dont le domaine est restreint, comme les probabilités, les concentrations et les fractions massiques, doivent respecter des bornes telles que

$$
0\le x_i\le 1
$$

Il faut aussi vérifier si le schéma autorise un léger dépassement inférieur et si l'écrêtage rompt la conservation. Remplacer simplement les valeurs négatives par zéro peut masquer un bogue.

### Symétrie et équivariance

Si une rotation, une réflexion ou une permutation des coordonnées d'entrée doit induire la même transformation physique de la sortie, testez

$$
f(Tx)=Tf(x)
$$

Cette relation fournit un oracle puissant même lorsque les valeurs de sortie correctes sont inconnues.

### Cohérence dimensionnelle et relations d'échelle

Lorsqu'un changement d'unité exprime le même état physique, les sorties sans dimension doivent rester identiques. Il faut d'abord établir si l'invariance d'échelle vaut réellement pour l'équation directrice et les conditions aux limites.

### Invariants de machine à états

- Ne pas supprimer deux fois une entité inexistante.
- Ne pas retraiter un événement terminé.
- Les quantités de ressources ne deviennent jamais négatives.
- Les horodatages ne diminuent pas à rebours de l'ordre causal.
- Le cycle de vie de chaque identifiant d'entité ne suit que des transitions d'état valides.

## 5. Utiliser ensemble tolérances absolue et relative

La forme élémentaire d'une comparaison en virgule flottante est

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

où \(s\) est une échelle de référence adaptée au problème.

~~~python
def assert_close(actual, expected, *, atol, rtol, scale=None):
    reference_scale = abs(expected) if scale is None else abs(scale)
    error = abs(actual - expected)
    limit = atol + rtol * reference_scale
    assert error <= limit, {
        "actual": actual,
        "expected": expected,
        "error": error,
        "limit": limit,
    }
~~~

L'erreur relative seule est inutilisable lorsque la valeur attendue est proche de zéro, tandis que l'erreur absolue seule est difficile à interpréter pour de grandes valeurs. Une tolérance n'est pas un nombre ajusté après coup pour faire réussir un test ; elle doit constituer un budget d'erreur fondé sur :

- l'erreur de troncature de la discrétisation
- la tolérance du solveur itératif
- les bornes d'accumulation en virgule flottante
- la précision de la mesure ou de l'entrée
- les seuils de décision en aval

## 6. Tests fondés sur les propriétés : générer des propriétés, pas des exemples

Un test fondé sur des exemples ne vérifie que les cas auxquels une personne a pensé. Les tests fondés sur les propriétés génèrent des entrées valides et réduisent une défaillance à un contre-exemple plus simple.

Voici un exemple conceptuel.

~~~python
from hypothesis import given, strategies as st

@given(
    total=st.floats(min_value=0.0, max_value=1.0e3,
                    allow_nan=False, allow_infinity=False),
    fraction=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False),
)
def test_partition_conserves_total(total, fraction):
    left, right = partition(total, fraction)

    assert left >= 0.0
    assert right >= 0.0
    assert_close(
        left + right,
        total,
        atol=1.0e-12,
        rtol=1.0e-12,
    )
~~~

Ces nombres illustrent la forme du code ; ils ne constituent pas des critères pour un projet particulier. Définissez les tolérances réelles à partir de la précision de calcul et du budget d'erreur.

### Qualités d'un bon générateur

- Il respecte les contraintes physiques valides.
- Il génère suffisamment de valeurs limites, de zéros, de très petites valeurs et de vastes plages dynamiques.
- Il ne génère pas indépendamment des variables corrélées.
- Il sépare les tests d'entrées invalides des tests de propriétés dans le domaine valide.
- Il enregistre non seulement la graine fautive, mais aussi l'entrée minimale obtenue après réduction.

Contrairement au fuzzing, qui se contente de soumettre de nombreuses entrées aléatoires à un programme, les tests fondés sur les propriétés énoncent **ce qui doit être vrai**.

## 7. Tests métamorphiques : connaître la relation même lorsque la réponse est inconnue

Pour une simulation complexe, il est difficile de connaître la sortie exacte d'une entrée arbitraire. Testez plutôt la relation attendue entre les sorties lorsque l'entrée est transformée.

Par exemple :

- Modifier l'ordre des entités ne change pas les agrégats invariants par permutation.
- Translater le domaine et la source selon la même symétrie translate la sortie à l'identique.
- Un cas limite avec une source nulle atteint un état simple connu.
- Le total de deux sous-systèmes indépendants combinés égale la somme de leurs totaux individuels.
- L'exécution de deux intervalles de temps consécutifs concorde avec une exécution ininterrompue, dans la limite de l'erreur du point de contrôle.

La dernière relation teste à la fois la propriété de semi-groupe et la sérialisation des points de contrôle.

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

Les solveurs adaptatifs ou la localisation d'événements peuvent emprunter des chemins d'exécution différents ; définissez donc explicitement le niveau d'équivalence requis.

## 8. Données minimales nécessaires au rejeu

Reproduire une défaillance exige **les événements d'entrée et la filiation des états**, et non de simples messages de journal.

### Manifeste d'exécution

~~~yaml
schema_version: 1
run_id: "<opaque-run-id>"
source_revision: "<commit>"
configuration_digest: "<hash>"
input_digest: "<hash>"
dependency_lock_digest: "<hash>"
random_streams:
  initialization: "<seed>"
  events: "<seed>"
execution:
  worker_count: "<count>"
  numeric_mode: "<mode>"
~~~

Remplacez les espaces réservés par des valeurs réelles, sans inclure de secrets, de chemins utilisateur ni de noms d'hôtes internes.

### Journal des événements

Dans une architecture fondée sur l'approvisionnement par événements, attribuez à chaque événement :

- un numéro de séquence strictement croissant ;
- le temps de simulation et le temps logique ;
- le type d'événement et la version du schéma ;
- une charge utile canonique ;
- une empreinte de l'état antérieur ou postérieur ;
- un parent causal ou une clé de corrélation.

Le moteur de rejeu remplace les E/S externes par les réponses enregistrées et applique la séquence d'événements dans le même ordre.

### Point de contrôle

Rejouer depuis le début une longue exécution est coûteux. Enregistrez un point de contrôle versionné avec le journal des événements ultérieurs. Le chargeur doit tester la migration depuis les anciens schémas ou échouer clairement lorsqu'une version n'est pas prise en charge.

## 9. Pièges des empreintes d'état

Une empreinte d'état aide à localiser l'étape où la divergence commence, mais elle n'est pas fiable sans canonisation.

- Trier les clés des tables associatives.
- Fixer le format de sérialisation et la version du schéma.
- Exclure les caches transitoires et les horodatages.
- Définir des règles pour la représentation de NaN et du zéro signé.
- Ne pas hacher les flottants après les avoir arbitrairement arrondis sous forme de chaînes.

Séparez le cœur discret, qui exige une égalité bit à bit, des champs numériques adaptés aux comparaisons avec tolérance. Par exemple, comparez exactement l'ordre des événements et le nombre d'entités, mais comparez les champs continus à l'aide de normes et d'invariants.

## 10. Calcul parallèle et réduction reproductible

L'addition en virgule flottante n'est pas exactement associative.

$$
(a+b)+c\neq a+(b+c)
$$

les résultats d'une réduction peuvent donc varier avec l'ordonnancement des threads. Les options comprennent :

- une partition et un arbre de réduction fixes
- une sommation par paires ou compensée
- un mode déterministe de la bibliothèque
- un accumulateur exact pour les totaux critiques
- un critère d'équivalence numérique plutôt que bit à bit

Une réduction non déterministe peut être autorisée pour des raisons de performances. Dans ce cas, utilisez des tests statistiques ou à tolérance pour vérifier que les résultats restent dans l'enveloppe admise, et documentez dans le contrat que le rejeu exact n'est pas disponible.

## 11. Utiliser sans risque les tests de régression et fichiers de référence

Les tests de référence sont utiles pour détecter les changements d'API, de formats et de trajectoires représentatives, mais ils exigent les principes suivants.

1. Versionnez également la procédure de génération des références.
2. Lors de l'approbation, présentez un résumé lisible des différences.
3. Préférez les grandeurs d'intérêt et invariants essentiels à un gros binaire complet.
4. Précisez les tolérances et l'ordre.
5. Séparez les mises à jour des références de l'exécution ordinaire des tests.
6. Ne vous fiez pas aux tests de référence sans tests analytiques ou d'invariants.

« Écraser automatiquement le fichier de référence avec la nouvelle sortie » désactive les tests de régression.

## 12. Un processus qui transforme les défaillances en actifs

1. Détecter une défaillance en production ou dans un test génératif.
2. Conserver la révision du code source, le manifeste, l'entrée minimale, le journal d'événements et le point de contrôle.
3. Confirmer que le rejeu reproduit la défaillance.
4. Trouver la première empreinte d'état à partir de laquelle la divergence commence.
5. Ajouter le plus petit test d'invariant ou de propriété qui en explique la cause.
6. Après la correction, faire réussir le nouveau test comme la suite existante.
7. Conserver le cas minimal dans le corpus de contre-exemples.
8. Si le non-déterminisme lui-même a causé la défaillance, ajouter un test distinct répétant l'ordonnancement.

## 13. Liste de contrôle de vérification

- [ ] Le déterminisme, la reproductibilité et la correction ont-ils été distingués ?
- [ ] Les entrées cachées et l'environnement d'exécution ont-ils été enregistrés en plus de la graine ?
- [ ] Les flux aléatoires ont-ils été séparés par sous-système ?
- [ ] Les équations de conservation et les bornes critiques sont-elles vérifiées par des assertions d'exécution ou des tests ?
- [ ] Le générateur de propriétés traite-t-il les contraintes physiques et les valeurs limites ?
- [ ] Les relations métamorphiques ont-elles été déduites des règles directrices ?
- [ ] Les tolérances ont-elles une justification numérique et des unités ?
- [ ] Les cibles de comparaison exacte et approximative ont-elles été séparées ?
- [ ] L'entrée réduite et la graine de chaque défaillance ont-elles été enregistrées ?
- [ ] Les schémas d'événements et de points de contrôle sont-ils versionnés ?
- [ ] Les E/S externes ont-elles été figées ou enregistrées pendant le rejeu ?
- [ ] Le contrat de déterminisme de la réduction parallèle est-il explicite ?
- [ ] Les mises à jour des références ne peuvent-elles pas s'exécuter automatiquement sans examen ?

## 14. Pièges et limites

### Une propriété erronée fait échouer un code correct

La monotonie, la symétrie et la positivité peuvent ne pas tenir selon le modèle, les conditions aux limites ou le schéma numérique. Déduisez les propriétés de la spécification et des équations, pas de l'intuition.

### Le rejeu exact n'est pas possible sur toutes les plateformes

Les différences de compilateur, de jeu d'instructions, de fonctions transcendantes et d'ordonnancement GPU peuvent modifier les résultats bit à bit. Il est plus réaliste de définir des niveaux de reproductibilité pris en charge.

- Niveau A : égalité bit à bit avec un binaire et un matériel identiques
- Niveau B : tolérance numérique sur la même architecture
- Niveau C : équivalence interplateforme des grandeurs d'intérêt et des invariants

### Journaliser tout l'état accroît le coût et l'exposition des informations

Combinez journaux d'événements, points de contrôle périodiques et empreintes d'état, avec des politiques de conservation et de masquage. Empêchez dès le schéma que des secrets ou données personnelles entrent dans les charges utiles.

### Le mode déterministe peut différer du chemin de production réel

Un mode monothread réservé aux tests peut réussir alors que le chemin parallèle de production reste invérifié. Comparez le mode de référence déterministe au mode d'exécution réel au moyen de tests différentiels.

## Conclusion

Des tests de simulation solides ne mémorisent pas des valeurs de sortie particulières. Ils encodent **ce qui ne doit jamais être rompu**, **les relations qui doivent tenir lorsque les entrées changent** et **la manière de relancer une défaillance depuis le même état**.

Les invariants transforment la physique et la connaissance du domaine en spécifications exécutables, les tests fondés sur les propriétés découvrent des entrées négligées, et le rejeu transforme une défaillance accidentelle ponctuelle en actif de régression permanent.
