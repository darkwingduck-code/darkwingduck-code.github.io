---
title: "Diseño de contrato primero API: errores, versiones, idempotencia y trabajos asincrónicos"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: Trate un API como un contrato en evolución y de larga duración en lugar de una colección de funciones, y diseñe sus solicitudes, respuestas, errores, reintentos y versiones en consecuencia.
lang: es
translation_key: api-contract-idempotency
hidden: true
---

{% include language-switcher.html %}

La calidad de API no debe juzgarse por la cantidad de puntos finales, sino por **si las personas que llaman pueden predecir el éxito, el fracaso y los reintentos**. Las implementaciones de servidores cambian, pero los contratos persisten entre múltiples clientes y sistemas de automatización.

## Un contrato es más amplio que una respuesta exitosa

Como mínimo, el contrato para una operación incluye lo siguiente.

- Método y camino
- Requisitos de autenticación y autorización.
- Esquemas de ruta, consulta, encabezado y cuerpo.
- Unidades, zonas horarias, rangos y reglas anulables
- Códigos de estado de éxito y esquemas de respuesta.
- Códigos de error y reintento
- Reglas de idempotencia y concurrencia.
- Límites de tarifas y paginación.
- Tiempos de espera o métodos de procesamiento asíncrono

Una especificación legible por máquina como OpenAPI no es simplemente un archivo para generar documentación. Es el punto de referencia que conecta la validación de esquemas, la generación de clientes, las pruebas de contratos y las comprobaciones de cambios importantes.

## Distinguir recursos de empleos

Los recursos basados en sustantivos representan el estado, mientras que los métodos HTTP expresan la intención.

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

No mantenga abierta una conexión síncrona HTTP hasta que haya finalizado un trabajo que lleva minutos.

1. `POST /v1/jobs` valida la entrada y registra un trabajo.
2. El servidor devuelve `202 Accepted`, un `job_id` y un estado URL.
3. El cliente consulta el estado o recibe un webhook o evento.
4. Los estados se hacen explícitos, por ejemplo `queued → running → succeeded | failed | cancelled`.

Las transiciones de estado deben ser unidireccionales y distinguir el motivo del fracaso de si se puede volver a intentar el trabajo.

## Validar entrada estrictamente en el límite

```yaml
components:
  schemas:
    CreateJobRequest:
      type: object
      additionalProperties: false
      required: [source_uri, mode]
      properties:
        source_uri:
          type: string
          format: uri
        mode:
          type: string
          enum: [quick, full]
```

Lo que importa es la política, no la sintaxis YAML.

- Decidir si rechazar o ignorar campos desconocidos.
- Distinguir la omisión de un `null` explícito.
- Reflejar unidades numéricas y rangos permitidos en nombres, descripciones y validación.
- Intercambiar la hora en un formato estándar que incluya un offset y definir la referencia interna.
- Al agregar un valor de enumeración, considere cómo responderán los clientes más antiguos.

## Los errores también tienen un esquema estable

Devolver solo una oración legible por humanos obliga al cliente a analizar el texto.

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request failed validation.",
    "details": [
      {"field": "mode", "reason": "unsupported_value"}
    ],
    "request_id": "req-example",
    "retryable": false
  }
}
```

- `code` es un identificador estable para bifurcación de máquinas.
- `message` es leído por usuarios u operadores.
- `details` estructura problemas a nivel de campo.
- `request_id` conecta casos de soporte con seguimientos.
- No devolver rastros de pila internos, SQL, rutas o secretos externos.

## POST Los reintentos necesitan una clave de idempotencia

Si la conexión se interrumpe después de que un cliente envía una solicitud pero antes de recibir la respuesta, el cliente no puede saber si se creó el trabajo. Enviar incondicionalmente el POST nuevamente puede crear un duplicado.

```text
Idempotency-Key: client-generated-unique-key
```

El flujo básico del servidor es el siguiente.

1. Busque un registro existente mediante la combinación de principal y clave autenticados.
2. En la primera solicitud, almacene el resultado junto con un hash normalizado del cuerpo de la solicitud.
3. Para la misma clave y el mismo cuerpo, devuelva el resultado almacenado.
4. Para la misma clave y diferente cuerpo, rechazar la solicitud por conflicto.
5. Documente el período de retención y las reglas de manejo de solicitudes simultáneas.

Usar solo una "verificación primero" a nivel de aplicación sin una restricción única de base de datos crea una condición de carrera.

## Las modificaciones simultáneas necesitan solicitudes condicionales

Si dos usuarios leen y modifican el mismo recurso, la escritura posterior puede sobrescribir el cambio anterior. La simultaneidad optimista utilizando un número de versión o `ETag` es una solución común.

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

Si la versión ha cambiado, el servidor informa un conflicto para que el cliente pueda volver a leer el estado más reciente.

## La paginación debe tolerar cambios de datos

No devuelva una lista grande de una vez. La paginación compensada es simple, pero las inserciones o eliminaciones cerca del frente pueden causar duplicados u omisiones. Para listas grandes que cambian con frecuencia, la paginación del cursor basada en una clave de clasificación estable es más adecuada.

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

Trate el cursor como opaco e incluya el orden de clasificación, el tamaño máximo de página y las reglas para combinar filtros y cursores en el contrato.

## El control de versiones es una política de cambios, no un último recurso

Clasifica los cambios en tres tipos.

- Compatible: agregar un campo opcional o un nuevo punto final
- Condicionalmente compatible: agregar un valor de enumeración o aflojar una restricción
- Incompatible: eliminar un campo o cambiar su tipo o significado

Mueva los cambios incompatibles a una nueva versión explícita u operación paralela. Administre juntos los avisos de desuso, los períodos de observación, el uso del cliente y los cronogramas de retiro. Agregar un número de versión al URL no completa la gestión de cambios.

## Pruebas de contrato y puertas de implementación

- Validar la especificación.
- Probar que las respuestas del servidor se ajusten a la especificación.
- Verificar que se puedan generar y compilar clientes representativos a partir de la nueva especificación.
- Verifique si hay cambios importantes en relación con la versión anterior.
- Pruebe la autenticación faltante, la autorización insuficiente, los límites de velocidad y los errores de validación.
- Pruebe solicitudes simultáneas con la misma clave de idempotencia.
- Realizar pruebas de humo en puntos finales críticos después de la implementación.

## Lista de verificación de verificación

- [] Se especifican esquemas de error, así como esquemas de solicitud y respuesta.
- [] Las políticas para unidades, zonas horarias, valores que aceptan valores NULL y extensión de enumeración son claras.
- [] Existe una estrategia de prevención de duplicados para solicitudes POST con efectos secundarios.
- [] El trabajo de larga duración se separa en un recurso de estado.
- [] Se evitan las actualizaciones perdidas debido a modificaciones simultáneas.
- [] El orden de paginación es determinista y los cursores son opacos.
- [] CI incluye detección de cambios incompatibles.
- [] Los seguimientos de pila y los detalles de implementación interna no se exponen en errores externos.

## Fallos comunes

- Devolver cada resultado como `200 OK` con formato libre JSON
- No distinguir los errores reintentables de los errores permanentes
- Crear trabajos después de un tiempo de espera del cliente sin evitar duplicados
- Usar diferentes unidades o zonas horarias para el mismo campo en todos los puntos finales
- Eliminar un campo de respuesta y "solo actualizar la documentación"
- Omitir datos cuando cambian durante la paginación compensada

Un buen API oculta los detalles de implementación y al mismo tiempo **especifica un comportamiento suficiente para que las personas que llaman fallen y vuelvan a intentarlo de forma segura**.

## Referencias

- [Especificación de OpenAPI](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — Semántica HTTP](https://www.rfc-editor.org/rfc/rfc9110.html)
