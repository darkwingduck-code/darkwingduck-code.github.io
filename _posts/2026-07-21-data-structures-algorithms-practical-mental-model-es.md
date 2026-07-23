---
title: "Un modelo mental práctico para estructuras de datos y algoritmos: justificación antes de la complejidad"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "Cómo interpretar el análisis Big-O y amortizado como modelos de costos reales y elegir matrices, hashes, montones, árboles y algoritmos de gráficos en función de los requisitos, la corrección y la medición."
math: true
lang: es
hidden: true
translation_key: data-structures-algorithms-practical-mental-model
---

{% include language-switcher.html %}

Memorizar estructuras de datos y algoritmos como una tabla de examen solo deja oraciones como "un hash es \(O(1)\), mientras que un árbol es \(O(\log n)\)". En el diseño real, primero haga las siguientes preguntas.

- ¿Los datos caben en la memoria?
- ¿Qué operación es más frecuente: búsqueda, inserción, extracción del mínimo o consultas de rango?
- ¿Se deben conservar el orden y los duplicados?
- ¿Es importante la latencia en el peor de los casos o es más importante el rendimiento promedio?
- ¿Cuáles son la distribución de los datos y la posibilidad de aportes contradictorios?
- ¿Cuáles son los costos de la localidad, la asignación y la simultaneidad de la caché?

Elegir un algoritmo no es un ejercicio de denominación. Es **el trabajo de traducir los requisitos en un modelo de costos e invariantes de corrección**.

## 1. Definir variables de tamaño antes del análisis

Big-O no tiene sentido si no sabes qué representa \(n\) en la expresión de complejidad.

- Número de elementos de la matriz \(n\)
- Número de vértices \(V\) y aristas \(E\) en un gráfico
- Longitud de la cuerda \(L\)
- Número de consultas \(Q\)
- Dimensión de estado \(d\)
- Número de bits \(b\) en un valor entero

Por ejemplo, describir un algoritmo gráfico incondicionalmente como \(O(n^2)\) borra la distinción entre gráficos dispersos y densos. BFS basado en una lista de adyacencia es

$$
\Theta(V+E)
$$

mientras se escanea una matriz de adyacencia completa

$$
\Theta(V^2)
$$

La representación, no sólo el nombre del algoritmo, cambia la complejidad.

## 2. Gran O, Gran Theta y Gran Omega

### Límite superior: \(O(g(n))\)

Si hay una constante \(c\) tal que, para \(n\) suficientemente grande,

$$
0\le f(n)\le c\,g(n)
$$

luego \(f(n)=O(g(n))\). Como se trata de un límite superior, una función en \(\Theta(n)\) también se puede describir como \(O(n^2)\). Siempre que sea posible, el enlace ajustado \(\Theta\) transmite más información.

### Asintóticamente el mismo orden: \(\Theta(g(n))\)

si

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

luego \(f(n)=\Theta(g(n))\).

### Límite inferior: \(\Omega(g(n))\)

Si \(f(n)\ge c\,g(n)\) es un \(n\) suficientemente grande, es un límite inferior.

### Califica peor, promedio y esperado

"La búsqueda de hash es \(O(1)\)" es generalmente una declaración esperada o amortizada que asume un hash y un factor de carga adecuados. El peor de los casos difiere cuando las colisiones están concentradas. Distinguir lo siguiente.

- Peor caso por operación
- Costo esperado sobre la aleatorización
- Caso promedio bajo una distribución de entrada específica
- Costo amortizado durante una secuencia de operación.

Promedio y amortizado no significan lo mismo.

## 3. Análisis amortizado: Distribuir operaciones raras y costosas en toda la secuencia

Cuando una matriz dinámica alcanza su capacidad, crear un búfer más grande y copiar todos los elementos puede hacer que un agregado cueste \(\Theta(n)\). Pero si la capacidad crece en un factor constante, el número total de copias en los anexos \(m\) está limitado por una serie geométrica.

$$
1+2+4+\cdots < 2m.
$$

Por lo tanto, el costo total de los anexos \(m\) es \(\Theta(m)\) y el costo amortizado por anexo es \(\Theta(1)\).

El análisis amortizado no es un promedio empírico que diga que "fue rápido la mayor parte del tiempo". Demuestra que **el costo total no excede el límite para ninguna secuencia de entrada**.

Los métodos de prueba representativos son:

- Método agregado: suma directamente el costo de toda la secuencia
- Método contable: cargar crédito por adelantado a operaciones baratas
- Método potencial: incluir cambios en el potencial de la estructura de datos en el costo.

En un sistema con una fecha límite de latencia, el \(O(1)\) amortizado puede no ser suficiente. Determine si una pausa \(O(n)\) para cambiar el tamaño es aceptable y si es necesaria una repetición incremental o una reserva de capacidad.

## 4. La complejidad es un costo multidimensional

Al elegir basándose únicamente en la complejidad del tiempo se pierde:

- Memoria auxiliar
- Número de asignaciones
- Errores de caché y persecución de puntero
- Predicción de sucursales
- Tamaño de serialización
- Contienda paralela
- Tiempo de preprocesamiento
- Ratio de actualizaciones a consultas.

Incluso en el mismo \(O(n)\), escanear una matriz contigua puede ser mucho más rápido que atravesar una estructura vinculada. Por el contrario, una lista vinculada puede resultar ventajosa para desvincularla cuando ya hay disponible un puntero al nodo intermedio. No se debe omitir el costo de encontrar ese nodo.

## 5. Un mapa de selección de estructura de datos

### Matriz / matriz dinámica

**Fortalezas**

- Acceso al índice en \(\Theta(1)\)
- Memoria contigua y buena localidad de caché
- Amortizado \(\Theta(1)\) anexar al final
- Adecuado para clasificación, búsqueda binaria y procesamiento vectorizado.

**Debilidades**

- La inserción o eliminación en el medio es \(\Theta(n)\) porque los elementos se mueven
- Cambiar el tamaño de los picos y la capacidad adicional
- Los punteros estables pueden quedar invalidados.

Este es un incumplimiento muy fuerte. Compruebe si la “lista” de un idioma es en realidad una matriz dinámica o una lista vinculada.

### Lista enlazada

**Fortalezas**

- \(\Theta(1)\) inserción y eliminación cuando ya se conoce la posición del nodo
- Estructuras que necesitan empalmes y referencias de nodos estables.

**Debilidades**

- Acceso al índice y búsqueda en \(\Theta(n)\)
- Asignación por nodo y sobrecarga de puntero
- Pobre localidad de caché

No seleccione uno simplemente porque "hay muchas inserciones". Si encontrar el punto de inserción cuesta \(\Theta(n)\), la ventaja general puede desaparecer.

### Tabla hash

**Fortalezas**

- Búsqueda, inserción y eliminación basadas en claves esperadas \(\Theta(1)\)
- Membresía, recuento de frecuencia y deduplicación.

**Debilidades**

- No apto para consultas de rango y orden de claves.
- Depende de la calidad del hash y del factor de carga.
- Costo de repetición
- Riesgos de colisiones adversarias y claves mutables.

La igualdad y el hash deben ser consistentes.

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

Cambiar un campo involucrado en la igualdad después de usar un objeto como clave puede hacer que la entrada sea imposible de encontrar.

### Árbol de búsqueda equilibrado

**Fortalezas**

- Búsqueda, inserción y eliminación de \(\Theta(\log n)\) en el peor de los casos
- recorrido ordenado
- Predecesor y sucesor
- Consultas de rango

**Debilidades**

- Constantes y punteros más grandes que una tabla hash
- Complejidad de las implementaciones de equilibrio.

Es apropiado cuando se requiere un mapa o conjunto ordenado, consultas de intervalo o un comportamiento predecible en el peor de los casos.

### Montón/cola de prioridad

Para un montón binario:

- Inspeccionar mínimo o máximo: \(\Theta(1)\)
- Empuje: \(\Theta(\log n)\)
- Pop mínimo o máximo: \(\Theta(\log n)\)
- Busque una clave arbitraria entre todos los elementos desordenados: \(\Theta(n)\)
- Amontonamiento a granel: \(\Theta(n)\)

Un montón no es un "contenedor ordenado". Garantiza sólo la prioridad de la raíz. Úselo cuando extraiga repetidamente el siguiente elemento de mayor prioridad, como en top-\(k\), programadores y la frontera de Dijkstra.

### Deque

Utilice uno cuando una cola necesite \(\Theta(1)\) push and pop en ambos extremos. En BFS, evite eliminar repetidamente desde el frente de una matriz y provocar cambios en \(\Theta(n)\).

### Unión de conjunto disjunto

Cuando se fusionan conjuntos repetidamente y se consulta la conectividad, la compresión de rutas con unión por rango o tamaño proporciona un costo amortizado por operación efectivamente cercano a constante:

$$
O(\alpha(n))
$$

No es adecuado cuando se requiere la eliminación dinámica o la ruta en sí.

## 6. Trabajar hacia atrás desde el objetivo hasta la estructura de datos

| Requisito básico | Primer candidato | Condiciones a verificar |
|---|---|---|
| Acceso al índice y escaneo secuencial | matriz dinámica | Frecuencia de modificaciones intermedias, capacidad |
| Membresía clave | conjunto/mapa de hash | Si se necesita orden o garantías en el peor de los casos |
| Claves ordenadas y consultas de rango | árbol equilibrado | Relación actualización/consulta |
| Extracción repetida de mínimo | montón | Soporte para eliminación arbitraria/tecla de disminución |
| FIFO | deque | Cola limitada, concurrencia |
| LIFO | pila/matriz dinámica | Profundidad máxima |
| Fusión/consulta de conectividad | conjunto disjunto | Si los bordes nunca se eliminan |
| Recorrido de gráfico disperso | lista de adyacencia | Multibordes, dirección |
| Gráfico denso o prueba de borde rápido | matriz de adyacencia/conjunto de bits | Si la memoria \(V^2\) es aceptable |

Un servicio puede separar su fuente de verdad de los índices de servicio. Por ejemplo, los registros se pueden almacenar en una matriz mientras se mantiene un índice hash para la búsqueda ID y un montón para la prioridad. En ese caso, **la invariante de sincronización entre representaciones** se convierte en un nuevo costo.

## 7. La representación gráfica determina el algoritmo

### Lista de adyacencia

La memoria es \(\Theta(V+E)\) y la iteración sobre los vecinos de un vértice es proporcional a su grado. Este es el valor predeterminado para gráficos dispersos.

### Matriz de adyacencia

La memoria es \(\Theta(V^2)\), pero para probar si existe una ventaja se necesita \(\Theta(1)\). Puede adaptarse a gráficos densos, gráficos pequeños y operaciones de bits paralelos.

### Lista de bordes

Esto es sencillo para los algoritmos que escanean u ordenan cada borde una vez. Buscar los vecinos de un vértice arbitrario es lento sin un índice separado.

Al elegir una representación, decida también si el gráfico es dirigido o no, ponderado o no ponderado, si permite bucles propios y aristas paralelas, si es mutable y qué tan densos son los ID de los vértices.

## 8. Condiciones previas para BFS, DFS y Dijkstra

### BFS

BFS encuentra la distancia más corta en número de aristas desde una fuente en un gráfico no ponderado o en un gráfico cuyos costos de aristas son todos iguales.

~~~python
from collections import deque

def bfs(graph, source):
    distance = {source: 0}
    parent = {source: None}
    queue = deque([source])

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v in distance:
                continue
            distance[v] = distance[u] + 1
            parent[v] = u
            queue.append(v)

    return distance, parent
~~~

Marque un vértice como visitado cuando esté **puesto en cola**, no cuando se elimine de la cola, para evitar que el mismo vértice se ponga en cola repetidamente.

Este ejemplo supone que cada vértice receptor que aparece como vecino también es una clave en `graph`. Un API real debería validar esta representación invariante o manejar explícitamente una adyacencia vacía con algo como `graph.get(u, ())`.

### DFS

DFS es un componente básico para la accesibilidad, los componentes conectados, la detección de ciclos y la clasificación topológica. Pero “usar DFS” por sí solo no determina los ciclos.

- Gráfico no dirigido: un vecino visitado distinto del borde principal señala un ciclo
- Gráfico dirigido: se necesita un borde posterior en la pila de recursividad actual o en el estado del color.
- Orden topológico: válido sólo para un gráfico acíclico dirigido

El orden transversal en un árbol DFS puede variar con el orden de iteración de adyacencia. Corrige el orden de los vecinos cuando se requiere una salida determinista.

### Dijkstra

Dijkstra encuentra las rutas más cortas de una sola fuente cuando **el peso de cada borde no es negativo**.

~~~python
from heapq import heappop, heappush
from math import inf, isfinite

def dijkstra(graph, source):
    distance = {v: inf for v in graph}
    distance[source] = 0.0
    heap = [(0.0, source)]

    while heap:
        best, u = heappop(heap)
        if best != distance[u]:
            continue

        for v, weight in graph[u]:
            if not isfinite(weight) or weight < 0:
                raise ValueError("Dijkstra requires finite nonnegative weights")
            candidate = best + weight
            if candidate < distance[v]:
                distance[v] = candidate
                heappush(heap, (candidate, v))

    return distance
~~~

Debido a que las entradas obsoletas para el mismo vértice pueden permanecer en la cola de prioridad, se requiere una verificación de entradas obsoletas. Una implementación que utiliza un montón con soporte directo de clave de disminución es diferente.

Con una lista de adyacencia y un montón binario, la complejidad temporal habitual es \(O((V+E)\log V)\), comúnmente escrita como \(O(E\log V)\) para un gráfico conectado. Para la implementación anterior, que permite entradas duplicadas, considere también la memoria dinámica y los costos constantes.

### Selección por estructura de peso

| Peso del borde | Candidato a algoritmo |
|---|---|
| Todos iguales | BFS |
| 0 o 1 | 0–1 BFS |
| Todo no negativo | Dijkstra |
| Posibles bordes negativos | Familia Bellman-Ford |
| DAG | Relajación de orden topológico |
| Todos los pares, gráfico denso/pequeño | Considere a Floyd-Warshall y otros |

Cuando se puede alcanzar un ciclo negativo, es posible que el camino finito más corto en sí mismo no esté definido. Esta es una cuestión de definición del problema, no una falla del algoritmo.

## 9. Recursión e iteración

La recursividad expresa definiciones de árbol y de divide y vencerás cercanas a la estructura del código. También tiene estos costos.

- Límites de profundidad de la pila de llamadas
- Asignación de tramas y sobrecarga de llamadas a funciones.
- La pila se desborda en árboles profundos o torcidos.
- Estado implícito y recuperación de errores.

La iteración gestiona el estado transversal directamente con una pila o cola explícita.

~~~python
def iterative_dfs(graph, source):
    visited = set()
    stack = [source]

    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        for v in reversed(graph[u]):
            if v not in visited:
                stack.append(v)

    return visited
~~~

Este ejemplo supone que la adyacencia es una secuencia determinista admitida por `reversed`. Para coincidir con el orden de visita del recursivo DFS, el comportamiento LIFO de la pila puede requerir que los vecinos sean empujados en orden inverso. Incluso cuando el orden de visita sea irrelevante para la corrección, verifique que las pruebas no dependan accidentalmente de él.

Los criterios de selección incluyen:

- Profundidad pequeña y claramente delimitada: la recursividad puede ser más fácil de leer
- Entrada adversaria o profundidad \(O(n)\): preferir iteración
- Pausar, reanudar o serializar el recorrido: el estado explícito es ventajoso
- Procesamiento posterior al pedido: almacenar el estado de entrada/salida en el marco de la pila

Verifique si el lenguaje y el tiempo de ejecución garantizan la optimización de las llamadas finales.

## 10. Conecte pruebas al código con invariantes de corrección

Para demostrar que un algoritmo es correcto para cada entrada válida en lugar de simplemente "trabajar para el ejemplo", utilice un invariante de bucle.

### Tres pasos

1. **Inicialización**: el invariante es verdadero antes de que comience el ciclo.
2. **Mantenimiento**: permanece verdadero después de una iteración.
3. **Terminación**: cuando finaliza el ciclo, el invariante produce la conclusión deseada.

### Ejemplo de invariante de búsqueda binaria

Cuando se utiliza el intervalo medio abierto \([lo,hi)\):

- Si existe una respuesta, siempre está dentro de \([lo,hi)\).
- \([0,lo)\) no cumple la condición.
- \([hi,n)\) cumple la condición.

Mantenga la misma convención de límites a través de actualizaciones y retornos para evitar errores uno por uno.

### BFS invariante

Las distancias de los vértices procesados desde la cola no disminuyen y el primer camino descubierto tiene el número mínimo de aristas. Esto depende de la condición previa de que el costo de cada borde sea igual.

### Invariante de Dijkstra

La distancia de un vértice finalizado con el mínimo válido del montón es la distancia más corta. Se requieren aristas no negativas para demostrar que un camino no visitado no puede luego reducir ese valor.

### Montón invariante

Cada clave de nodo en un montón mínimo no es mayor que las claves de sus hijos. No se requiere clasificación total. Pruebe si la reparación local después de push o pop restaura este invariante.

## 11. Los casos extremos son entradas de diseño, no excepciones posteriores

### Colecciones

- Vacío
- Un elemento
- Todos iguales
- Ya ordenados / ordenados al revés
- Muchos duplicados
- Inmediatamente antes y después de un límite de capacidad
- Clave faltante y eliminación repetida

### Numérico

- Cero y cero negativo
- Valores mínimos y máximos representables.
- Desbordamiento de enteros
- Si se permiten NaN e infinito
- Igualdad y tolerancia en coma flotante.
- Magnitudes muy diferentes

### Gráfico

- Vértice aislado
- Componente desconectado
- Auto-bucle
- Borde paralelo
- Confusión entre dirigido y no dirigido
- Ciclo y ciclo negativo alcanzable.
- Fuente ausente en el gráfico.
- Múltiples caminos más cortos

### Recursos

- Entrada que no cabe en la memoria
- Profundidad máxima de recursividad
- Cancelación y tiempo de espera
- Lecturas y escrituras parciales.
- Mutación concurrente

No deje los casos extremos sólo en una lista de prueba. Decida en el contrato API si rechazar, normalizar o respaldar cada uno.

## 12. Elaboración de perfiles: encuentre dónde está el costo en lugar de adivinar

Incluso un algoritmo con buena complejidad puede no ser el verdadero cuello de botella. Siga esta secuencia antes de la optimización.

1. Defina objetivos de rendimiento o latencia de un extremo a otro.
2. Perfil bajo una carga de trabajo similar a la de producción.
3. Separe CPU, asignación, espera I/O y contención de bloqueo.
4. Inspeccionar la frecuencia de las llamadas y el costo por llamada en la ruta activa.
5. Mida nuevamente en las mismas condiciones después de cambiar el algoritmo o la representación.

La eliminación de un bucle \(O(n^2)\), una serialización innecesaria, consultas repetidas de DB o un patrón de asignación a menudo tienen un efecto mucho mayor que la microoptimización.

## 13. Condiciones para confiar en un punto de referencia

### Carga de trabajo

- Mida en múltiples puntos en todo el rango de tamaño real
- Incluir distribuciones ordenadas, con muchos duplicados, sesgadas y contradictorias, no solo entradas aleatorias
- Refleja las proporciones de lectura/escritura y de aciertos de caché
- Distinguir cachés cálidos y fríos.

### Medición

- Control de calentamiento y efectos JIT/GC
- Configuración separada de la región cronometrada
- Mida los percentiles de la mediana y la cola en múltiples repeticiones.
- Grabar escala de frecuencia CPU y carga en segundo plano
- Consumir resultados para evitar la eliminación de códigos muertos
- Mida también la memoria máxima y las asignaciones

### Interpretación

Un gráfico log-log o un recuento de operaciones por tamaño de entrada puede revelar el cruce. Un algoritmo simple puede ser más rápido para \(n\) pequeño, mientras que uno asintóticamente mejor lo supera para \(n\) grande.

Un punto de referencia no demuestra una verdad universal. Es evidencia sobre el hardware medido, el tiempo de ejecución y la distribución de entrada.

## 14. Flujo de trabajo de selección práctico

1. **Operaciones de lista**: estime las frecuencias de búsqueda, inserción, eliminación, mínimo, rango y recorrido.
2. **Defina el contrato**: decida el orden, los duplicados, la mutabilidad, la simultaneidad y los límites de latencia.
3. **Defina tamaños y distribuciones**: registre \(n,V,E,Q\), escasez, asimetría y la posibilidad de entradas adversas.
4. **Compare estructuras candidatas**: tabule el tiempo y la memoria promedio, en el peor de los casos y amortizado.
5. **Invariantes de corrección de escritura**: registran las condiciones que la estructura y el algoritmo deben mantener.
6. Cree **la implementación correcta más simple**.
7. Verificar invariantes con **pruebas de bordes y propiedades**.
8. Utilice **perfiles** para encontrar el verdadero cuello de botella.
9. Compare alternativas con un **punto de referencia representativo**.
10. **Registre el fundamento**: conservar los supuestos de carga de trabajo y los umbrales de reevaluación.

## 15. Lista de verificación de verificación

- [] ¿Están definidas las variables de tamaño en las expresiones de complejidad?
- [ ] ¿Se distingue lo peor, lo esperado, lo promedio y lo amortizado?
- [] ¿Se evalúan la memoria, la asignación y la localidad además del tiempo?
- [ ] ¿El coste de inserción de una lista enlazada incluye la localización del puesto?
- [] ¿Se han verificado el orden de hash, la colisión y las condiciones de clave mutable?
- [] ¿Se entiende un montón como algo más que una estructura completamente ordenada?
- [] ¿La representación del gráfico se ajusta a las necesidades de escasez y consulta?
- [ ] ¿Se han verificado las condiciones previas de dirección y peso del borde de BFS, DFS y Dijkstra?
- [] ¿La profundidad de recursividad no está limitada por la entrada?
- [] ¿Se puede explicar la inicialización, el mantenimiento y la terminación del invariante del bucle?
- [] ¿Se prueban los casos vacíos, duplicados, desbordados y desconectados?
- [] ¿Se confirmó el cuello de botella mediante la elaboración de perfiles antes de la optimización?
- [ ] ¿Se registran la carga de trabajo y el entorno de referencia?
- [] ¿Se inspeccionaron la latencia de cola y la memoria máxima, además de los promedios?

## 16. Errores y limitaciones comunes

### Una estructura con Big-O más pequeño siempre es más rápida

Las constantes, la localidad de la caché, la asignación y el rango real de \(n\) determinan el cruce. Se necesitan tanto análisis asintóticos como puntos de referencia.

### Inferir complejidad solo a partir del nombre de una biblioteca

Los contenedores con el mismo nombre pueden tener diferentes implementaciones en distintos idiomas. Consulta garantías de funcionamiento y normas de invalidación en documentación oficial.

### Asumir que la entrada ordenada es una entrada fácil

Dependiendo del algoritmo, la entrada ordenada o inversa puede ser el peor de los casos. Inspeccione las suposiciones detrás de los pivotes, los hashes y el equilibrio de árboles.

### Dar a Dijkstra ventajas negativas y comprobar sólo el resultado

Puede que funcione en un ejemplo pequeño, pero se incumple la condición previa de su prueba de corrección. Coloque la validación de entrada en el límite del algoritmo.

### Suponiendo que la conversión de recursividad a un bucle siempre conserva el orden

El árbol transversal cambia con el orden en que los vecinos se insertan en la pila explícita y el momento en que se marcan como visitados.

### Corregir permanentemente una elección basada en un punto de referencia

Cuando cambian el tamaño de los datos, la proporción de lectura/escritura o la versión del tiempo de ejecución, la lógica también puede cambiar. Registrar criterios para la reevaluación.

## Conclusión

El modelo mental práctico para estructuras de datos y algoritmos se puede condensar en esta afirmación.

> Primero anotar las operaciones requeridas y garantías, elegir la estructura más simple que las mantenga, comprobar la escalabilidad con análisis asintótico y medirla bajo la carga de trabajo real.

Big-O es un mapa para filtrar candidatos, una invariante es un contrato que preserva la corrección y la elaboración de perfiles y la evaluación comparativa son el panel para verificar los costos reales. Con los tres, elegir una estructura de datos se convierte en una decisión de ingeniería en lugar de un ejercicio de memorización.
