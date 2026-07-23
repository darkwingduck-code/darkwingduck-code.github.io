---
title: "Diseño de acciones GitHub CI/CD: Comience con límites de confianza, no con automatización rápida"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: Aprenda a diseñar flujos de trabajo de acciones GitHub, trabajos y límites de confianza de ejecutores de forma segura con permisos, secretos, entornos, matrices, cachés y simultaneidad.
lang: es
translation_key: github-actions-ci-cd-design
hidden: true
---

{% include language-switcher.html %}

## El problema: un flujo de trabajo pasajero no es lo mismo que un canal confiable

CI/CD reduce el trabajo repetitivo, pero un diseño deficiente conecta los privilegios más poderosos del repositorio con entradas externas. Un flujo de trabajo verifica el código fuente, descarga dependencias, ejecuta pruebas y, en ocasiones, cambia el entorno de producción. En otras palabras, un pequeño archivo YAML sirve simultáneamente como sistema de compilación, intermediario de credenciales y plano de control de implementación.

Si se detiene en "las pruebas se ejecutan automáticamente", persisten los siguientes problemas.

- Cada trabajo comparte un token predeterminado con acceso de escritura.
- El código que no es de confianza de una bifurcación PR puede acceder a secretos.
- Una implementación anterior de la misma rama sobrescribe la implementación más reciente.
- Los cachés y los artefactos pasan a las etapas de ejecución sin comprobaciones de procedencia.
- Sólo una de muchas combinaciones de matrices realiza una validación significativa.
- La compilación y la implementación están acopladas, lo que impide la promoción del mismo artefacto.

El objetivo de un buen oleoducto no es simplemente un cheque verde. Es **un resultado reproducible para la misma entrada, privilegios mínimos, promoción consistente de un artefacto validado y puntos de parada claros en caso de falla**.

## Modelo mental: un flujo de trabajo es un DAG que transmite privilegios y datos

Distinguir las unidades principales de las Acciones GitHub.

- **evento**: entrada externa que inicia una ejecución, como `pull_request`, `push` o `workflow_dispatch`.
- **flujo de trabajo**: un archivo que define eventos y el gráfico de trabajo
- **trabajo**: una colección de pasos que se ejecutan en un corredor. Los sistemas de archivos no se comparten entre trabajos de forma predeterminada.
- **paso**: Una acción o comando de shell
- **runner**: proceso efímero o autohospedado que ejecuta código
- **artefacto**: una salida transferida y retenida explícitamente entre trabajos y flujos de trabajo
- **caché**: una optimización que restaura rápidamente dependencias reproducibles
- **entorno**: un límite de control que agrupa un objetivo de implementación, aprobaciones, reglas de protección y secretos del entorno.

Haga cuatro preguntas en cada límite.

1. ¿Quién controla la entrada?
2. ¿Qué código se ejecuta?
3. ¿Qué tokens y secretos se exponen?
4. ¿Cómo se verifican la procedencia y la integridad de los productos?

### Separar CI de CD

CI valida la calidad de una confirmación y crea un artefacto inmutable. CD promueve un artefacto ya validado a un entorno específico. Si cada entorno lo reconstruye, el "binario que se probó" puede diferir del "binario implementado en producción".

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

Un identificador de implementación debe ser un valor inmutable, como una confirmación SHA, un resumen de imagen o un resumen de artefacto, en lugar de un nombre de rama.

## Patrón práctico: validar RP con privilegios bajos e implementar a través de un límite separado

### Un flujo de trabajo CI con privilegios mínimos

El siguiente ejemplo es un esqueleto básico para un proyecto Python. Adáptelo al archivo de bloqueo del repositorio y a los comandos de prueba.

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

Para facilitar la lectura, el ejemplo utiliza las etiquetas principales de acciones oficiales. En un repositorio de alta seguridad, fije una acción a una **confirmación completa SHA** revisada y actualícela usando una herramienta de actualización de dependencias. Revise la fuente, el mantenedor, la procedencia de la versión y los permisos solicitados de una acción de terceros en lugar de su calificación de mercado.

Una matriz no es mejor simplemente porque sea más grande. Incluya únicamente las dimensiones que el contrato de soporte realmente debe garantizar.

- Biblioteca: las combinaciones de tiempo de ejecución mínimas y más recientes admitidas
- Aplicación: el entorno principal que coincide con la producción, además de entornos con alto riesgo de compatibilidad
- GPU o integración grande: pruebas de humo separadas en cada PR de las pruebas completas programadas

`fail-fast: false` conserva la información de compatibilidad de las combinaciones restantes cuando una falla. Por el contrario, los trabajos costosos generalmente deberían seguir a los trabajos unitarios y de pelusa rápidos y bloquearse con `needs`.

### Distinguir un caché de un artefacto

| Artículo | Caché | Artefacto |
|---|---|---|
| Propósito | Acelere las entradas reproducibles | Transferir y conservar resultados e informes de compilación |
| En una falla | La ejecución debería realizarse correctamente, aunque más lentamente | Una etapa posterior requerida debería fallar |
| Clave | OS, tiempo de ejecución, hash de archivos de bloqueo, etc. | Confirme SHA, cree ID, resuma, etc. |
| Confianza | Asumir posible contaminación y validar | Gestionar procedencia y digerir juntos |

Valide las dependencias restauradas desde un caché con el archivo de bloqueo y los hashes del paquete. No coloque scripts ejecutables arbitrarios ni credenciales de larga duración en una memoria caché. Revise la configuración de eventos y alcance para que una caché grabable desde un PR no fluya hacia un trabajo privilegiado en una rama protegida.

Promociona un artefacto creado una vez en todos los entornos. Limite su período de retención a las necesidades comerciales y verifique su resumen antes de la implementación. Los informes de prueba y la cobertura son datos de observabilidad; no reemplazan el binario de implementación.

### Los trabajos de implementación utilizan entornos y credenciales de corta duración

Ejecute una implementación de producción en un flujo de trabajo separado activado desde una rama o etiqueta protegida, o en un trabajo estrictamente aislado, en lugar de en el flujo de trabajo PR. El siguiente esqueleto demuestra la estructura. Reemplace los valores `<...>` y los SHA de acción con configuraciones para la nube y el repositorio relevantes.

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

Los puntos esenciales son los siguientes.

- Otorgar `id-token: write` solo al trabajo que necesita el intercambio OIDC.
- Restringir la política de confianza en la nube por repositorio, rama o etiqueta y reclamos de entorno.
- Emitir credenciales de corta duración en lugar de almacenar claves de acceso de larga duración como secretos del repositorio.
- Configurar aprobadores, ramas o etiquetas permitidas y secretos específicos del entorno en el entorno `production`.
- Configure la implementación de producción en `cancel-in-progress: false` y haga que la herramienta de implementación sea segura bajo ejecución duplicada.

El uso de OIDC no es automáticamente seguro. Si las condiciones de confianza del lado de la nube son demasiado amplias, un flujo de trabajo en cualquier rama puede obtener el rol de producción.

### Gestione las rutas de exposición secretas, no sólo los “valores” secretos

Almacenar un secreto en el GitHub UI no es el final de la tarea.

- Un argumento de shell puede aparecer en una lista de procesos o en un registro de depuración.
- Transformar o codificar un secreto puede impedir que el enmascaramiento lo reconozca.
- Los objetos de error, los dispositivos de prueba o los artefactos pueden duplicar el valor.
- El disco o los procesos de un ejecutor autohospedado pueden dejar rastros para el siguiente trabajo.

Páselo solo como variable de entorno al paso que lo necesita y nunca imprima el valor completo.

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

El valor predeterminado es no proporcionar secretos protegidos para bifurcar las relaciones públicas. En particular, `pull_request_target` puede recibir privilegios en el contexto de la rama base, por lo que no debe combinarse con un patrón que verifica y ejecuta código PR que no es de confianza. Separe el procesamiento de metadatos, como etiquetas y comentarios, de la ejecución del código en diferentes flujos de trabajo.

### Inyección de expresión separada de las citas de Shell

La interpolación directa de la entrada del usuario, como un título PR, en un bloque `run` puede convertirlo en código shell. Pase el valor a través del entorno y cítelo en el shell.

Forma arriesgada:

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

Forma más segura:

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

Cuando sea posible, evite incluso imprimir las entradas del usuario y utilice la validación de formato y una lista de permitidos.

### Las políticas de concurrencia difieren entre CI y CD

En PR CI, una ejecución anterior pierde valor cuando llega una nueva confirmación, por lo que la cancelación es eficiente.

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

Durante la implementación, la cancelación abrupta de un cambio en curso puede dejar el entorno en un estado intermedio. Serialice las implementaciones en el mismo entorno y utilice la cola de forma predeterminada en lugar de la cancelación. La herramienta de implementación de la aplicación debe admitir idempotencia, tiempos de espera y reversión o avance.

## Lista de verificación de validación

Verifique los siguientes elementos en un PR que cambia un flujo de trabajo:

- [] El disparador responde solo a los eventos y ramas requeridos.
- [] Los `permissions` de nivel superior son de solo lectura, con acceso de escritura solo en trabajos que lo requieran.
- [] Los PR de bifurcación y el código que no es de confianza no pueden acceder a secretos ni a credenciales de implementación.
- [ ] Una política vincula acciones de fuentes confiables a los SHA revisados.
- [] Las dependencias se verifican con un archivo de bloqueo y hashes.
- [] La compilación se realiza correctamente incluso si se pierde el caché.
- [] El artefacto está vinculado a una confirmación o resumen y no se reconstruye en cada entorno.
- [] Las aprobaciones del entorno y la política de confianza en la nube limitan el alcance de la rama y la etiqueta.
- [] CI cancela ejecuciones obsoletas, mientras que CD serializa los cambios en el mismo entorno.
- [ ] Cada trabajo tiene un valor `timeout-minutes` razonable.
- [] Los registros de fallas y los artefactos no contienen secretos ni información personal.
- [] Los nombres de verificación requeridos en la protección de sucursales siguen siendo válidos después del cambio de flujo de trabajo.

Combine la delimitación de esquemas de flujo de trabajo, revisión de dependencias, escaneo de secretos y verificaciones de políticas de acción para una validación estática. Pasar pelusa no es prueba de un diseño de permiso seguro, por lo tanto, revise también el modelo de amenaza para cada evento.

## Casos de falla y limitaciones

### Resolviendo problemas con `permissions: write-all`

Los errores de permiso desaparecen, pero el radio de explosión aumenta. Identifique la operación API requerida y agregue solo el alcance específico a nivel de trabajo.

### Asumir que una etiqueta fija completamente la cadena de suministro

Una etiqueta principal o de versión se puede mover. Una confirmación completa SHA es un punto fijo más sólido, pero el origen y el proceso de publicación de esa confirmación aún requieren revisión. La fijación debe ir acompañada de automatización de actualizaciones y respuesta a vulnerabilidades.

### Uso de una caché como resultado de compilación confiable

Un caché es una optimización y su eliminación no debe afectar la corrección. Transfiera los objetivos de implementación como artefactos explícitos con procedencia.

### Tratar a un corredor autohospedado únicamente como una medida de ahorro de costos

Un ejecutor autohospedado puede tener una superficie de ataque mayor, incluido el acceso a la red, los discos persistentes y los metadatos de la nube. No ejecute relaciones públicas públicas ni bifurque en un corredor persistente; operar aislamiento efímero, restablecimiento de imágenes, restricciones de salida y parches.

### Ejecutando todas las pruebas en cada PR

Cuando la validación se vuelve lenta, los desarrolladores lo solucionan o crean lotes grandes. Coloque el portafolio de pruebas en capas rápidas requeridas, integración basada en rutas de cambio, regresión completa programada y validación posterior a la implementación. Diseñar filtros de ruta de forma conservadora para que no omitan dependencias reales.

Las acciones GitHub no son un problema de sintaxis de YAML; es un problema de diseño de límites de confianza. La separación de eventos, código, credenciales, artefactos y entornos revela una automatización riesgosa mucho antes.
