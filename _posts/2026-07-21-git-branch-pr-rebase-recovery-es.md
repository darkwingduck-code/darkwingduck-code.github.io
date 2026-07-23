---
title: "Sucursales, relaciones públicas, fusión, rebase y un manual de recuperación segura de Git"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: Aprenda a elegir una estrategia de integración PR del gráfico de sucursal y confirmación y recupérese de errores de forma segura sin perder datos.
lang: es
translation_key: git-branch-pr-rebase-recovery
hidden: true
---

{% include language-switcher.html %}

## El problema: Los incidentes de Git crecen cuando pasas por alto si el historial se comparte, no debido a un comando

La recuperación es completamente diferente dependiendo de si el mismo error todavía existe solo localmente o ya se ha publicado de forma remota. Puede reescribir las confirmaciones locales con relativa libertad, pero cambiar las confirmaciones públicas en las que otros han basado su trabajo mediante rebase o forzar la inserción altera tanto el historial de sus colegas como los puntos de referencia CI.

Tres preguntas son suficientes para tomar una decisión segura.

1. ¿El cambio que no debe perderse está en el árbol de trabajo, en el área de preparación o en una confirmación?
2. ¿Alguien más ha obtenido ya el compromiso de destino?
3. ¿El resultado deseado es contrarrestarlo con una nueva historia o reescribir la historia existente?

No comience con un comando de recuperación. Primero capture el estado y el gráfico.

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Modelo mental: una rama es un nombre que apunta a una confirmación

Pensar en una rama como una “copia de una carpeta” hace que la combinación y el cambio de base sean difíciles de entender. Una rama es una referencia ligera que apunta a una confirmación ID.

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature` apunta a `F2`, mientras que `main` apunta a `M3`. Hay tres formas representativas de integrar las dos ramas.

| Método | Resultado | Más adecuado para | Precaución |
|---|---|---|---|
| fusionar compromiso | Crea un compromiso de integración con dos padres | Preservar la estructura de sucursales y los compromisos individuales | La historia puede volverse compleja |
| fusión de calabaza | Integra los cambios de PR como una nueva confirmación | Pequeñas características y compromisos de trabajo sin pulir | Los límites de confirmación dentro del PR desaparecen |
| rebase + avance rápido | Las repeticiones cuentan con confirmaciones en la base más reciente | Mantener un historial lineal y compromisos significativos | Los ID de confirmación cambian, así que tenga cuidado al reescribir el historial público |

Antes de rebase:

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

Después de cambiar la base de `feature` a `main`:

```text
M1---M2---M3---F1'---F2'  feature
```

Incluso si `F1'` y `F2'` tienen contenido similar, son objetos nuevos con padres diferentes e ID de confirmación. En lugar de "mover" confirmaciones, rebase **recrea parches** en una nueva base.

### A PR es una unidad de control de cambios más allá del propio Git

Una solicitud de extracción combina una comparación de ramas con los siguientes elementos.

- Discusión y justificación del diseño.
- Pruebas automatizadas y análisis estático.
- Aprobación del propietario del código
- Reglas de protección del entorno de implementación.
- Una decisión de integración auditable.

Por lo tanto, un buen PR no es simplemente “un lugar para cargar código”, sino un paquete que reúne riesgos de cambio, evidencia de validación y métodos de reversión.

## Patrón práctico: ramas cortas, integración explícita y una instantánea antes de la recuperación

### Flujo básico para una rama de funciones pequeña

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

Cuanto más corta es la vida de una rama, menor es su superficie de conflicto. Incluso una característica grande se puede integrar en main con frecuencia dividiéndola con indicadores de características, cambios avanzados en la interfaz y el patrón de expansión/contratación para las migraciones de datos.

Como mínimo, incluya lo siguiente en la descripción PR.

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

### Dos formas de actualizar una rama de funciones con la principal

Si el equipo utiliza un flujo de trabajo basado en combinación:

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

Si el equipo utiliza un flujo de trabajo basado en rebase y usted es efectivamente la única persona que utiliza la rama de funciones:

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

Cuando Git se detenga debido a un conflicto, repita la siguiente secuencia.

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

Si no está seguro de la resolución, vuelva al estado original.

```bash
git rebase --abort
```

Si debe actualizar su rama de funciones remotas existente después de la rebase, use lo siguiente en lugar del `--force` normal.

```bash
git push --force-with-lease
```

`--force-with-lease` intenta sobrescribir la referencia remota solo cuando todavía tiene el valor observado por última vez. No es una garantía absoluta de que se preserve cada nuevo impulso de otra persona, por lo que las reglas de protección de ramas compartidas y los acuerdos de equipo tienen prioridad. No permita empujones forzados a ramas protegidas como `main`.

### Recuperación segura por tipo de error

#### 1. Quiere descartar un cambio que no se ha realizado

Lea primero la diferencia y confirme que es realmente seguro descartarla.

```bash
git diff -- <FILE>
git restore -- <FILE>
```

Debido a que `git restore` cambia el contenido del árbol de trabajo, puede perder los cambios no confirmados. Especifique el nombre del archivo con precisión; Si no está seguro, conserve el cambio primero en un archivo de parche o en una confirmación en una rama temporal.

#### 2. Desea deshacer solo `add` y conservar el contenido editado

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

Esto sólo elimina el cambio y generalmente deja intacto el cambio del árbol de trabajo.

#### 3. Quiere corregir el último mensaje de confirmación local o agregar un archivo faltante

Confirme que la confirmación aún no se ha compartido.

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

La modificación también crea una nueva confirmación ID. Si la confirmación ya se ha publicado, suele ser más seguro agregar una confirmación de seguimiento.

#### 4. Quiere deshacer el efecto de una confirmación pública incorrecta

Registre el cambio opuesto en una nueva confirmación sin eliminar el historial público.

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

Revertir una confirmación de fusión requiere elegir el padre principal y puede afectar futuras fusiones. En este caso, revise el gráfico y el estado de implementación y luego siga el procedimiento del equipo.

#### 5. Parece que se perdió una confirmación después de restablecerla o cambiarla

En la mayoría de los casos, el objeto no se eliminó inmediatamente; la rama simplemente ya no apunta a ella. Busque el `HEAD` anterior en el reflog.

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

Después de crear una rama de recuperación, verifique los archivos y las pruebas, luego seleccione o fusione en la rama normal. El reflog registra los movimientos de referencia en un repositorio local; no es una copia de seguridad permanente. Las políticas de limpieza y el paso del tiempo pueden eliminar objetos.

#### 6. Trabajaste en una rama completamente diferente

No descartes los cambios. Consérvalos en una confirmación o guárdalos en la ubicación actual, luego muévelos. Una confirmación de rama temporal es el método más auditable.

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

Si no desea una confirmación WIP en el historial final, elimínela durante la integración de PR o límpiela con una rebase interactiva antes de su publicación.

### Los modos `reset` difieren en qué tan lejos mueven las tres áreas

| Modo | Sucursal/HEAD | Área de preparación | Árbol de trabajo | Riesgo representativo |
|---|---:|---:|---:|---|
| `--soft` | Movimientos | Conservado | Conservado | Elegir el punto equivocado de la historia |
| predeterminado `--mixed` | Movimientos | Cambiado a compromiso de destino | Conservado | Se elimina el estado por etapas |
| `--hard` | Movimientos | Cambiado a compromiso de destino | Cambiado a compromiso de destino | Pérdida de trabajo no comprometido |

`git reset --hard` no es el primer paso de la recuperación. Si es necesario, conserve la confirmación actual ID y los cambios del árbol de trabajo en un punto seguro separado, verifique la confirmación de destino con `git show` y luego utilícela en un alcance limitado. `revert` es el valor predeterminado para deshacer el historial compartido.

### Hacer que las salvaguardas formen parte de la política del repositorio

La atención humana por sí sola no puede proteger a la principal. Aplique lo siguiente en la configuración del repositorio.

- Permitir cambios solo a través de RP
- Requerir controles de estado para pasar
- Requerir un número mínimo de aprobaciones y descartar aprobaciones obsoletas
- Requerir revisión del propietario a través de CODEOWNERS para conocer las rutas aplicables
- Bloquear la integración mientras las conversaciones sigan sin resolverse.
- Restringir los empujones forzados y la eliminación de ramas.
- El administrador de registros omite como procedimiento de excepción

## Lista de verificación de validación

Antes de integrar un PR:

- [ ] El alcance del cambio se centra en un propósito.
- [] La rama base es correcta, sin confirmaciones ni archivos innecesarios.
- [ ] Se revisaron las rutas de falla y la reversión, además de las pruebas automatizadas.
- [] Se verificó la compatibilidad con versiones anteriores de los datos, API y los cambios de configuración.
- [] El método de integración (fusionar, aplastar o rebase) coincide con la política del repositorio.
- [ ] Las métricas previas y posteriores a la implementación y sus propietarios son claros.

Antes de ejecutar un comando de recuperación:

- [ ] Se capturaron `status`, `log --graph --all` y `reflog`.
- [] Usted determinó si los cambios son solo locales o ya están compartidos.
- [] Se creó una rama de preservación o confirmación.
- [] Los ID de archivo, rama y confirmación se especificaron con precisión.
- [] Si se expuso un secreto, la revocación y reemisión de credenciales se produjo antes de la manipulación de Git.
- [] La diferencia, las pruebas y el gráfico remoto se verificaron nuevamente después de la recuperación.

## Casos de falla y limitaciones

### Integrar una rama longeva de una vez

El problema con los conflictos es su significado, no el número de líneas. En una rama separada durante mucho tiempo, la intención del diseño en ambos lados cambia; Los conflictos de comportamiento pueden surgir incluso sin conflictos de texto. Las relaciones públicas pequeñas y la integración continua reducen el costo de recuperación.

### Reestructurar descuidadamente una sucursal pública

Rebase en sí no es peligroso; sustituir una fundación compartida sin acuerdo sí lo es. Distinga entre limpiar una rama de características personales y cambiar el historial de una rama compartida.

### Decidir que un conflicto se resuelve simplemente eliminando sus marcadores

Eliminar `<<<<<<<`, `=======` y `>>>>>>>` no significa que se haya preservado la intención de ambas partes. Después de resolver un conflicto, vuelva a ejecutar las pruebas relevantes, las verificaciones de tipos y la validación de la migración de datos.

### Pensar que eliminar un secreto del historial de confirmaciones finaliza el incidente

Una vez que se ha insertado un token o una clave, es posible que ya permanezca en clones, registros CI, cachés y bifurcaciones. Primero revoque y reemplace el secreto. Si es necesaria una limpieza del historial, trátela como una respuesta a incidentes independiente coordinada por los administradores del repositorio y todos los usuarios. Un impulso unilateral puede romper la historia colaborativa sin deshacer la exposición.

### Tratar el reflog como una copia de seguridad

El reflog es sumamente útil, pero es un mecanismo de recuperación local y temporal. No reemplaza las políticas de inserción remota, ramas protegidas, etiquetas, retención de artefactos o copia de seguridad del repositorio.

El propósito de una buena estrategia de Git no es un "gráfico bonito". Su objetivo es mantener los cambios pequeños, preservar la evidencia de la revisión y permitir que cualquiera pueda determinar a qué compromiso regresar después de una falla.
