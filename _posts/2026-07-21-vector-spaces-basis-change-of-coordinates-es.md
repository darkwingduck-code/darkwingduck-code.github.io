---
title: "De los espacios vectoriales al cambio de base: comprensión de la estructura del álgebra lineal"
date: 2026-07-21 09:00:00 +0900
categories: [Mathematics, Linear Algebra]
tags: [vector-space, subspace, span, linear-independence, basis, dimension, change-of-basis]
description: "Conecte subespacios, tramos, independencia lineal, bases, dimensiones y transformaciones de coordenadas a través de definiciones, ejemplos resueltos y procedimientos prácticos de validación."
math: true
lang: es
translation_key: vector-spaces-basis-change-of-coordinates
hidden: true
---

{% include language-switcher.html %}

Gran parte de la confusión en el álgebra lineal comienza no con los métodos de cálculo sino con **mezcla de conceptos en diferentes niveles**. Un espacio vectorial es el entorno en el que las operaciones son válidas, mientras que un subespacio es un entorno más pequeño cerrado bajo esas operaciones. Un tramo es el rango que se puede formar a partir de vectores dados, la independencia lineal significa que no hay redundancia en una representación y una base es un sistema de coordenadas que satisface ambas propiedades.

El objetivo de este artículo no es memorizar términos por separado, sino responder las siguientes preguntas de forma coherente.

- ¿Un conjunto dado es realmente un subespacio?
- ¿Qué espacio abarca un conjunto de vectores?
- ¿Cómo eliminamos la redundancia de un conjunto de expansión?
- ¿Cuándo puede un vector formar una base?
- Cuando cambia la base, ¿cómo cambian el vector mismo y sus coordenadas?

## 1. Espacios vectoriales: Conjuntos en los que las combinaciones lineales permanecen contenidas de forma segura

Un espacio vectorial \(V\) sobre un campo \(\mathbb F\) es un conjunto equipado con suma vectorial y multiplicación escalar. En la práctica, los escalares suelen extraerse de \(\mathbb R\) o \(\mathbb C\). No comprobamos cada axioma, como la asociatividad, la conmutatividad y la distributividad, cada vez, pero su esencia se puede condensar en la siguiente afirmación.

> Para \(u,v\in V\) y \(a,b\in\mathbb F\), cada combinación lineal \(au+bv\) también debe pertenecer a \(V\).

Los vectores no se limitan a secuencias de números. Los polinomios, matrices, funciones y señales también son vectores cuando su suma y multiplicación escalar satisfacen los axiomas. Por tanto, la esencia del álgebra lineal no es la geometría de las flechas sino una **estructura que preserva las combinaciones lineales**.

## 2. Subespacios: una prueba de una línea más fuerte que tres condiciones separadas

Para que \(W\subseteq V\) sea un subespacio, debe cumplir las siguientes condiciones.

1. El vector cero pertenece a \(W\).
2. Está cerrado bajo suma.
3. Está cerrado bajo multiplicación escalar.

Combinarlos en una sola prueba da lo siguiente.

$$
u,v\in W,\quad a,b\in\mathbb F
\quad\Longrightarrow\quad
au+bv\in W.
$$

Verifique también \(W\neq\varnothing\) para que el conjunto vacío no pase incorrectamente.

### Las restricciones homogéneas crean subespacios; Las restricciones no homogéneas generalmente no

Para una matriz \(A\),

$$
W=\{x\mid Ax=0\}
$$

es siempre un subespacio. Si \(Au=0\) y \(Av=0\), entonces

$$
A(au+bv)=aAu+bAv=0
$$

debido a la linealidad. Por eso un espacio nulo es un subespacio.

En contraste,

$$
S=\{x\mid Ax=c\},\qquad c\neq 0
$$

generalmente no contiene el vector cero y, por tanto, no es un subespacio. Si existen soluciones, \(S\) es un **conjunto afín** obtenido al traducir el espacio nulo. Una línea o plano que no pasa por el origen es un ejemplo representativo.

## 3. Span: Todo lo que se puede fabricar con los materiales proporcionados.

El lapso de vectores \(v_1,\dots,v_k\) es el conjunto de todas sus combinaciones lineales.

$$
\operatorname{span}(v_1,\dots,v_k)
=
\left\{
\sum_{i=1}^{k}a_i v_i
\;\middle|\;
a_i\in\mathbb F
\right\}.
$$

El intervalo es el **subespacio más pequeño** que contiene cada uno de \(v_1,\dots,v_k\). Agregar más vectores de expansión no necesariamente aumenta la dimensión. Si ya hay un nuevo vector en el intervalo existente, sólo la representación se vuelve redundante; el espacio permanece sin cambios.

Construyendo la matriz

$$
A=[v_1\;v_2\;\cdots\;v_k]
$$

convierte \(\operatorname{span}(v_1,\dots,v_k)\) en el espacio de columna de \(A\). Si un vector \(y\) pertenece a este intervalo se puede determinar en función de si \(Ac=y\) tiene una solución.

## 4. Independencia lineal: Unicidad de la representación del vector cero.

El conjunto de vectores \(\{v_1,\dots,v_k\}\) es linealmente independiente cuando

$$
a_1v_1+\cdots+a_kv_k=0
$$

solo tiene la solución \(a_1=\cdots=a_k=0\). Si coeficientes distintos de cero pueden producir el vector cero, el conjunto es linealmente dependiente.

Desde la perspectiva matricial, todas las siguientes afirmaciones son equivalentes.

- \(v_1,\dots,v_k\) son linealmente independientes.
- La única solución de \(Ac=0\) es \(c=0\).
- El número de columnas dinámicas en \(A\) es \(k\).
- \(\operatorname{rank}(A)=k\).
- La nulidad es 0.

### Una afirmación frecuentemente incorrecta: "Un vector de base sólo necesita ser distinto de cero"

Para un único vector \(v\), si \(v\neq0\), entonces \(\{v\}\) es una base del subespacio unidimensional \(\operatorname{span}(v)\) que crea. Sin embargo, no es la base de un subespacio arbitrario mayor. Para ser una base, los vectores no solo deben ser **linealmente independientes** sino también **abarcar** todo el espacio objetivo.

## 5. Base y dimensión: un conjunto abarcador mínimo y un conjunto independiente máximo

Una base \(B=(b_1,\dots,b_n)\) de un subespacio \(W\) satisface las dos condiciones siguientes.

1. \(\operatorname{span}(b_1,\dots,b_n)=W\)
2. \(b_1,\dots,b_n\) son linealmente independientes.

Esto permite entender una base de dos maneras.

- Un **conjunto de expansión mínima** que ya no abarca todo el espacio si se elimina algún vector
- Un **conjunto independiente máximo** que se vuelve dependiente si se agrega un vector más

Cada base de un espacio de dimensión finita tiene el mismo número de vectores. Ese número es la dimensión \(\dim W\). Para una matriz \(A\in\mathbb F^{m\times n}\),

$$
\operatorname{rank}(A)+\operatorname{nullity}(A)=n
$$

sostiene. Esto significa que los \(n\) grados de libertad de entrada se descomponen en direcciones de espacio de columna observables y direcciones de espacio nulo que \(A\) borra.

## 6. Ejemplo resuelto: encontrar la base de un avión de dos maneras

Considere el siguiente plano homogéneo.

$$
W=\{(x,y,z)^\mathsf T\in\mathbb R^3\mid x+y+z=0\}.
$$

Debido a que la restricción da \(x=-y-z\),

$$
\begin{bmatrix}x\\y\\z\end{bmatrix}
=
y\begin{bmatrix}-1\\1\\0\end{bmatrix}
+
z\begin{bmatrix}-1\\0\\1\end{bmatrix}.
$$

Por lo tanto, una base candidata es

$$
B=
\left(
\begin{bmatrix}-1\\1\\0\end{bmatrix},
\begin{bmatrix}-1\\0\\1\end{bmatrix}
\right)
$$

Los dos vectores no son múltiplos escalares entre sí, por lo que son independientes y abarcan todas las soluciones. Por lo tanto \(\dim W=2\).

Podemos llegar a la misma conclusión mediante la nulidad de rango. La matriz de restricciones \(A=[1\;1\;1]\) tiene rango 1, por lo que su nulidad es \(3-1=2\). Comprobar que diferentes enfoques dan la misma dimensión es una técnica de verificación útil.

## 7. Distinguir las coordenadas del propio vector.

Si las coordenadas de un vector \(v\) en la base \(B=(b_1,\dots,b_n)\) se escriben como

$$
[v]_B=
\begin{bmatrix}c_1\\\vdots\\c_n\end{bmatrix}
$$

entonces

$$
v=c_1b_1+\cdots+c_nb_n
$$

Aquí, \(v\) es un objeto abstracto, mientras que \([v]_B\) es una representación numérica que depende de la base elegida.

A continuación, supongamos que dos bases de un espacio \(n\)-dimensional se expresan en un único sistema de coordenadas de referencia fijo \(n\)-dimensional, por lo que sus matrices de base son cuadradas e invertibles. Si la matriz cuyas columnas son los vectores base también se denota por \(B\), entonces

$$
v=B[v]_B,\qquad [v]_B=B^{-1}v
$$

sostiene. Si \(B\) y \(C\) son dos bases del mismo espacio, entonces

$$
[v]_C=C^{-1}B[v]_B.
$$

Por lo tanto, la matriz que convierte las coordenadas \(B\) en \(C\) es

$$
P_{C\leftarrow B}=C^{-1}B
$$

Leer la flecha del subíndice como “desde la base de entrada hasta la base de salida” ayuda a evitar errores en el orden de multiplicación.

Cuando una base de subespacio se escribe directamente en las coordenadas de un espacio ambiental más grande, la matriz de base puede ser rectangular y \(B^{-1}\) no existe. En este caso, resuelva \(B[v]_B=v\) con QR o un método similar, o primero elija una base de referencia fija dentro del subespacio y exprésela como una matriz de coordenadas cuadradas.

### La matriz de una transformación lineal también depende de la base.

Si \(A\) es la matriz de base estándar de una transformación lineal \(T:V\to V\) y \(B\) es la nueva matriz de base, entonces

$$
[T]_B=B^{-1}AB.
$$

La secuencia envía un vector desde las nuevas coordenadas a las coordenadas estándar, aplica \(A\) y lo devuelve a las nuevas coordenadas. Debido a que \(A\) y \(B^{-1}AB\) expresan la misma transformación lineal en diferentes sistemas de coordenadas, comparten invariantes de similitud como traza, determinante y valores propios.

## 8. Flujo de trabajo práctico para la resolución de problemas

### Cuando se da un conjunto

1. Especifique el espacio ambiental y el campo escalar.
2. Comprueba primero si contiene el vector cero.
3. Para \(u,v\) y escalares \(a,b\) arbitrarios, verifique que \(au+bv\) conserve la condición de definición.
4. Si hay un término constante no homogéneo, una desigualdad o una condición de norma fija, investigue primero la probabilidad de que no sea un subespacio.

### Cuando se dan vectores de expansión

1. Construya una matriz con los vectores como columnas.
2. Encuentre las columnas dinámicas mediante reducción de filas.
3. Seleccione las columnas dinámicas de la **matriz original** como base del espacio de columnas.
4. Compare el rango con el número de vectores base.

Las columnas de una matriz de filas reducidas pueden tener un espacio de columna diferente al original. Las operaciones de fila preservan el espacio de la fila, pero generalmente no preservan el espacio de la columna en sí.

### Cuando se da una transformación de coordenadas

1. Especifique el sistema de coordenadas en el que está escrito cada vector base.
2. Haga coincidir el orden de las columnas de la matriz base con el orden de los componentes de coordenadas.
3. Calcule \(P_{C\leftarrow B}=C^{-1}B\).
4. Verifique que \(CP_{C\leftarrow B}=B\).
5. Para un vector de prueba arbitrario, verifique que \(B[v]_B=C[v]_C\).

## 9. Lista de verificación de validación

- [] ¿Llamaste subespacio a un conjunto que no contiene el vector cero?
- [ ] ¿Distinguiste un tramo del propio conjunto?
- [ ] ¿Marcó “spans” y “es independiente” por separado?
- [] ¿El número de vectores base es igual a la dimensión conocida?
- [ ] ¿La suma del rango y la nulidad es igual al número de columnas?
- [] ¿Seleccionó columnas dinámicas de la matriz original?
- [] ¿Etiquetó la dirección base de entrada y salida de la transformación de coordenadas?
- [] ¿El vector real se reconstruye sin cambios después de la transformación?
- [] ¿Registraste la tolerancia de detección de rango para cálculos numéricos?

## 10. Escollos y limitaciones

### Intentando decidir todo con un determinante

El determinante se define sólo para matrices cuadradas. Para preguntas de independencia, extensión y rango que involucran matrices rectangulares, la reducción de filas, QR y SVD son más generales.

### El rango numérico no es un número entero exacto

Con datos de punto flotante, usted decide si un valor singular es “suficientemente pequeño” en lugar de si es exactamente cero. Dado que cambiar el umbral puede cambiar la clasificación estimada, informe la escala y la tolerancia juntas.

### Suponiendo que una base es única

La dimensión es fija, pero hay infinitas bases. Una buena base depende del propósito. Una base ortonormal estabiliza los cálculos, una base propia simplifica las operaciones y una base dispersa puede facilitar la interpretación y el almacenamiento.

### Extender demasiado la intuición de dimensión finita

En espacios de dimensión infinita, como los espacios funcionales, una base algebraica se distingue de una base analítica que implica convergencia. Una vez que aparecen sumas, normas y completitud infinitas, la intuición de matriz finita por sí sola es insuficiente.

## Conclusión

El flujo esencial es simple.

$$
\text{Subspace}
\longrightarrow
\text{span}
\longrightarrow
\text{linear independence}
\longrightarrow
\text{basis}
\longrightarrow
\text{dimension and coordinates}
$$

Una base no es simplemente una "lista de vectores de dirección". Es una **interfaz que representa cada elemento de un espacio sin redundancia**. Una vez que adopte este punto de vista, la proyección, los mínimos cuadrados, SVD y la reducción de dimensionalidad se conectan a través del mismo lenguaje.
