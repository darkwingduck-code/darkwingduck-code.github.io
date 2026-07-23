---
title: "SQL Principios de normalización y compensaciones prácticas: 1NF, 2NF, 3NF y BCNF"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "A partir de dependencias funcionales y claves candidatas, esta guía explica cómo evaluar 1NF, 2NF, 3NF y BCNF, junto con criterios prácticos para la descomposición sin pérdidas, la preservación de dependencias y la desnormalización."
math: true
lang: es
hidden: true
translation_key: sql-normalization-1nf-2nf-3nf-bcnf
---

{% include language-switcher.html %}

La normalización no es una regla que diga dividir una tabla en muchas partes. Su esencia es **gestionar cada hecho exactamente en un lugar y así reducir las anomalías de actualización**. Para aplicarlo correctamente, primero escriba las dependencias funcionales (las reglas comerciales) en lugar de mirar los nombres de las columnas.

Este artículo evalúa las formas normales en la siguiente secuencia.

$$
\text{Business rules}
\rightarrow
\text{Functional dependencies}
\rightarrow
\text{Candidate keys}
\rightarrow
\text{Normal forms}
\rightarrow
\text{Lossless, dependency-preserving decomposition}
$$

## 1. Las tres anomalías que previene la normalización

Almacenar diferentes hechos de forma redundante en una relación causa los siguientes problemas.

- **Anomalía de actualización**: El mismo hecho aparece en varias filas, pero solo algunas de ellas están actualizadas.
- **Insertar anomalía**: No se puede registrar un hecho independiente a menos que también esté presente otro hecho.
- **Eliminar anomalía**: al eliminar una fila también se elimina la única instancia de un hecho separado.

Por ejemplo, si cada fila de pedido repite el nombre para mostrar del cliente, un cambio de nombre requiere actualizar cada fila histórica. Sin embargo, si el requisito es preservar el “nombre para mostrar en el momento del pedido”, la repetición puede ser una instantánea intencional en lugar de una redundancia. Que la normalización sea apropiada no depende de la forma de una columna, sino de **si su valor representa un hecho actual o un hecho histórico**.

## 2. Dependencias funcionales: reglas, no datos

Para conjuntos de atributos \(X,Y\) en relación \(R\),

$$
X\to Y
$$

significa que dos tuplas cualesquiera con el mismo valor \(X\) deben tener siempre el mismo valor \(Y\). \(X\) determina funcionalmente \(Y\).

Una advertencia importante es que una dependencia funcional no surge simplemente porque la muestra actual no contiene duplicados. Una dependencia debe ser una regla comercial que se aplique a todos los datos válidos que puedan ingresarse en el futuro.

### Dependencia trivial

Si \(Y\subseteq X\), entonces \(X\to Y\) es trivial. Por ejemplo,

$$
\{A,B\}\to A
$$

siempre se cumple independientemente de lo que signifiquen los valores.

### Cierre

El cierre \(X^+\) de un conjunto de atributos \(X\) es el conjunto de todos los atributos que \(X\) puede determinar bajo las dependencias funcionales dadas. Las claves candidatas se identifican mediante cierre.

1. Comience con \(X^+=X\).
2. Para cada \(Y\to Z\), si es \(Y\subseteq X^+\), agregue \(Z\) a \(X^+\).
3. Repita hasta que el conjunto ya no cambie.
4. Si \(X^+=R\), entonces \(X\) es una superclave.
5. Si ningún subconjunto adecuado de \(X\) es una superclave, entonces \(X\) es una clave candidata.

## 3. Distinga los términos clave con precisión

- **Superclave**: un conjunto de atributos que identifica de forma única una fila. Puede incluir atributos innecesarios.
- **Clave candidata**: una superclave mínima que no se puede reducir más.
- **Clave principal**: la clave candidata elegida como clave representativa en una implementación.
- **Clave alternativa**: cualquier clave candidata no seleccionada como clave principal.
- **Atributo principal**: un atributo incluido en al menos una clave candidata.
- **Clave externa**: Un atributo que hace referencia a una clave candidata o única en otra relación.

Agregar una ID de incremento automático como clave principal no borra las claves candidatas comerciales originales ni las dependencias funcionales. Una clave natural que no debe duplicarse aún necesita una restricción `UNIQUE` separada.

## 4. 1NF: Un valor por posición de atributo en una relación

La primera forma normal es el principio relacional de que cada intersección tupla-atributo contiene un valor único del dominio relevante. Las columnas repetidas y las listas de longitud variable dentro de una celda generalmente se separan en sus propias relaciones.

Forma incorrecta:

| id_artículo | etiquetas |
|---|---|
| un identificador | múltiples etiquetas separadas por comas |

Forma normalizada:

~~~sql
CREATE TABLE item (
    item_id BIGINT PRIMARY KEY
);

CREATE TABLE label (
    label_id BIGINT PRIMARY KEY,
    label_name TEXT NOT NULL UNIQUE
);

CREATE TABLE item_label (
    item_id BIGINT NOT NULL REFERENCES item(item_id),
    label_id BIGINT NOT NULL REFERENCES label(label_id),
    PRIMARY KEY (item_id, label_id)
);
~~~

### “Atomic” se refiere a la semántica de la consulta, no al tamaño del tipo de datos

No es necesario dividir una fecha en columnas de año, mes y día para satisfacer 1NF. Si un dominio de fecha se trata como un valor, una columna de fecha es atómica. Por el contrario, almacenar una dirección completa como una cadena puede no violar 1NF, pero una estructura separada es más apropiada si se requiere búsqueda y validación por ciudad.

En lugar de declarar que el uso de un JSON o un tipo de matriz viola automáticamente 1NF, pregunte:

- ¿Los elementos que contiene deben participar en uniones y restricciones relacionales?
- ¿Se actualizan los elementos individuales de forma independiente?
- ¿La base de datos debe hacer cumplir reglas de cardinalidad y duplicación?
- ¿Es una carga útil externa que requiere evolución del esquema?

## 5. 2NF: Eliminar hechos que dependen solo de una parte de una clave candidata compuesta

La segunda forma normal requiere que una relación:

1. estar en 1NF; y
2. no tener ningún atributo no principal que dependa funcionalmente de un subconjunto adecuado de cualquier clave candidata.

En otras palabras, elimina dependencias parciales. Si cada clave candidata consta de un único atributo, no puede ocurrir una violación 2NF.

Considere esta relación.

~~~text
order_line(
  order_id,
  product_id,
  order_time,
  customer_id,
  customer_name,
  product_name,
  quantity,
  agreed_unit_price
)
~~~

Si un producto puede aparecer sólo una vez en un pedido, la clave candidata es \((order\_id, product\_id)\). Supongamos que las reglas de negocio son:

$$
order\_id\to order\_time, customer\_id
$$

$$
product\_id\to product\_name
$$

$$
(order\_id,product\_id)
\to quantity,agreed\_unit\_price.
$$

`order_time` y `customer_id` dependen sólo de `order_id`, parte de la clave, mientras que `product_name` depende sólo de `product_id`; estas dependencias violan 2NF.

Descomponga la relación en:

- encabezado_pedido(id_pedido, hora_pedido, id_cliente)
- producto(id_producto, nombre_producto)
- línea_pedido(id_pedido, id_producto, cantidad, precio_unidad_acordado)

Aquí, el precio unitario acordado es el precio acordado para esa línea de pedido, no el precio actual del producto, por lo que depende de toda la clave compuesta. Pasarlo a la relación de producto simplemente porque los nombres suenan relacionados destruiría el hecho histórico.

## 6. 3NF: Eliminar dependencias indirectas mediante atributos que no son clave

La intuición detrás de la Tercera Forma Normal es que un atributo no clave no debe determinarse indirectamente a través de otro atributo no clave.

En el ejemplo anterior, si

$$
order\_id\to customer\_id
$$

y

$$
customer\_id\to customer\_name
$$

entonces la dependencia transitiva

$$
order\_id\to customer\_name
$$

surge. Almacenar el nombre actual del cliente en cada pedido crea una anomalía de actualización, así que descompóngalo en:

- cliente (id_cliente, nombre_actual)
- encabezado_pedido(id_pedido, hora_pedido, id_cliente)

### El criterio exacto de 3NF

Una relación está en 3NF si, para cada dependencia funcional no trivial \(X\to A\), al menos uno de los siguientes es verdadero:

1. \(X\) es una superclave.
2. \(A\) es un atributo principal.

Esta definición es más precisa para relaciones con múltiples claves candidatas que el mnemotécnico "si una no clave determina una no clave, siempre es una violación".

## 7. BCNF: Cada determinante es una superclave

La forma normal de Boyce-Codd requiere que \(X\) sea una superclave para cada dependencia funcional no trivial \(X\to Y\).

$$
X\to Y\text{ nontrivial}
\quad\Longrightarrow\quad
X\text{ is a superkey}.
$$

BCNF es más fuerte que 3NF.

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

Cada relación BCNF está en 3NF, pero no todas las relaciones 3NF están en BCNF.

### Un ejemplo en 3NF pero no BCNF

Considere la relación

~~~text
assignment(student, course, instructor)
~~~

con las siguientes reglas.

1. A un estudiante se le asigna un instructor para un curso determinado.
2. Cada instructor imparte exactamente un curso.

Las dependencias funcionales son:

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

Las claves candidatas son \((student,course)\) y \((student,instructor)\). Por lo tanto, cada atributo es primo, por lo que se satisfacen las condiciones 3NF.

Sin embargo, `instructor` por sí sola no es una superclave todavía determina `course`, por lo que la relación viola BCNF.

Una descomposición BCNF puede ser:

- instructor_curso(instructor, curso)
- estudiante_instructor(estudiante, instructor)

Esto reduce la duplicación, pero la restricción \((student,course)\to instructor\) original puede resultar difícil de verificar utilizando solo restricciones locales en las tablas individuales. Aquí es donde aparece la compensación entre BCNF y la preservación de la dependencia.

## 8. Dos condiciones para una buena descomposición

### Unirse sin pérdidas

La unión natural de las relaciones descompuestas debe reconstruir la relación original sin introducir tuplas espurias.

Para una descomposición en dos relaciones \(R_1,R_2\), no hay pérdidas si cualquiera de las siguientes condiciones se cumple en el cierre de dependencia funcional:

$$
(R_1\cap R_2)\to R_1
$$

o

$$
(R_1\cap R_2)\to R_2.
$$

La intuición es que los atributos compartidos deben actuar como clave para al menos una de las relaciones.

### Preservación de la dependencia

Una descomposición preserva la dependencia si las dependencias funcionales originales pueden imponerse mediante restricciones locales en cada relación, sin una unión.

La síntesis 3NF es muy adecuada para lograr uniones sin pérdidas y preservación de dependencias. Una descomposición BCNF puede realizarse sin pérdidas, pero no siempre preserva todas las dependencias. Por tanto, “una forma normal superior siempre produce un mejor esquema” es falso.

## 9. Un flujo de trabajo de normalización práctico

### Paso 1: escribir hechos como oraciones

Antes de dibujar un ERD, establezca las reglas comerciales en formas como:

- Una A puede tener varias B.
- Cada B pertenece exactamente a un C.
- ¿Es el precio un atributo actual o una instantánea del momento de la transacción?
- ¿Nunca se reutiliza un identificador durante toda su vida útil?

### Paso 2: enumerar claves candidatas y dependencias funcionales

No considere sólo la clave principal; identificar cada clave candidata. Incluya restricciones únicas, columnas que aceptan valores NULL y validez temporal.

### Paso 3: Obtenga una cobertura mínima

- Divida cada lado derecho en un solo atributo.
- Elimina atributos extraños de cada lado izquierdo.
- Eliminar dependencias redundantes implicadas por las demás.

### Paso 4: Evaluar la forma normal

Comience con 1NF y avance hasta 2NF, 3NF y BCNF. Conecte cada infracción a una actualización, inserción o eliminación de anomalía concreta.

### Paso 5: Verificar la calidad de la descomposición

Verifique la unión sin pérdidas y la preservación de dependencias. Si una restricción abarca varias tablas, documente la transacción, el desencadenante, la alternativa de aserción o la invariante de aplicación que la aplica.

### Paso 6: Diseñar el esquema físico

Agregue PK, UNIQUE, FK, NOT NULL, CHECK e índices. No asuma que la base de datos crea automáticamente un índice en columnas de clave externa; verifique el comportamiento del DBMS en uso.

### Paso 7: Evalúe con consultas reales y escriba rutas

Mida los planes de consulta, la cardinalidad, el bloqueo, la amplificación de escritura y el almacenamiento. Desnormalizar intencionalmente sólo cuando se haya demostrado un problema de rendimiento.

## 10. Cuando la desnormalización es razonable

La normalización es el valor predeterminado para diseñar la fuente lógica de la verdad. Las representaciones derivadas pueden ser apropiadas en los siguientes casos.

### Leer rendimiento

Si los agregados frecuentes o las uniones múltiples son un cuello de botella real, considere una vista materializada, una vista indexada o una tabla de resumen. Especifique las relaciones de origen y la política de actualización.

### Modelos analíticos

Un esquema en estrella OLAP prioriza la simplicidad de las consultas y la eficiencia del escaneo en torno a hechos y dimensiones. Es más seguro verlo como un modelo de publicación transformado que como un reemplazo directo del esquema fuente OLTP.

### Eventos e instantáneas

Una carga útil de evento inmutable puede duplicar algunos valores para preservar el estado en ese momento. Distinga los datos maestros actuales de la verdad de los acontecimientos históricos.

### Preservación de documentos externos

Si una carga útil externa API debe conservarse en su forma original, pueden coexistir tablas de consulta sin formato JSON y normalizadas. El uso de la carga útil sin procesar como único modelo de consulta puede dificultar las restricciones y las migraciones.

Toda desnormalización también debe definir:

- la fuente autorizada;
- el responsable de las actualizaciones;
- el método de actualización síncrona o asíncrona;
- estancamiento aceptable;
- el procedimiento de reconstrucción; y
- una consulta que detecta inconsistencia.

## 11. El tiempo y la historia son dimensiones separadas

"El nombre de un cliente" puede no ser un valor actual.

- nombre canónico actual
- nombre para mostrar en el momento del pedido
- nombre legal durante un período de validez particular
- nombre sin formato recibido en el evento original

Cuando existan requisitos temporales, distinga `valid_from`, `valid_to`, hora del sistema y hora del evento. Si la tabla actual está normalizada pero los valores simplemente se sobrescriben cuando se necesita el historial, se pierde la reproducibilidad.

## 12. Lista de verificación de validación

- [] ¿Las dependencias funcionales son reglas de negocio en lugar de coincidencias en una muestra?
- [] ¿Se han identificado todas las claves candidatas además de la clave principal?
- [] ¿Una clave sustituta oculta duplicados en una clave natural?
- [] ¿Se evaluó la atomicidad de 1NF según el uso y la semántica del dominio?
- [] ¿Se comprobaron las dependencias parciales de una clave compuesta?
- [] ¿Se verificaron las dependencias transitivas a través de atributos no clave?
- [] ¿Se aplicó correctamente la excepción de atributo principal en 3NF?
- [] ¿Se verificó la descomposición BCNF para detectar pérdida de preservación de dependencia?
- [] ¿Se verificó que la descomposición tuviera una unión sin pérdidas?
- [] ¿Se aplican realmente las reglas con las restricciones PK, UNIQUE, FK y CHECK?
- [ ] ¿Se distinguen los hechos actuales de las instantáneas históricas?
- [] ¿Cada valor desnormalizado tiene una política de fuente y actualización?
- [ ] ¿Se verificaron las conclusiones de rendimiento con planes de consulta reales?

## 13. Errores comunes

### La idea errónea de que agregar un ID a cada tabla garantiza 2NF

El hecho de que una clave primaria sustituta sea una sola columna no elimina las dependencias parciales de las claves candidatas comerciales originales. Las anomalías persisten.

### La idea errónea de que NULL simplifica las dependencias funcionales

La semántica de SQL NULL, la lógica de tres valores y el tratamiento de una restricción UNIQUE de NULL varían según DBMS y deben verificarse. Hacer que un identificador de negocio requerido sea anulable oscurece el razonamiento de la clave candidata.

### Diseñar únicamente para reducir las uniones

Las uniones son una operación fundamental de base de datos relacional. Fusionar tablas basadas en una consulta de lectura y al mismo tiempo ignorar el costo de las actualizaciones redundantes y el riesgo de coherencia puede aumentar el costo total del sistema.

### La idea errónea de que la normalización resuelve todos los problemas de integridad

Las formas normales abordan dependencias funcionales y redundancia. Las reglas que involucran restricciones de rango, agregados entre filas, superposiciones temporales o transiciones de estado requieren restricciones y diseño de transacciones adicionales.

### Priorizar mecánicamente BCNF por encima de todo

Una descomposición puede perder la preservación de la dependencia y hacer que una regla sea imposible de verificar sin uniones o desencadenantes complejos. Permanecer en 3NF a veces puede ser más seguro desde el punto de vista operativo.

## Conclusión

1NF, 2NF, 3NF y BCNF no son una secuencia para memorizar; son un marco para identificar y eliminar diferentes causas de despido.

- 1NF: relacionalmente un valor en cada posición de atributo
- 2NF: eliminación de hechos no primos que dependen sólo de una parte de una clave candidata compuesta
- 3NF: control de dependencias indirectas mediante atributos no clave
- BCNF: restricción de cada determinante a una superclave

El objetivo práctico no es el número más alto. Es un **esquema en el que la base de datos aplica consistentemente reglas comerciales, la descomposición no produce pérdidas y las dependencias requeridas se preservan de una manera operativamente viable**.
