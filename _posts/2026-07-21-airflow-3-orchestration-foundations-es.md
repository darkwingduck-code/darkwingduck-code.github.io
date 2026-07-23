---
title: "Airflow 3 Fundamentos de orquestación: diseño de tiempo, estado y reejecución"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: Diseñe XCom, conexiones, variables, reintentos, reabastecimientos, sensores diferibles, programación de activos y verificación operativa en torno a Airflow 3 DAG, tareas e intervalos de datos.
lang: es
hidden: true
translation_key: airflow-3-orchestration-foundations
---

{% include language-switcher.html %}

## El problema: conectar tareas en orden no crea una canalización operativa

Airflow es un orquestador para desarrollar, programar y observar flujos de trabajo por lotes. No reemplaza el motor informático real ni el transporte de datos de gran volumen. La falta de este límite causa los siguientes problemas.

- El tiempo de ejecución se confunde con el período que se está procesando, por lo que se lee la partición incorrecta.
- Agrega repetición al reintentar la tarea, duplicando datos.
- Pasar un marco de datos a través de XCom infla la base de datos de metadatos.
- Un sensor ocupa un puesto de trabajador durante mucho tiempo.
- `catchup=False` se confunde con una prohibición de reprocesar datos históricos.
- Los secretos y la configuración del tiempo de ejecución se escriben directamente en la fuente DAG.
- El DAG tiene éxito mientras que la frescura y la calidad de los artefactos fallan.

Un flujo de trabajo Airflow operable debe responder tres preguntas claramente.

1. **¿Qué intervalo de datos** ejecuta este proceso DAG?
2. ¿Volver a ejecutar la misma tarea produce **el mismo estado final**?
3. Después de una falla, ¿cómo comprobamos no solo el estado de Airflow sino también **si el artefacto orientado al usuario está en buen estado**?

Las API de Airflow 3 y el comportamiento de este artículo siguen la [documentación oficial de Apache Airflow estable 3.x] (https://airflow.apache.org/docs/apache-airflow/stable/) disponible al momento de escribir este artículo. Las API públicas y los argumentos del operador pueden variar según la versión secundaria y del proveedor, por lo que debe fijar también la documentación de la versión implementada.

## Modelo mental: una ejecución DAG es una instancia de orquestación correspondiente a un intervalo de tiempo o evento

### Distinguir DAG, tareas, instancias de tareas y ejecuciones de DAG

- **DAG**: una definición de flujo de trabajo que contiene programaciones, tareas, dependencias y devoluciones de llamadas.
- **tarea**: una plantilla de trabajo declarada a través de un Operador, Sensor, TaskFlow `@task` o interfaz similar
- **Ejecución DAG**: ejecución de un DAG para un intervalo lógico o evento particular
- **instancia de tarea**: una ejecución real de una tarea dentro de una ejecución particular de DAG

Si la misma definición de tarea se ejecuta diariamente, hay una tarea pero una instancia de tarea en la ejecución DAG de cada día. Un reintento es un nuevo intento realizado por la misma instancia de tarea; un reabastecimiento crea nuevas ejecuciones DAG para intervalos históricos.

La interfaz de creación pública de Airflow 3 se centra en `airflow.sdk`. Los archivos DAG deben utilizar API públicas y operadores de proveedores en lugar de manipular modelos de metadatos internos. Consulte la [documentación de tareas y DAG] oficial (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/) para conocer los conceptos básicos.

### La fecha lógica no es el tiempo de ejecución real

Una programación basada en tiempo tiene un **intervalo de datos**. Si una ejecución diaria de DAG procesa `[2026-01-01 00:00, 2026-01-02 00:00)`, el programador generalmente crea la ejecución después de que finaliza el intervalo. Su fecha lógica representa el inicio del intervalo de datos, no la hora de inicio del reloj de pared.

La [documentación de ejecuciones DAG] (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) oficial explica que una ejecución programada se crea después de que finaliza su intervalo de datos y que la fecha lógica representa el inicio del intervalo. Por lo tanto, elegir una partición con `now()` puede leer datos diferentes después de retrasos, reintentos o reabastecimientos de la cola.

Las tareas basadas en tiempo deben utilizar:

- `data_interval_start`: inicio inclusivo del intervalo
- `data_interval_end`: fin exclusivo del intervalo
- `run_id`: distingue repeticiones manuales o instancias de reposición para el mismo intervalo

La estandarización en intervalos medio abiertos `[start, end)` reduce los eventos de límites duplicados y faltantes.

### Una dependencia es una orden de ejecución, no un transporte de datos.

`extract >> transform` expresa una dependencia de control: la transformación puede ejecutarse después de que la extracción se realice correctamente. Esto no significa que se muevan grandes cantidades de datos entre las memorias de los trabajadores.

Plano de datos recomendado:

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

La base de datos de metadatos Airflow es para el estado de orquestación. Coloque conjuntos de datos, binarios de modelos y marcos de datos reales en el almacenamiento de objetos, bases de datos o motores informáticos adecuados.

## Patrón práctico: primero cree tareas idempotentes basadas en intervalos

### Comprenda los intervalos de datos y la publicación atómica con un ejemplo local seguro

El siguiente DAG crea un archivo por intervalo en `/tmp` y reemplaza atómicamente el mismo destino cuando se vuelve a ejecutar el intervalo. Es para aprendizaje y pruebas locales; en producción, adáptelo a escrituras condicionales de almacenamiento de objetos, transacciones de tablas o semántica de cambio de nombre atómico.

```python
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import DAG, Asset, get_current_context, task


OUTPUT_ROOT = Path("/tmp/airflow-orchestration-example")
PUBLISHED_ASSET = Asset("local-example://orchestration/partitions")


with DAG(
    dag_id="interval_aware_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
) as dag:

    @task(outlets=[PUBLISHED_ASSET])
    def publish_partition() -> dict[str, str]:
        context = get_current_context()
        interval_start = context["data_interval_start"]
        interval_end = context["data_interval_end"]
        run_id = context["run_id"]

        partition = interval_start.format("YYYY-MM-DD")
        target = OUTPUT_ROOT / f"date={partition}" / "result.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        # run_id를 그대로 파일명에 쓰지 않고 안정된 제한 길이 ID로 만든다.
        attempt_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
        staging = target.with_name(f".{target.name}.{attempt_id}.tmp")

        payload = {
            "data_interval_start": interval_start.isoformat(),
            "data_interval_end": interval_end.isoformat(),
        }
        staging.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        staging.replace(target)

        # XCom에는 작은 metadata만 반환한다.
        return {
            "path": str(target),
            "partition": partition,
        }

    @task
    def verify_partition(metadata: dict[str, str]) -> None:
        path = Path(metadata["path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"published partition is invalid: {metadata['partition']}")

    verify_partition(publish_partition())


if __name__ == "__main__":
    dag.test()
```

La [documentación de depuración DAG](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html) oficial proporciona `dag.test()` para una ejecución rápida de tareas en un solo proceso. El éxito local no valida el ejecutor, la red, los permisos o el backend secreto, por lo que se requiere un entorno de integración independiente.

### La idempotencia es un requisito previo para los reintentos y reabastecimientos

Una tarea idempotente produce el mismo estado final después de ejecuciones repetidas con la misma entrada lógica. Esto es más fuerte que simplemente decir "la segunda ejecución tiene éxito".

Patrones prácticos:

- derivar claves de salida de `data_interval_start/end`, no del reloj de pared
- utilice la sobrescritura de partición, la combinación/inserción o el reemplazo según corresponda en lugar de agregar
- terminar la puesta en escena antes de la publicación atómica
- enviar claves de idempotencia deterministas a API externas
- combinar efectos secundarios y marcadores de finalización a través de una transacción o comparar y configurar
- especificar la posición de reinicio y la propiedad de la limpieza después de una finalización parcial

La entrega de correo electrónico, los pagos y la creación de tickets externos pueden producir efectos secundarios duplicados con un simple reintento. No confíe únicamente en la configuración de reintento Airflow; utilice la clave de idempotencia del sistema externo y la consulta de resultados API.

Para lograr reproducibilidad, registre las siguientes entradas excluyendo los secretos.

- DAG ID, tarea ID, ejecute ID y pruebe el número
- inicio/fin del intervalo de datos
- partición/versión de origen y salida URI
- revisión de código/imagen
- recuento de filas, suma de comprobación y resultados de calidad de datos

### Reintentar solo errores transitorios

Errores adecuados para reintentar:

- tiempo de espera temporal de la red
- limitación de velocidad con un reintento explícito
- dependencia temporalmente no disponible
- preferencia del trabajador o bloqueo del proceso

Errores que no se pueden solucionar al reintentar:

- discrepancia entre esquema/código
- credenciales o permisos no válidos
- entrada no válida
- error determinista
- superó persistentemente la cuota de almacenamiento

Establezca un recuento de intentos limitado, un retroceso exponencial, un retraso máximo y un tiempo de espera de ejecución de tareas. Aplicar un recuento alto de reintentos a cada tarea retrasa la detección de incidentes y crea tormentas de reintentos contra las dependencias.

Si la propia biblioteca de una tarea vuelve a intentarlo antes que Airflow, el recuento total de intentos puede multiplicarse. Presuponga qué capa maneja los reintentos rápidos de la red y cuál maneja las reejecuciones a nivel de flujo de trabajo.

## Separe XCom, conexiones, variables y parámetros por función

| Herramienta | Alcance y finalidad | Valores adecuados | Valores a evitar |
|---|---|---|---|
| XCom | comunicación dentro de una instancia de tarea/ejecución DAG | URI, partición, pequeños metadatos JSON | marco de datos, binario grande, punto de control de reintento |
| Conexión | punto final y autenticación para un sistema externo | host, esquema, conexión ID, referencia de credencial | resultado de la tarea, parámetro de negocio |
| Variables | configuración de tiempo de ejecución con ámbito de instalación o de equipo | interruptor de tiempo de ejecución de emergencia, configuración pequeña por implementación | constante versionada, entrada por ejecución, grande JSON |
| Parámetros | entrada validada por DAG-run | modo de procesamiento, fechas/opciones limitadas | secreto de larga duración, resultado entre tareas |

La [documentación de XCom] oficial (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html) establece que XCom es para valores serializables pequeños, no para objetos grandes como marcos de datos. Airflow 3 requiere `task_ids` al recuperar el XCom de otra tarea, y los XCom pueden borrarse antes de volver a intentar una tarea fallida, así que no los utilice como puntos de control duraderos.

Una devolución de TaskFlow es conveniente, pero el objeto completo se puede serializar en XCom. Devuelva un manifiesto como este en lugar del resultado del trabajo externo real.

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

Una conexión hace referencia a una conexión externa mediante `conn_id` lógico, mientras que los ganchos/proveedores manejan las credenciales reales. No coloque URI ni contraseñas sin formato en la fuente DAG. Siga la [documentación de conexiones y ganchos](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html).

Una variable es un almacén de claves/valores de tiempo de ejecución global. La [documentación de variables] oficial (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html) recomienda colocar la configuración en una fuente DAG con versión controlada siempre que sea posible y limitar las variables a valores genuinamente dependientes del tiempo de ejecución. Llamadas repetidas de nivel superior `Variable.get()` para analizar el rendimiento y la disponibilidad de metadatos/búsquedas de backend secreto; léalos en tiempo de ejecución de la tarea o en plantillas.

## Administre secretos en la identidad de ejecución y un backend de secretos, no en DAG

El uso de una conexión Airflow o un nombre de variable no hace que un valor sea seguro automáticamente. Revise las rutas de exposición a través de la base de datos de metadatos, variables de entorno, registros, DAG serializados y entornos de tareas.

Principios recomendados:

- registre solo `conn_id` y nombres secretos lógicos en DAG
- utilizar un backend de secretos externos o una identidad de carga de trabajo
- Separe los ámbitos secretos requeridos por el programador, el procesador DAG, el servidor API y el trabajador.
- minimizar los roles en la nube y los permisos de espacio de nombres por tarea de trabajador
- prefiera credenciales de corta duración a claves de acceso de larga duración
- nunca registre secretos sin procesar, URI de conexión o el entorno completo

Airflow 3 puede configurar un backend de secretos de trabajo independiente. Dado que el orden de las búsquedas y las colisiones de claves son importantes, asegúrese de que el mismo nombre no esté presente en varios servidores durante la migración. Siga la [documentación oficial de Secrets Backend](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html).

El cifrado Fernet y el enmascaramiento UI no protegen el ciclo de vida secreto completo. El proceso de trabajo contiene texto sin formato tan pronto como el código de tarea lee un valor. También se requiere aislamiento de trabajadores, redacción de registros, restricciones de salida, rotación y auditorías.

## Separar la espera de los espacios para trabajadores

### Modos de empuje, reprogramación y aplazamiento

| Modo | Espacio de trabajador mientras espera | Situación adecuada | Principal compensación |
|---|---:|---|---|
| sensor `poke` | continuamente ocupado | esperas muy cortas que requieren controles frecuentes | desperdicia trabajadores durante largas esperas |
| sensor `reschedule` | liberado entre controles | esperas que permiten realizar sondeos cada pocos minutos | programador reprogramación de gastos generales |
| operador diferible | entregado al gatillo y liberado | largas esperas por eventos externos | se requieren operaciones de activación y soporte del proveedor |

La [documentación de sensores] oficial (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) explica la diferencia de uso de ranura entre `poke` y `reschedule`. Según [Operadores y activadores aplazables] (https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html), un activador asincrónico en el activador sondea durante el aplazamiento mientras la tarea libera su espacio de trabajador.

Consulte la documentación de la versión del proveedor para ver si un sensor es compatible con `deferrable=True`; el argumento no se puede agregar arbitrariamente a cada sensor. No coloque el trabajo de bloqueo I/O o CPU en activadores personalizados. Un disparador que bloquea el bucle de eventos puede retrasar muchas tareas aplazadas.

Cada tarea de espera debe tener:

- un `timeout` general
- un intervalo de sondeo o semántica de activación
- si el tiempo de espera causa una falla suave o dura
- un criterio que distingue eventos obsoletos y nuevos
- éxito inmediato si la condición externa ya se cumple
- seguimiento de la salud del activador y la edad de la tarea diferida

Si el sondeo es inevitable, verifique no solo que exista un archivo sino también su partición esperada, marcador de suma de comprobación/compleción y marca de tiempo del evento. No confunda un archivo antiguo de una ejecución anterior con un nuevo éxito.

## La recuperación y el reabastecimiento son controles diferentes para intervalos históricos

### Ponerse al día

Con `catchup=True` en una programación basada en tiempo, el programador puede crear ejecuciones de DAG para intervalos de datos no creados después de `start_date`. La implementación de un DAG nuevo con un `start_date` antiguo puede crear muchas ejecuciones a la vez.

`catchup=False` evita que el programador diario cree automáticamente intervalos históricos faltantes. No significa que las tareas puedan utilizar `now()` o que el reprocesamiento histórico sea imposible.

### Relleno

Un reabastecimiento crea ejecuciones DAG para un rango de fechas histórico explícito. La [documentación de relleno] oficial de Airflow 3 (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html) proporciona comportamiento de reprocesamiento, un `max_active_runs` independiente, orden de ejecución y simulacros.

Primero inspeccione los intervalos que se crearían.

```bash
export DAG_ID='interval_aware_example'
export FROM_DATE='2026-01-01'
export TO_DATE='2026-01-07'

airflow backfill create \
  --dag-id "$DAG_ID" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --dry-run
```

Antes de crearlos, verifique:

- ¿La retención de fuentes aún preserva el intervalo histórico?
- ¿Es el código actual compatible con el esquema histórico?
- ¿Puede la sobrescritura de salida entrar en conflicto con el trabajo posterior simultáneo?
- ¿Son suficientes las cuotas API, la carga de la base de datos y la capacidad del grupo?
- ¿El comportamiento de reprocesamiento coincide con la intención de las ejecuciones exitosas existentes?
- ¿Las dependencias permiten el procesamiento primero de lo más nuevo o de lo más antiguo?

Utilice un grupo o cuota independiente para que la simultaneidad de reabastecimiento no compita sin límites con el tráfico de producción. Juzgue el éxito por el número de particiones, las sumas de verificación, la calidad de los datos y la actualización posterior, así como por el estado de la tarea.

## Cuándo utilizar activos y programación basada en eventos

Un cronograma expresa claramente "procesar el intervalo del día anterior después de esta hora cada día". Si la terminación upstream varía mucho o se deben expresar dependencias entre varios productores, un cronograma que tenga en cuenta los activos puede ser más directo.

Un productor declara un activo de producción; después del éxito, puede programar un consumidor DAG.

```python
import pendulum
from airflow.sdk import DAG, Asset, task


CURATED_ASSET = Asset("object://<BUCKET>/curated/<DATASET>")


with DAG(
    dag_id="asset_producer_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task(outlets=[CURATED_ASSET])
    def publish() -> None:
        # 실제 구현은 output을 완전히 검증한 뒤 atomic publish해야 한다.
        pass

    publish()


with DAG(
    dag_id="asset_consumer_example",
    schedule=[CURATED_ASSET],
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task
    def consume() -> None:
        pass

    consume()
```

Según la [documentación oficial de programación consciente de activos] (https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html), se registra una actualización de activos cuando la tarea del productor se realiza correctamente y el consumidor DAG está programado. Las condiciones AND/OR entre activos y combinaciones con cronogramas son posibles, pero primero defina el orden de los eventos, la duplicación, la fusión y la semántica de reproducción para una lógica compleja.

La [programación basada en eventos](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html) de Airflow 3 puede conectar eventos externos a actualizaciones de activos. No todos los `BaseTrigger` son adecuados; Se requiere un disparador compatible. Si una cola de mensajes proporciona al menos una entrega, diseñe los ID de eventos y la idempotencia para que la entrega duplicada no duplique los resultados.

Los activos no crean automáticamente un catálogo de datos completo. Administre los contratos de nomenclatura, propietario, esquema, actualización, partición y calidad URI por separado. No coloque credenciales ni identificadores personales en los URI de activos ni en `extra`; La documentación oficial asume que estos pueden no estar cifrados y recomienda identificadores públicamente seguros.

## Separar el análisis DAG de la lógica empresarial

El programador y el procesador DAG importan repetidamente archivos DAG. Estas acciones de alto nivel hacen que el análisis sea lento y poco confiable.

- API externo y llamadas a bases de datos
- cargar grandes marcos de datos
- búsquedas repetidas de variables/conexión
- importar bibliotecas pesadas de aprendizaje automático
- estructura de tareas que cambia de forma no determinista según el tiempo actual

Mantenga los archivos DAG enfocados en declaraciones de gráficos y adaptadores delgados. Coloque la lógica de dominio en un paquete Python normal y pruébelo unitariamente sin Airflow.

```text
repository/
├── dags/
│   └── curated_pipeline.py
├── src/
│   └── pipeline_core/
│       ├── extract.py
│       ├── transform.py
│       └── contracts.py
└── tests/
    ├── test_dag_structure.py
    └── test_transform.py
```

Si los conflictos de dependencia proveedor/Airflow son grandes o el cálculo es pesado, haga que la tarea envíe un contenedor o trabajo por separado. La instalación de cada dependencia de carga de trabajo en los trabajadores Airflow amplía las imágenes y aumenta los conflictos entre DAG y el riesgo de actualización.

## Observabilidad: observe juntos el plano de control Airflow y el producto de datos

### Señales del plano de control

- programador y latidos del procesador DAG
- Errores de importación DAG y duración del análisis
- antigüedad de las tareas en cola/programadas
- ejecutor abierto/en cola/en ejecución y espacios de grupo
- recuento de tareas diferidas y estado del activador
- Latencia de la base de datos de metadatos, conexiones y crecimiento del almacenamiento.
- fallos en la entrega remota del registro de tareas

La [documentación de métricas Airflow](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html) oficial proporciona `scheduler_heartbeat`, `dag_processor_heartbeat`, `dag_processing.import_errors` y métricas de grupo, ejecutor y estado de tarea. Verifique los nombres y etiquetas del ejecutor instalado y el backend de telemetría.

### Señales de flujo de trabajo

- DAG ejecución exitosa/falla y duración
- reintento de tareas, tiempo de espera, zombis y fallas en los latidos del corazón
- retraso en la programación: desde el final del intervalo hasta el inicio de la ejecución
- retraso en la cola: tarea programable hasta el inicio real
- finalización de un extremo a otro: intervalo desde el final hasta la publicación de salida

### Señales de datos-producto

- frescura y última partición exitosa
- recuentos de filas esperados/reales y anomalías de volumen
- violaciones de esquema/contrato
- nulos, duplicados e integridad referencial
- conciliación de fuente a salida y sumas de verificación

Un DAG puede tener éxito después de publicar un archivo vacío, mientras que el producto de datos falla. Por el contrario, el usuario SLO puede suspender si una tarea se reintenta y aún produce resultados correctos a tiempo. Conecte las páginas de guardia para que la frescura y la corrección impacten en los artefactos importantes en lugar de en la cantidad de tareas fallidas.

Estructurar registros con DAG/task/run/try/data intervalo/revisión de salida. No registre secretos, URI de conexión ni registros de origen completos. Configure el registro remoto para trabajadores desechables y observe las fallas del backend de registro. Consulte la [documentación de implementación de producción] oficial (https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html).

## Prueba local y lista de verificación de verificación CI

### Capas de verificación rápida

1. Prueba unitaria de la lógica de dominio ordinaria de Python.
2. Verifique cada error de importación y análisis DAG.
3. Pruebe estructuralmente los ID de DAG, los ID de tareas, las dependencias, los cronogramas y las políticas de reintento.
4. Ejecute un intervalo representativo localmente con `dag.test()`.
5. Pruebe las conexiones reales, el backend secreto, el ejecutor y la integración del almacenamiento en la etapa de preparación.
6. Observe un DAG sintético y su frescura después del despliegue en producción.

Las [Mejores prácticas: prueba de un DAG](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag) distinguen las pruebas del cargador DAG, las pruebas unitarias, las autoverificaciones y la verificación provisional.

Ejemplo de prueba CI DagBag:

```python
from airflow.dag_processing.dagbag import DagBag


def test_all_dags_import_without_errors() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    assert dagbag.import_errors == {}


def test_critical_dag_contract() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    dag = dagbag.get_dag("interval_aware_example")

    assert dag is not None
    assert dag.catchup is False
    assert set(dag.task_ids) == {"publish_partition", "verify_partition"}
    assert dag.get_task("publish_partition").downstream_task_ids == {
        "verify_partition"
    }
```

`airflow.dag_processing.dagbag` aparece en los ejemplos de prueba oficiales, pero es una ruta de paquete interna, así que verifique las importaciones de prueba durante las actualizaciones menores de Airflow. Prefiera la interfaz pública Airflow 3 en el código de producción DAG.

Comandos de ejemplo CI:

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

Utilice el mismo núcleo Airflow, proveedor y bloqueo de dependencia de Python en CI como producción. Airflow se comporta como aplicación y biblioteca, por lo tanto, combine las restricciones oficiales con la estrategia de bloqueo de la organización y verifique la compatibilidad entre núcleo y proveedor en la preparación.

Revisión de DAG:

- [] La programación, la zona horaria, `start_date` y la semántica de actualización son claras.
- [] Las tareas derivan particiones de `data_interval_start/end`.
- [] Los reintentos y reposiciones no duplican la salida.
- [] Tiempos de espera, reintentos, grupos y capacidad de dependencia de coincidencia de simultaneidad.
- [] XCom solo transporta pequeños metadatos.
- [] Las conexiones, variables y parámetros están separados por función.
- [] No aparece ningún secreto sin formato en los URI de origen, registros, XCom o activos.
- [ ] Las largas esperas se eliminan de los trabajadores mediante reprogramaciones, aplazamientos o eventos.
- [] El análisis de nivel superior no realiza importaciones de red/DB/heavy.
- [] Las tareas hoja y las reglas de activación no tergiversan el estado general de ejecución de DAG-.

Revisión de operaciones:

- [ ] Se revisó el comportamiento del simulacro de reabastecimiento, la simultaneidad y el reprocesamiento.
- [] Se comprobó la retención de fuentes y la compatibilidad del esquema histórico.
- [ ] Se observan el programador, el procesador DAG, el disparador, el ejecutor y los metadatos DB.
- [] Existen alertas de actualización y corrección de artefactos de usuario.
- [] Existen políticas de retención de registros y limpieza de bases de datos de metadatos.
- [ ] La copia de seguridad de metadatos, la migración, la compatibilidad de proveedores y la preparación se prueban antes de las actualizaciones.
- [] Los permisos de borrado/reintento/relleno de tareas y los registros de auditoría están restringidos.

## Casos de falla y limitaciones

### Usando Airflow como motor de procesamiento de datos

Procesar grandes marcos de datos en la memoria del trabajador y pasarlos a través de XCom rompe la escalabilidad y el aislamiento. Deje que Airflow orqueste la computación externa, como Spark, almacenes y trabajos de contenedores, mientras realiza un seguimiento de pequeños metadatos.

### Usando `now()` como clave de partición

Los reintentos, retrasos en la cola, ejecuciones manuales y reabastecimientos pueden leer o escribir particiones diferentes. Derive entradas lógicas a partir de intervalos de datos y parámetros explícitos.

### Marcar el éxito de la tarea antes de confirmar la salida

Si una tarea envía un trabajo externo asincrónico y tiene éxito antes de verificar su finalización, el trabajo posterior lee datos incompletos. Utilice un operador diferible o un sensor independiente para verificar el estado del terminal y la calidad de la salida antes de tener éxito.

### Uso de XCom como almacén estatal duradero

XCom es para valores pequeños de comunicación de tareas y puede borrarse al reintentar. Almacene puntos de control de larga duración y cargas útiles grandes con versiones en almacenamiento externo, colocando solo referencias en XCom.

### Ocultar la inestabilidad aumentando los reintentos

Los reintentos ayudan a los errores transitorios, pero retrasan la detección de fallas deterministas y aumentan la carga de dependencia. Defina una taxonomía de errores y vuelva a intentar el presupuesto, luego falle con un contexto procesable cuando se agote.

### Expresar cada dependencia a través del sondeo de sensores

Esto aumenta la carga de los trabajadores y del programador y la latencia de sondeo. Si la fuente emite eventos, considere los cronogramas de activos/eventos; si es necesario realizar un sondeo, utilice un sensor diferible y un tiempo de espera.

### Confundir eventos de activos con entrega exactamente una vez

Es posible realizar repeticiones del productor, eventos externos duplicados y reprocesamiento del consumidor después de una falla. Un activo expresa una dependencia, no una transacción comercial. Tanto los productos como los consumidores deben ser idempotentes.

### Creer que Airflow reemplaza el streaming

Airflow se adapta a la orquestación orientada a lotes. Cuando el procesamiento continuo de eventos de baja latencia, el estado por evento y la contrapresión son fundamentales, deje que un procesador de flujo y un sistema de mensajería sean dueños del plano de datos mientras Airflow maneja los flujos de trabajo de administración y conciliación por lotes.

El núcleo de las operaciones de Airflow no es un gráfico DAG elaborado. Se trata de definir los intervalos de procesamiento con precisión, hacer que las tareas se puedan volver a ejecutar, separar los pequeños metadatos de orquestación del plano de datos real y diseñar el reprocesamiento histórico y la respuesta a incidentes desde el principio.
