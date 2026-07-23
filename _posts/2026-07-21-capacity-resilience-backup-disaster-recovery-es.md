---
title: "Capacidad, resiliencia y recuperación ante desastres: desde pruebas de carga hasta restauraciones de copias de seguridad"
date: 2026-07-21 12:09:00 +0900
categories: [Reliability, Operations]
tags: [capacity-planning, resilience, backup, disaster-recovery, load-testing]
description: Un marco de verificación unificado que conecta la planificación de capacidad, la protección contra sobrecargas, las pruebas de resiliencia, la restauración de copias de seguridad, RTO/RPO y la recuperación ante desastres.
lang: es
translation_key: capacity-resilience-backup-disaster-recovery
mermaid: true
math: true
hidden: true
---
{% include language-switcher.html %}

## El problema: una copia de seguridad exitosa y la capacidad de recuperación son afirmaciones diferentes

Medir el rendimiento sólo mientras un servicio está en buen estado no indica nada sobre su comportamiento durante una falla.

Un estado de trabajo de copia de seguridad verde no le dice nada sobre si la copia de seguridad realmente se puede restaurar.

Los siguientes riesgos suelen estar ocultos.

- La carga promedio es baja, pero una breve ráfaga abruma la cola.
- La latencia SLO se viola antes de que comience el ajuste de escala automático.
- Los reintentos crean más carga que el tráfico original.
- Después de la conmutación por error, las zonas restantes carecen de capacidad suficiente.
- Existe una copia de seguridad, pero su clave de cifrado y su configuración IAM no se pueden recuperar.
- Se restauró la base de datos, pero el esquema de la aplicación no coincide.
- El runbook DR existe solo en la memoria de una persona.

La resiliencia no es el número de réplicas. Es evidencia de que la funcionalidad y los datos se recuperaron dentro del tiempo permitido después de una falla.

## Modelo mental: carga normal, sobrecarga, falla y desastre forman un continuo

```mermaid
flowchart LR
    N[Normal] --> P[Peak]
    P --> O[Overload]
    O --> F[Component Failure]
    F --> D[Site or Region Disaster]
    D --> R[Recovery]
    R --> N
```

### La capacidad no es un número único para un solo recurso

El rendimiento de un extremo a otro está limitado por la primera restricción de saturación.

- CPU
- Memoria
- Grupo de conexiones
- Hilo o trabajador
- Ancho de banda de la red
- Almacenamiento IOPS y rendimiento
- Partición de cola
- Bloqueo de base de datos
- Cuota externa API

### Utilice la ley de Little para desarrollar la intuición de colas

En estado estable, la relación entre el número promedio de trabajos simultáneos $L$, la tasa de llegada $\lambda$ y el tiempo promedio en el sistema $W$ es la siguiente.

$$
L = \lambda W
$$

Si la tasa de llegada se mantiene por encima de la tasa de procesamiento, el retraso continúa creciendo.

Incluso con el escalado automático, debe calcular cuánto se acumula durante el retraso del escalamiento horizontal.

### Distinguir RTO de RPO

- **RTO**: el tiempo máximo permitido para restaurar el servicio después de una falla
- **RPO**: el rango de pérdida de datos en un momento dado aceptable durante la recuperación

Pueden diferir según el conjunto de datos y la funcionalidad.

Requerir RPO 0 y RTO inmediato para cada sistema hace que aumenten los costos y la complejidad.

## Flujo de trabajo: establecer una línea base de capacidad

### Paso 1. Registre el modelo de carga de trabajo

- Proporción de cada tipo de solicitud.
- Distribución del tamaño de la carga útil
- Relación lectura/escritura
- Proporción de aciertos de caché
- Tiempo de reflexión del usuario
- Superposición entre el tráfico por lotes y el interactivo.
- Latencia de dependencia externa
- Crecimiento y estacionalidad

Una prueba que repite un usuario promedio no reproduce el sesgo del mundo real.

### Paso 2. Seleccionar SLI representativos

- Rendimiento
- percentiles de latencia
- Tasa de error
- Edad de la cola
- Saturación
- Número de transacciones comerciales exitosas
- Corrección de los datos

La latencia promedio oculta problemas de cola, así que inspeccione los percentiles.

Para evitar omisiones coordinadas, verifique también que el generador de carga no deje de producir nuevas solicitudes debido a respuestas lentas.

### Paso 3. Separar las pruebas de referencia y de límite

Una prueba de referencia examina la estabilidad con la carga objetivo normal.

Una prueba de esfuerzo identifica el punto de inflexión y los modos de falla.

Una prueba de pico examina explosiones repentinas.

Una prueba de remojo examina las fugas y los problemas acumulativos.

Una prueba de punto de interrupción encuentra límites en un entorno aislado de forma segura.

### Paso 4. Verificar el bucle de escalado automático

Sume el retraso en la recopilación de métricas, la ventana de evaluación, el tiempo de aprovisionamiento y el tiempo de preparación.

Compruebe que el activador de escalamiento horizontal no sea demasiado tarde en relación con el usuario SLO.

Revise el drenaje de conexiones y la pérdida de caché durante la ampliación horizontal.

Alinee el recuento máximo de instancias con la capacidad descendente.

### Paso 5. Agregar control de admisión

Rechazar explícitamente solicitudes que un sistema no puede manejar puede respaldar la recuperación mejor que colocarlas en una cola ilimitada.

Utilice cuotas por inquilino, límites de simultaneidad, colas limitadas, plazos y prioridades.

Preservar el tráfico crítico.

Asigne a los reintentos un presupuesto separado.

## Flujo de trabajo: resiliencia del diseño y DR

### Paso 6. Modos de falla del inventario

- Fallo del proceso
- Pérdida de nodo
- Pérdida de zona
- Tiempo de espera de dependencia
- DNS o error de identidad
- Corrupción de datos
- Eliminación accidental
- Compromiso de credenciales
- Pérdida de una región o sitio
- Error del operador

Asigne propietarios para la detección, contención, recuperación y verificación de cada modo.

### Paso 7. Verificar la independencia de la redundancia

Varias réplicas pueden compartir la misma zona, cuenta, credenciales, implementación o configuración.

Marque las causas comunes en el mapa de arquitectura.

Verifique periódicamente que se pueda enviar tráfico real al destino de conmutación por error.

Un modo de espera inactivo es propenso a cambios de configuración y parches.

### Paso 8. Elija los tipos de copia de seguridad y la retención

- Completo, incremental y diferencial.
- Instantánea y volcado lógico
- Registro de transacciones o recuperación de un momento dado
- Copia de seguridad coherente con la aplicación
- Copia inmutable o protegida contra escritura
- Copia entre cuentas o fuera del sitio

La regla 3-2-1 es un punto de partida útil, pero adáptela al modelo de amenaza y a los requisitos reglamentarios.

La copia de seguridad en sí debe estar aislada del ransomware y del compromiso de credenciales.

### Paso 9. Preservar las dependencias de recuperación juntas

Los datos por sí solos no pueden restaurar una aplicación.

- IaC e imágenes
- Migraciones de esquemas
- Configuración
- Claves de cifrado y certificados.
- Arranque IAM
- DNS y control de dominio
- Observabilidad
- Runbooks y contactos.
- Licencia o información de integración externa.

Diseñe un sistema de gestión recuperable sin colocar bytes secretos directamente en los documentos.

### Paso 10. Pruebe la restauración en un entorno aislado

1. Seleccione un punto de recuperación específico.
2. Cree una infraestructura en una cuenta o espacio de nombres limpio.
3. Claves y permisos de arranque.
4. Restaure la copia de seguridad.
5. Alinear el esquema y las versiones de la aplicación.
6. Verificar la integridad y las invariantes comerciales.
7. Realizar una transacción sintética.
8. Registre los RTO y RPO reales.
9. Limpie de forma segura el entorno temporal y las copias confidenciales.

### Paso 11. Distinguir la conmutación por error de la conmutación por recuperación

La recuperación al sitio original después de una conmutación por error exitosa tiene sus propios riesgos.

Decida cómo fusionar las escrituras generadas en ambos lados.

Se necesitan vallas y transferencia de autoridad para evitar la división del cerebro.

DNS TTL, las cachés del cliente y la reutilización de la conexión pueden impedir que el cambio de tráfico se complete inmediatamente.

### Paso 12. Establecer prioridades de recuperación por nivel de servicio

No intente restaurar todas las funciones a la vez.

- Plano de identidad y control.
- Ruta de lectura principal
- Ruta de escritura principal
- Procesamiento asincrónico
- Informes y lotes.
- Funciones no críticas

Establezca el orden según el gráfico de dependencia y el impacto empresarial.

## Ejemplo práctico: probar la pérdida de una zona

### Hipótesis

Incluso si una zona desaparece, el núcleo API SLO permanece dentro de un nivel limitado de degradación.

### Condiciones previas

- Consultar reservas y cupos en el resto de zonas.
- Verificar el comportamiento de conmutación por error de la base de datos
- Verifique PDB y ubicación.
- Definir el umbral de cancelación para el impacto en el cliente.
- Asignar retroceso y observadores.

### Ejecución

1. Registre la línea de base con tráfico canario.
2. Inyecte la falla seleccionada en un alcance pequeño.
3. Observe el enrutamiento de solicitudes y la reubicación de réplicas.
4. Observe los reintentos y la antigüedad de la cola.
5. Observe el restablecimiento de la conexión de la base de datos.
6. Compare el SLO con el umbral de aborto.
7. Restaurar el estado saludable.
8. Verifique las invariantes de datos y el drenaje de atrasos.

### Resultados

Registre el tiempo real de detección, el tiempo de conmutación por error, el error máximo, el tiempo de recuperación y las acciones manuales en lugar de un simple paso/fallo.

## Ejemplo práctico: restauración a un momento dado

Elija un momento hipotético para una eliminación errónea.

Restaure la base de datos en un punto de recuperación justo antes del incidente.

Restaure a una nueva instancia en lugar de sobrescribir la original.

Compare los datos eliminados con las escrituras válidas que se produjeron después.

Cree un plan de corrección que vuelva a aplicar solo los registros necesarios.

Haga que el propietario de la empresa apruebe si todos los datos se pueden revertir a un único momento.

Después de la recuperación, reconstruya el índice de búsqueda, la caché y las tablas derivadas.

## Lista de verificación de verificación

### Capacidad

- [ ] La combinación de carga de trabajo y el pico reflejan el tráfico real.
- [ ] La latencia percentil y la saturación se examinan juntas.
- [] El tráfico de reintento se incluye en el modelo de carga.
- [] Se midieron el retardo de escalado automático y el calentamiento.
- [ ] El control de admisión opera antes de que se alcancen los límites aguas abajo.
- [ ] Se verificó la capacidad restante después de la pérdida de zona.

### Copia de seguridad

- [ ] RPO y la retención se definen para cada conjunto de datos.
- [ ] Las copias de seguridad están aisladas de las credenciales de producción.
- [] Se probó la recuperación de la clave de cifrado.
- [] Existen alertas sobre fallas y antigüedad de las copias de seguridad.
- [ ] Se probaron escenarios de eliminación y corrupción.
- [ ] Se verifican las invariantes comerciales de los resultados restaurados.

### DR

- [ ] RTO y la orden de recuperación se definen para cada nivel.
- [ ] DNS, la identidad y la observabilidad están incluidas en el plan.
- [] Otro operador puede ejecutar el runbook.
- [] La autoridad de conmutación por error y las barreras son explícitas.
- [ ] Se probaron la conmutación por recuperación y la conciliación de datos.
- [] El tiempo de ejercicio real se registra y se compara con el objetivo.

## Fallos y limitaciones comunes

### Convertir una prueba de carga en una competencia por el mayor número de producción

El objetivo no es alardear de un número, sino encontrar el punto de rodilla y un rango de operación seguro.

### Creer que el escalado automático reemplaza la planificación de capacidad

Persisten las cuotas, los retrasos en el aprovisionamiento, los cuellos de botella de estado y los límites posteriores.

### Tratar la replicación como copia de seguridad

La eliminación y la corrupción también pueden replicarse rápidamente.

Es necesario un punto de recuperación independiente.

### Grabación de una restauración de instantánea exitosa como recuperación de servicio

Faltan la conectividad de la aplicación, el esquema, las claves y la verificación de transacciones comerciales.

### Escribir documentación DR sin ejercitarla

Las dependencias, permisos, contactos y comandos cambian con el tiempo.

Los ensayos regulares mantienen el documento válido.

## Referencias oficiales

- [AWS Pilar de confiabilidad bien diseñado](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Libro de Google SRE: Manejo de sobrecarga](https://sre.google/sre-book/handling-overload/)
- [Kubernetes Gestión de recursos](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [NIST SP 800-34 Rev. 1 Guía de planificación de contingencias](https://csrc.nist.gov/pubs/sp/800/34/r1/final)
- [Copia de seguridad y restauración de PostgreSQL](https://www.postgresql.org/docs/current/backup.html)

## Conclusión

La capacidad y la recuperación ante desastres no son documentos separados, sino escalas diferentes de la misma cuestión de confiabilidad.

Mida los límites bajo carga normal, limite la sobrecarga, inyecte fallas y, de hecho, restaure las copias de seguridad.

La recuperabilidad no se demuestra mediante un diagrama de arquitectura, sino mediante restauraciones y registros repetibles que verifican la funcionalidad de cara al usuario.
