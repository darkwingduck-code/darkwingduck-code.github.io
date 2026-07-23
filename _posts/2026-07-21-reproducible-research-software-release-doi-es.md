---
title: "Lanzamiento de software de investigación reproducible: lanzamientos, CITATION.cff y DOI de Zenodo"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "Un procedimiento para convertir un repositorio de código de investigación en una versión reproducible y conectar CITATION.cff, un archivo de preservación y un software DOI manteniendo separados los identificadores de papel y preimpresión."
lang: es
hidden: true
translation_key: reproducible-research-software-release-doi
---

{% include language-switcher.html %}

El mero hecho de que el código de investigación esté en un repositorio público no lo hace reproducible o citable. La rama predeterminada sigue cambiando, las dependencias desaparecen y los lectores tienen dificultades para saber qué confirmación produjo los resultados.

Para publicar correctamente un software de investigación, hay que distinguir cuatro objetos.

1. El **repositorio de código fuente**, donde continúa el desarrollo
2. Una **versión y etiqueta versionadas** que congelan un estado significativo
3. Un **registro de software de archivo y DOI** para preservación y citación a largo plazo.
4. Un **artículo o preimpresión** que explique la pregunta de investigación, los métodos y los resultados.

Este artículo presenta un procedimiento práctico para vincular estos cuatro objetos de forma rastreable sin combinarlos.

## 1. Primero separa lo que identifica cada identificador

| Objeto | Rol principal | Mutabilidad | Identificador típico |
|---|---|---|---|
| repositorio | colaboración y desarrollo continuo | sucursales siguen cambiando | repositorio URL |
| comprometerse | instantánea de origen | contenido abordado y arreglado efectivamente | confirmar hash |
| etiqueta | etiqueta de versión legible por humanos | debería ser inmutable por política | nombre de etiqueta + compromiso de destino |
| lanzamiento | notas de distribución y paquete de artefactos | las notas de la versión pueden ser editables | versión + lanzamiento URL |
| archivo de software | objeto de investigación preservado a largo plazo | archivos en un registro de versión son fijos | software DOI |
| preimpresión/artículo | afirmaciones y exposición de la investigación | la política de versiones varía según la plataforma | publicación DOI o identificador |
| conjunto de datos | objeto de datos de entrada o salida | debería arreglarse por versión | conjunto de datos DOI |

Un hash de confirmación apunta a la fuente exacta pero no proporciona metadatos académicos ni una política de preservación a largo plazo. Un DOI proporciona enlaces de metadatos e identificación persistentes, pero no restaura automáticamente el entorno de ejecución. Utilice ambos juntos.

## 2. Indique el nivel de reproducibilidad

No diga simplemente “reproducible”; definir el alcance admitido.

- **Reproducibilidad de la fuente**: se puede obtener el mismo árbol fuente.
- **Reproducibilidad de compilación**: el mismo ejecutable o paquete se puede compilar en el entorno especificado.
- **Reproducibilidad computacional**: se puede obtener la misma salida a partir de las entradas dentro de una tolerancia permitida.
- **Reproducibilidad de resultados**: las figuras, tablas y métricas del artículo se pueden regenerar.
- **Auditabilidad**: el código, la configuración y la procedencia de los datos se pueden rastrear hacia atrás a partir de un resultado.

Garantizar una salida bit a bit idéntica en todas las plataformas puede resultar difícil. En ese caso, especifique el OS y la arquitectura, la tolerancia numérica y los componentes no deterministas admitidos.

## 3. Una liberación es un contrato que especifica qué compromiso citar

### La diferencia entre etiqueta, versión y archivo

- Una etiqueta Git es un nombre adjunto a una confirmación específica.
- Una versión de servicio de hosting es un objeto de distribución que conecta notas de versión y artefactos binarios a una etiqueta.
- Un archivo es un registro de investigación independiente que preserva las fuentes y los metadatos a largo plazo.

Las versiones de los tres objetos deben coincidir.

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Política de versiones

Puede utilizar el control de versiones semántico, pero primero defina qué constituye el “público API” del software de investigación.

- opciones de línea de comandos y formatos de archivo
-Python/C++ API
- esquema de configuración
- semántica del método numérico o valores predeterminados
- esquema de salida y unidades
- pesos entrenados o paquetes de parámetros

Si cambiar un método numérico o un valor predeterminado altera la interpretación científica de la misma entrada, considere cuidadosamente si debe tratarse como un simple parche. El contrato de compatibilidad tiene prioridad sobre el número de versión.

### No mover etiquetas

La actualización forzada de una etiqueta publicada a una confirmación diferente hace que el mismo nombre de versión haga referencia a una fuente diferente. Si es necesaria una corrección, cree una nueva versión del parche y documente el problema conocido en la versión anterior.

## 4. El paquete de reproducibilidad que se incluirá en una versión

Como mínimo, una versión necesita lo siguiente.

### Comprensión y ejecución

- README: propósito, alcance e inicio rápido
- LICENSE: términos para usar la fuente y los activos empaquetados
- entorno/archivo de bloqueo
- ejemplos de configuración y esquema
- diccionario de datos de entrada/salida
- ejemplo mínimo de un extremo a otro
- limitaciones conocidas

### Evidencias de calidad

- resultados de pruebas automatizados
- verificación analítica o de referencia
- tolerancia numérica
- contrato determinista/no determinista
- matriz de plataforma compatible
- registro de cambios y notas de migración

### Procedencia

- revisión de fuente
- fecha de lanzamiento y versión
- resumen de bloqueo de dependencia
- resumen de la imagen del contenedor, grabado con la etiqueta si existe
- versión de datos de entrada o suma de comprobación
- comandos para generar figuras y tablas

No incluya indiscriminadamente grandes resultados generados y secretos en un archivo fuente. Proporcione recetas y sumas de verificación para resultados reproducibles y vincule los datos necesarios como un objeto de archivo separado después de verificar su licencia y restricciones de privacidad.

## 5. El papel de CITATION.cff

`CITATION.cff` es un archivo de metadatos de citas basado en YAML- que las personas pueden leer y las herramientas pueden interpretar. Colocarlo en la raíz del repositorio permite que las IU de alojamiento compatibles muestren información de citas. La guía oficial CFF y la documentación GitHub actuales utilizan el formato `cff-version: 1.2.0` en sus ejemplos.

La siguiente plantilla genérica ilustra su estructura.

~~~yaml
cff-version: 1.2.0
message: "If you use this software, please cite this version."
title: "Example Scientific Software"
type: software
version: 1.0.0
date-released: 2026-07-21
license: MIT
repository-code: "https://example.org/example-software"
authors:
  - family-names: "Replace-With-Family-Name"
    given-names: "Replace-With-Given-Name"
~~~

Reemplace los marcadores de posición con metadatos públicos reales y valide el archivo con un validador CFF. No se requiere un correo electrónico personal para una citación; omitirlo a menos que haya una razón para publicarlo.

### Campos que deben coincidir como mínimo

- título del software
- creadores y su orden
- versión
- fecha de lanzamiento
- repositorio URL
- licencia
- software específico de la versión DOI

No determine el orden de los contribuyentes automáticamente a partir del recuento de confirmaciones. Establezca de antemano políticas de elegibilidad de autoría y rol de colaborador, y proporcione metadatos de colaborador por separado si es necesario.

### Cómo conectar el software en sí y un documento

Puede presentar un artículo relacionado a través de `preferred-citation`, pero esto puede causar que la cita del repositorio UI dé prioridad a la cita del artículo en lugar del software. Cuando el crédito por el software en sí y la reproducibilidad de la versión exacta son importantes, es más claro mantener la cita raíz como registro del software y vincular el artículo a través de referencias o identificadores relacionados.

## 6. Comprenda el archivo antes de asignar un DOI

Un DOI no es un número decorativo en el código fuente sino un identificador persistente para un objeto de investigación específico. Según la guía actual de Zenodo, la publicación de un registro registra un DOI, mientras que una nueva versión con archivos modificados se administra como un registro separado y un identificador persistente.

### Versión DOI y Concepto DOI

El control de versiones de Zenodo DOI proporciona dos categorías de DOI en la primera publicación.

- **Versión DOI**: identifica los archivos de una versión específica
- **Concepto DOI**: identifica la colección de todas las versiones y enlaza a la página de inicio de la última versión.

La versión DOI es la predeterminada cuando se cita el código exacto utilizado para la reproducibilidad. El Concepto DOI puede ser apropiado cuando se hace referencia al proyecto de software en evolución en su conjunto.

No cree versiones agregando arbitrariamente un sufijo como `.v2` a una cadena DOI. Los metadatos del archivo conectan las relaciones de versión.

## 7. Un procedimiento seguro para conectar Zenodo y un disparador

El flujo habitual cuando se utiliza la integración de alojamiento Git es el siguiente.

1. Confirme que el repositorio se puede hacer público.
2. Ejecute un análisis secreto, una auditoría del historial y una auditoría de la licencia.
3. Habilite el repositorio en la integración de archivos.
4. Congele la confirmación del candidato de lanzamiento.
5. Ejecute pruebas, la compilación de la documentación y la reproducción de ejemplos.
6. Alinee los metadatos de la versión con `CITATION.cff`.
7. Cree una etiqueta inmutable y suéltela.
8. Revise el título, los creadores, el tipo de recurso, la versión y la licencia del registro de archivo.
9. Después de la publicación, registre la Versión DOI y el Concepto DOI por separado.
10. Agregue las relaciones correctas a la página de lanzamiento, README, CFF y los metadatos en papel.

La guía oficial de GitHub explica que la integración de Zenodo puede emitir un DOI para un archivo de repositorio y que el repositorio integrado debe ser público. Los repositorios de la organización pueden requerir una aprobación por separado para el acceso a la integración.

### Si desea colocar el DOI en archivos antes del lanzamiento

Hay dos enfoques.

- Reserve un DOI en el archivo con anticipación y luego agréguelo a los metadatos de la versión.
- Archive la primera versión, agregue DOI a la rama predeterminada y sincronice completamente los metadatos de la versión desde la próxima versión en adelante.

Eliminar un borrador con un DOI reservado puede hacer que pierdas la reserva, así que consulta la política actual del archivo. Si el mismo objeto ya tiene un DOI, no emita un duplicado DOI; ingrese el DOI existente en los metadatos.

## 8. Un software DOI y una preimpresión DOI nunca identifican el mismo objeto

El software y una preimpresión son resultados de investigación distintos.

| Distinción | Registro de software | Registro de preimpresión |
|---|---|---|
| Contenido | fuente, paquete, ejecutable, documentación | pregunta de investigación, métodos, resultados, interpretación |
| Tipo de recurso | software | preimpresión/publicación |
| Significado de la versión | lanzamiento de código | revisión del manuscrito |
| Destino de cita principal | versión exacta del software que se ejecutó | versión del documento que fue leído y discutido |
| Identificador | software DOI | preimpresión DOI/identificador |

Por lo tanto, evite lo siguiente.

- colocar una preimpresión DOI en el campo del software DOI de `CITATION.cff`
- mezclar un archivo de preimpresión en un archivo de software y contraer ambos en un tipo de recurso
- reutilizar un artículo de revista DOI como DOI para cargar un código complementario
- forzar las versiones de lanzamiento de código y las revisiones de manuscritos en el mismo esquema de numeración

En su lugar, conecte las relaciones en los metadatos del archivo.

- software **IsSupplementTo** papel
- software **IsDocumentedBy** en papel o un registro de documentación independiente
- papel **Referencias** software
- software **Requiere** conjunto de datos de entrada; conjunto de datos **IsRequiredBy** software

Verifique los nombres de los tipos de relaciones reales en el vocabulario de metadatos del archivo y verifique su dirección. Es mejor proporcionar identificadores relacionados legibles por máquina que utilizar únicamente descripciones en prosa.

## 9. Congelar la fuente, el entorno y los datos juntos

Incluso con un software DOI, los resultados no se pueden reproducir sin dependencias e entradas.

### Fuente

- etiqueta exacta y compromiso
- revisiones de submódulos
- versión del generador para la fuente generada
- construir guiones

### Medio ambiente

- archivo de bloqueo de dependencia
- versión compilador/intérprete
- OS y arquitectura
- bibliotecas numéricas y tiempo de ejecución del acelerador
- resumen de contenedor o exportación de entorno

Grabar solo la etiqueta del contenedor `latest` puede apuntar a una imagen diferente con el tiempo. Registre también un resumen inmutable.

### Datos y configuración

- versión del conjunto de datos de entrada/DOI
- suma de comprobación del archivo
- código de preprocesamiento y orden
- archivo de configuración
- semilla aleatoria y manifiesto dividido
- esquema y unidades

Si los datos sin procesar no se pueden publicar, proporcione un ejemplo, esquema, generador y condiciones de acceso sintéticos o mínimos, e indique qué componentes privados limitan la reproducción completa.

## 10. Puertas de liberación automatizadas

Un flujo de trabajo de lanzamiento CI puede verificar al menos lo siguiente.

~~~text
[quality]
unit + integration + numerical tests pass
example workflow reproduces expected metrics
documentation builds without broken internal links

[metadata]
package version == tag version
CITATION.cff parses and validates
release date and changelog entry exist
license and notices are present

[security]
secret scan passes
private paths and hostnames are absent
large or restricted data are not bundled

[archive readiness]
source archive is self-contained
dependency lock exists
input/output schema is documented
~~~

Emitir un DOI es en sí mismo una publicación que cambia el estado externo, por lo que utilizar un ensayo y una revisión humana es más seguro. Un registro de archivo publicado no debe tratarse como una sucursal ordinaria.

## 11. Lanzamiento del runbook

### Preparación

- Clasificar cambios de alcance y compatibilidad.
- Decidir la versión.
- Redactar el registro de cambios y notas de migración.
- Revisar dependencias y licencias obsoletas.
- Revisar los metadatos del autor y del colaborador de la cita.

### Verificación

- Construir en un ambiente limpio.
- Vuelva a ejecutar el ejemplo mínimo desde el principio.
- Consultar los comandos que generan ratios y tablas.
- Comprobar tolerancias numéricas y diferencias de plataforma.
- Extraiga y ejecute el paquete fuente exacto que se va a archivar.

### Publicación

- Fusionar el compromiso de lanzamiento.
- Aplicar una política de etiquetas anotadas/firmadas, si existe.
- Publicar notas de la versión y sumas de comprobación de artefactos.
- Realizar una revisión final de los metadatos de los registros de archivo y luego publicarlos.
- Conecte la versión DOI a la versión y CFF.

### Después de la publicación

- Confirme que DOI se resuelva en la página de destino correcta.
- Verifique la lista de archivos y las sumas de verificación del archivo.
- Confirmar que los DOI de concepto y versión aparecen según lo previsto.
- Actualizar identificadores relacionados en el repositorio, documentación y preimpresión.
- Crear un problema de runbook para la próxima versión.

## 12. Lista de verificación de verificación

- [ ] ¿Se han distinguido los roles de repositorio, confirmación, etiqueta, lanzamiento y archivo?
- [] ¿Coinciden las versiones de etiqueta, paquete, documentación, CFF y archivo?
- [] ¿Existe una política que prohíba el movimiento de etiquetas publicadas?
- [] ¿El ejemplo de un extremo a otro se ejecuta en un entorno limpio?
- [] ¿Se han solucionado las versiones de dependencia y datos de entrada?
- [] ¿Está `CITATION.cff` en la raíz y pasa un validador?
- [] ¿El título del software, el orden de los creadores, la versión y la licencia coinciden con los metadatos del archivo?
- [ ] ¿Se distinguen los usos de la Versión DOI y del Concepto DOI?
- [] ¿Los DOI del software se gestionan por separado de los DOI de preimpresión/artículo?
- [] ¿Los DOI relacionados están conectados a través de relaciones legibles por máquina?
- [] ¿Las fuentes y los archivos están libres de secretos, rutas personales y datos privados?
- [] ¿Se registra un resumen inmutable además de la etiqueta del contenedor?
- [ ] ¿Una persona revisa los metadatos y el paquete de archivos antes de la publicación DOI?

## 13. Errores y limitaciones comunes

### “Está en Git, por lo que se conserva permanentemente”

Un hosting URL y una cuenta no son identificadores de preservación. Un archivo y DOI mejoran la accesibilidad a largo plazo, pero sin una licencia, metadatos y una receta de ejecución, su utilidad es limitada.

### “Tiene un DOI, por lo que es reproducible”

Un DOI identifica un objeto. No proporciona automáticamente dependencias, datos, configuración o tolerancias numéricas.

### Citando solo el último concepto DOI

Un lector puede recibir una versión posterior incompatible. La reproducción de un resultado de investigación específico requiere la versión DOI y la versión de lanzamiento.

### Copiar un DOI manualmente en el README y causar inconsistencias

Genere CFF, metadatos de paquetes, notas de la versión y metadatos de archivo desde una única fuente cuando sea posible, o verifíquelos en CI.

### Suponiendo que eliminar un registro de un repositorio público también elimina sus secretos

Los secretos pueden permanecer en el historial, bifurcaciones, registros CI, artefactos de lanzamiento y archivos. Después de la exposición, no se limite a eliminarlos; revocarlos y rotarlos inmediatamente e inspeccionar cada lugar de conservación.

### Fuente sin contrato de ejecución

Sin documentación de las plataformas compatibles, tolerancias, componentes no deterministas y rango de tiempo de ejecución esperado, es difícil determinar si una falla en la reproducción es un error o una diferencia ambiental.

## 14. Referencias oficiales

- [Guía oficial sobre el formato del archivo de citas](https://citation-file-format.github.io/)
- [GitHub orientación sobre archivos de citas](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [Orientación oficial sobre la conservación de un repositorio GitHub con un DOI](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Ciclo de vida de los registros y versiones de Zenodo](https://help.zenodo.org/docs/deposit/about-records/)
- [Guía de versiones de Zenodo DOI](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Guía de reserva de Zenodo DOI](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [Definiciones de relación de identificador relacionado con DataCite](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## Conclusión

Los enlaces principales para el software de investigación reproducible son los siguientes.

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

Un artículo o preimpresión es un objeto separado que explica y hace afirmaciones sobre estos enlaces. Separe los DOI para software y documentos, luego conéctelos con identificadores relacionados para preservar tanto el crédito como la reproducibilidad.

Una buena publicación no es simplemente "el día en que se publicó el código". Es el estado en el que un tercero ya no tiene que adivinar qué versión obtener, qué entorno utilizar o qué ejecutar.
