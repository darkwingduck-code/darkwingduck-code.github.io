---
title: "Imágenes Docker reproducibles y seguras: del contexto de compilación a la ejecución no raíz"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Diseñe compilaciones de varias etapas, fijación de dependencias, comprobaciones de estado, ejecución no raíz y verificación de imágenes en torno a capas Docker y contextos de compilación.
lang: es
translation_key: docker-reproducible-secure-images
hidden: true
---

{% include language-switcher.html %}

## El problema: puedes mover "Funciona en mi máquina" a una imagen

Los contenedores empaquetan un entorno de ejecución, pero no garantizan automáticamente la reproducibilidad o la seguridad. Si conserva una imagen base `latest`, dependencias desbloqueadas, un contexto de compilación de gran tamaño, el usuario raíz o secretos copiados en la imagen, empaqueta las diferencias ambientales y la superficie de ataque junto con la aplicación.

Dos imágenes pueden diferir incluso cuando se crean a partir del mismo Dockerfile.

- En el momento de la compilación, la etiqueta base apuntaba a un resumen diferente.
- El índice del paquete seleccionó una nueva dependencia.
- Un archivo temporal local ingresó al contexto de compilación.
- Se descargó una rueda nativa diferente para una arquitectura CPU diferente.
- Los metadatos de compilación y las marcas de tiempo difieren.

Por tanto, distingue los objetivos.

1. **Reproducibilidad funcional**: la misma fuente y bloqueo producen el mismo comportamiento.
2. **Reproducibilidad de dependencia**: se seleccionan los mismos artefactos base y de paquete.
3. **Reproducibilidad bit a bit**: incluso el resumen de la imagen generada es idéntico.

Un servicio típico debe alcanzar los dos primeros objetivos antes de extenderse a construcciones y procedencias deterministas cuando los requisitos de la cadena de suministro son más estrictos.

## Modelo Mental: Una Imagen Son Capas Inmutables; un contenedor está en estado de ejecución

Los componentes principales de una compilación Docker son los siguientes.

- **Contexto de compilación**: el conjunto de archivos enviados al constructor
- **Instrucción Dockerfile**: un paso que crea una capa y metadatos de imagen
- **Imagen**: un conjunto inmutable de capas y configuración dirigidas al contenido
- **Contenedor**: una instancia en ejecución que combina una imagen con una capa grabable, un proceso, espacios de nombres y límites de recursos.
- **Registro**: almacenamiento que retiene y distribuye manifiestos de imágenes y blobs.

Cada paso de Dockerfile crea una clave de caché a partir del estado anterior, la instrucción y los archivos que utiliza. Si se copia el código fuente que cambia con frecuencia antes de instalar las dependencias, incluso un pequeño cambio de código invalida la capa de dependencia.

Las etiquetas y los resúmenes también difieren.

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

Una combinación útil es que los humanos busquen lanzamientos por etiqueta de versión, mientras que los sistemas de implementación utilizan resúmenes verificados.

### El aislamiento del contenedor es una capa del límite de seguridad

Los contenedores generalmente no tienen un kernel separado como VM. Utilice tiempos de ejecución sin raíz, seccomp/AppArmor/SELinux, eliminación de capacidades, sistemas de archivos de solo lectura, políticas de red y parches de host juntos. Configurar `USER` como no root en la imagen es un valor predeterminado importante, pero no es un entorno limitado completo.

## Patrón práctico: contexto pequeño, entradas bloqueadas, múltiples etapas y privilegios mínimos de tiempo de ejecución

### Restringir primero el contexto de construcción

Ejemplo `.dockerignore`:

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

`.dockerignore` no es simplemente una herramienta para reducir el tamaño de la imagen. Reduce lo que se envía al constructor y evita que `COPY . .` incluya secretos y archivos innecesarios. Si un proyecto realmente necesita pruebas o documentación en tiempo de ejecución, no las excluya indiscriminadamente; contextos de diseño para cada propósito de construcción.

Incluso si se excluye `.env`, su contenido puede quedar expuesto si ya se ha confirmado en Git o se ha pasado como argumento de compilación. El escaneo secreto y la rotación de credenciales se requieren por separado.

### Un Dockerfile de varias etapas para un servicio Python

El siguiente ejemplo es un esqueleto de servicio que utiliza ruedas binarias bloqueadas mediante hash sin necesidad de un compilador.

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

Este patrón está destinado a hacer lo siguiente.

- Copie el bloqueo de dependencia antes de la fuente para estabilizar el límite de la caché.
- Rechazar artefactos de paquete ausentes del bloqueo con `--require-hashes`.
- Separe la etapa de descarga en tiempo de compilación del tiempo de ejecución.
- Reducir las diferencias en la resolución del usuario en tiempo de ejecución con UID y GID numéricos.
- Utilice el formulario ejecutivo `CMD` en lugar del formulario shell para simplificar la entrega de la señal.
- Haga que la verificación de estado verifique una respuesta HTTP en lugar de simplemente la existencia del proceso de servicio.

En CI, fije la base mediante resumen.

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

Reemplace los marcadores de posición `<...>` con valores que realmente hayan sido revisados. La fijación de resúmenes no impide las actualizaciones; hace que los cambios sean visibles en las solicitudes de extracción. Cuando se publique una solución de vulnerabilidad de imagen base, revise una solicitud de extracción de actualización de resumen automatizada y reconstruya.

Si las extensiones nativas deben compilarse desde el código fuente, instale el compilador y los encabezados en una etapa de creación y copie solo las ruedas resultantes en el tiempo de ejecución. La cadena de herramientas del compilador y las versiones del paquete OS también son entradas, así que inclúyalas dentro del alcance del bloqueo y la procedencia.

### Un archivo de bloqueo representa artefactos exactos, no rangos

Un archivo que contenga solo rangos como los siguientes puede seleccionar diferentes resultados a lo largo del tiempo.

```text
framework>=1.0
client-library
```

Un bloqueo de producción fija versiones y hash a través de dependencias transitivas, y una herramienta de actualización automatizada crea un nuevo bloqueo que luego se prueba. Editar manualmente solo una parte del árbol de dependencias puede producir una resolución inconsistente.

El mismo principio se aplica a los paquetes OS. La ejecución de `apt-get upgrade` en cada compilación puede ser actual, pero no es una entrada reproducible. Elija una política que se ajuste a los requisitos del sistema.

- Incluya el paquete OS configurado en un resumen de imagen base confiable y actualice la base con frecuencia.
- Utilice un repositorio de instantáneas de paquetes y versiones exactas.
- Utilice el canal de imagen base reforzado de la organización.

La respuesta a la vulnerabilidad no es una elección entre "siempre más reciente" y "fijado para siempre". Es un **proceso de actualización y validación periódica de las entradas fijadas**.

### No dejes secretos de construcción en capas e historia.

Evite este formulario:

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

Los argumentos y entornos de compilación se pueden exponer en el historial de imágenes, metadatos, registros y rutas de caché. Utilice un montaje secreto de BuildKit y no imprima el valor dentro de las instrucciones.

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

El script de ejemplo también debe evitar dejar el token en URL, excepciones o registros de depuración. Cuando sea posible, utilice una credencial de corta duración emitida por el servicio de compilación en lugar de un token de larga duración.

### Ejecutar con un sistema de archivos de solo lectura y capacidades mínimas

Agregue una política de tiempo de ejecución al valor predeterminado no raíz de la imagen.

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

Si el servicio debe escribir archivos, no abra todo el sistema de archivos raíz. Monte explícitamente solo las ubicaciones necesarias, como `/tmp`, cargas y cachés. `--privileged`, los montajes de sockets de host y las redes de host debilitan sustancialmente el modelo de aislamiento y no deben usarse como opciones convenientes.

No incluya credenciales en una imagen o en un archivo de entorno normal. Utilice el almacén de secretos y la identidad de la carga de trabajo de la plataforma de implementación, y entregue secretos solo al proceso que los necesita a través de la memoria o un montaje restringido.

### Distinguir vivacidad de preparación en los controles de salud

Un Dockerfile `HEALTHCHECK` representa solo un estado. Un orquestador generalmente separa lo siguiente.

- **Inicio**: ¿Se ha completado la inicialización?
- **Vivecidad**: ¿El proceso está lo suficientemente atascado como para reiniciarlo?
- **Preparación**: ¿Puede aceptar tráfico nuevo ahora?

Un fuerte acoplamiento de la preparación a cada dependencia externa puede eliminar cada réplica del tráfico durante una falla transitoria descendente y amplificar una interrupción en cascada. El punto final debe reflejar la capacidad de manejar tráfico real, pero una falla externa que no se puede solucionar reiniciando no debe convertirse en una falla de actividad.

### Preservar evidencia después de construir una imagen

El resultado del proceso de verificación incluye no solo la imagen, sino también lo siguiente.

- Revisión de fuente e invocación de compilación.
- Resúmenes de imagen base e imagen final.
- SBOM
- Resultados del análisis de vulnerabilidades y fechas de vencimiento de excepciones
- Resultados de la prueba
- Construir procedencia y firmas o atestados.

En el momento de la implementación, no vuelva a resolver la etiqueta; Utilice el resumen aprobado. Alinee la política de retención del registro para que los blobs a los que hace referencia el resumen no se eliminen antes de que finalice el período de implementación.

## Lista de verificación de verificación

Antes de la construcción:

- [] `.dockerignore` excluye datos de Git, secretos, cachés locales y artefactos innecesarios.
- [] Las imágenes base y las dependencias de idioma están bloqueadas en versiones revisadas o resúmenes y hashes.
- [] Las actualizaciones de bloqueo se someten a pruebas automatizadas y revisión de vulnerabilidades.
- [] Los secretos de compilación están ausentes en `ARG`, `ENV`, URL y registros.
- [] Los manifiestos de dependencia se copian antes del código fuente para establecer el límite de la caché.

Revisión de imagen:

- [] La imagen en tiempo de ejecución no contiene compilador, caché del administrador de paquetes ni credenciales de prueba.
- [] `USER` no es root y utiliza valores fijos de UID y GID.
- [ ] El punto de entrada puede recibir señales y apagarse correctamente.
- [ ] El control de salud es rápido, tiene un tiempo de espera y no causa efectos secundarios.
- [ ] Se han inspeccionado los contenidos de la capa, el SBOM y las vulnerabilidades (no solo el tamaño de la imagen).
- [] Se han probado imágenes de múltiples arquitecturas en cada arquitectura de destino real.

Revisión de tiempo de ejecución:

- [] La implementación utiliza un resumen inmutable.
- [] El sistema de archivos raíz es de solo lectura y los montajes grabables están minimizados.
- [] Se aplican eliminación de capacidad, no privilegios nuevos y una capa secundaria.
- [ ] Se definen los límites CPU, memoria y PID y un período de apagado gradual.
- [] Los secretos se entregan desde una identidad en tiempo de ejecución o un almacén de secretos.
- [] Los significados de las sondas de preparación, actividad y puesta en marcha son distintos.

## Casos de falla y limitaciones

### Elegir Alpine basándose únicamente en el tamaño de la imagen

Un tamaño más pequeño no siempre significa menor riesgo u operaciones más rápidas. Compare las diferencias de libc, la falta de ruedas nativas, DNS y el comportamiento de la zona horaria, y la dificultad de depuración. Elija la base más pequeña cuya compatibilidad operativa haya sido validada.

### Suponiendo que una compilación de varias etapas es automáticamente segura

Copiar un sistema de archivos completo en la etapa final con algo como `COPY --from=builder / /` recupera los secretos de compilación y la cadena de herramientas. Copie solo las rutas de artefactos requeridas.

### Realizar autenticación, escrituras o consultas pesadas en una verificación de estado

Las sondas se ejecutan con frecuencia. Una sonda lenta o que cambia de estado se convierte en una fuente de falla en sí misma. Verifique solo la preparación esencial dentro de un tiempo limitado.

### Tratar los resultados del escáner como juicios absolutos

Los escáneres dependen de los inventarios de paquetes y de la calidad del asesoramiento. Son posibles tanto falsos positivos como vulnerabilidades no descubiertas. Revise el código accesible, la explotabilidad y los controles de compensación, mientras asigna a cada excepción un propietario y una fecha de vencimiento.

### Tratando de lograr toda la reproducibilidad solo a través de contenedores

Los esquemas de bases de datos externas, indicadores de funciones, versiones secretas, controladores de hardware, núcleos y dependencias de red permanecen fuera de la imagen. Realice también un seguimiento de los manifiestos de implementación, migraciones, IaC, versiones de configuración y contratos de datos.

Un buen Dockerfile no es simplemente un archivo corto. Es un contrato de construcción que explica qué entradas produjeron qué, qué es innecesario en tiempo de ejecución y bajo qué privilegios se ejecuta el resultado.
