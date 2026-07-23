---
title: "Fundamentos de diagnóstico de Linux: procesos de lectura, archivos, señales y systemd como evidencia"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: Un flujo de trabajo práctico para reducir los incidentes de Linux utilizando evidencia de procesos, descriptores, sistemas de archivos, señales, recursos y el diario systemd en lugar de comenzar con un reinicio.
lang: es
translation_key: linux-diagnostics-processes-files-signals-systemd
hidden: true
---
{% include language-switcher.html %}

## El problema: reiniciar borra los síntomas pero no explica la causa

Cuando un servicio de Linux es lento o no responde, reiniciarlo inmediatamente puede restaurarlo temporalmente.

Sin embargo, la evidencia de la memoria, descriptores, sockets, procesos secundarios, sistemas de archivos y dependencias pueden desaparecer con él.

Los siguientes conceptos erróneos retrasan el diagnóstico.

- Bajo CPU significa que el proceso está en buen estado.
- La poca memoria libre debe significar una escasez de memoria.
- Si existe un archivo, debe ser legible.
- `kill` significa terminación forzada.
- Si el estado del servicio es activo, la funcionalidad de cara al usuario también debe estar en buen estado.
- La última línea del registro debe ser la causa.
- Ejecutar como root es una forma aceptable de evitar problemas de permisos.

El diagnóstico operativo debe seguir `observation -> hypothesis -> minimal check -> safe mitigation -> verification`.

## Modelo mental: un proceso es un conjunto de recursos del núcleo

Un proceso no es simplemente un archivo ejecutable.

Tiene lo siguiente.

- PID y padre PID
- Identidad de usuario y grupo.
- Mapa de memoria virtual
- Abrir tabla de descriptores de archivos
- Directorio de trabajo actual
- Medio ambiente
- Disposición de la señal
- Espacio de nombres y membresía de cgroup
- Hilos y estado de programación.

Reemplazar un archivo ejecutable no cambia automáticamente la asignación de memoria de un proceso que ya se está ejecutando.

Un archivo eliminado puede seguir ocupando bloques de disco mientras su descriptor permanece abierto.

### `/proc` es una ventana al kernel en ejecución

`/proc/<pid>/status` muestra una descripción general del estado y la memoria.

`/proc/<pid>/fd` muestra descriptores abiertos.

`/proc/<pid>/maps` muestra asignaciones de memoria.

`/proc/<pid>/limits` muestra límites de recursos.

Los límites de permisos y espacios de nombres se aplican incluso a las lecturas.

### Los descriptores de archivos no apuntan solo a archivos

Los archivos, directorios, sockets, tuberías, dispositivos y objetos de eventos normales pueden ser descriptores.

Una fuga de descriptor puede aparecer no sólo como una falla al abrir archivos, sino también como una falla al establecer nuevas conexiones.

Verifique los límites por proceso y para todo el sistema.

### Una señal es una notificación asincrónica

`SIGTERM` es una señal captable que solicita una terminación elegante.

`SIGKILL` no puede ser manejado ni ignorado por un proceso.

Históricamente, `SIGHUP` significa desconexión del terminal y algunos demonios lo usan para indicar recarga, pero debes verificar el contrato de la aplicación.

La entrega exitosa de la señal y la limpieza exitosa de la aplicación son cosas diferentes.

## Workflow: una orden para acotar incidencias

### Paso 1. Identificar el síntoma visible para el usuario

- ¿Cuándo empezó?
- ¿Afecta a todas las solicitudes o solo a un punto final específico?
- ¿Es un tiempo de espera o un error inmediato?
- ¿Es un anfitrión o toda la flota?
- ¿Hubo cambios recientes de implementación, configuración, certificado o dependencia?

Capture una marca de tiempo UTC y una correlación ID.

### Paso 2. Verifique el estado del administrador de servicios

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)` significa poco más que que el proceso principal está activo.

No garantiza que las solicitudes comerciales tengan éxito.

Inspeccione también las políticas `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile` y de reinicio de la unidad.

### Paso 3. Inspeccionar el árbol y el estado del proceso.

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

Las pistas principales en `STAT` son las siguientes.

- `R`: en ejecución o ejecutable
- `S`: sueño interrumpible
- `D`: sueño ininterrumpido, normalmente esperando I/O
- `T`: detenido o rastreado
- `Z`: zombi

Un zombi es un niño que ya salió pero cuyo padre no ha recopilado su estado de salida.

Un zombi en sí casi no usa memoria, pero un aumento sostenido es un signo de un error parental.

### Paso 4. Separar CPU del comportamiento del programador

El promedio de carga no es lo mismo que la utilización de CPU.

Puede incluir tareas ejecutables y algunas tareas ininterrumpibles.

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

Examine el usuario CPU, el sistema CPU, la espera I/O y los cambios de contexto juntos.

En un contenedor, una cuota de cgroup puede provocar limitaciones.

Incluso si al host le queda CPU capacidad, la carga de trabajo aún puede estar limitada.

### Paso 5. Ver la memoria por componente

Linux utiliza memoria adicional como caché de página.

Mire también la estimación `available` de `free`.

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

Distinga RSS, tamaño virtual, memoria anónima, asignaciones respaldadas por archivos y memoria compartida.

Consulte el diario del kernel y los eventos de cgroup para ver si hay evidencia de una eliminación de OOM.

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Paso 6. Verificar descriptores y sockets

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

Compare la tendencia del recuento de descriptores con su límite.

Vea si los estados de conexión se concentran en `SYN-SENT`, `CLOSE-WAIT` o `TIME-WAIT`.

La acumulación de conexiones `CLOSE-WAIT` puede indicar que la aplicación no cierra los sockets después de que el par se desconecta.

### Paso 7. Separe la capacidad del sistema de archivos de la capacidad de inodo

```bash
df -h
df -i
findmnt
```

Los inodos pueden agotarse incluso cuando queda capacidad de bytes.

Un archivo abierto y eliminado no aparece en las listas de directorios, pero aún consume espacio.

```bash
lsof +L1
```

Verifique también las opciones de montaje, los remontajes de solo lectura y la latencia del sistema de archivos de red.

### Paso 8. Inspeccionar los permisos a lo largo de toda la ruta

El modo de archivo por sí solo no es suficiente.

Se requiere permiso de recorrido en cada directorio principal.

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

Si SELinux o AppArmor están en uso, verifique también si hay denegaciones de políticas MAC.

Ejecutarlo como root puede ocultar la causa y romper los límites de permisos.

### Paso 9. Observe I/O y las llamadas al sistema dentro de un alcance mínimo

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace` puede agregar gastos generales y exponer datos confidenciales.

Úselo brevemente, filtre solo las llamadas al sistema requeridas y siga la política operativa.

Aplique los mismos principios de seguridad a las herramientas `perf` y eBPF.

### Paso 10. Apagar de forma segura

Primero detenga el servicio a través del administrador de servicios.

```bash
systemctl stop example.service
```

Si es necesario, envíe SIGTERM y observe el estado durante el período de gracia.

SIGKILL es el último recurso.

Antes de la terminación forzada, capture la evidencia que necesita, como pilas, registros, descriptores y política de volcado de núcleo.

## Cómo leer una unidad systemd

### La dependencia y el orden son diferentes

`After=` define el pedido inicial, pero no agrega automáticamente un requisito de dependencia.

`Requires=` y `Wants=` expresan relaciones de dependencia.

El hecho de que la red sea `online` no significa que una dependencia de la aplicación esté realmente lista.

### La política de reinicio puede ocultar fallas

`Restart=on-failure` ayuda a recuperarse de fallas transitorias.

Sin embargo, un rápido ciclo de caídas puede ejercer presión sobre las dependencias.

Verifique el límite de tasa de inicio y retroceso.

Alerta sobre recuentos de reinicios repetidos y el motivo de salida más reciente.

### El entorno de ejecución difiere de un shell interactivo

PATH, el directorio de trabajo, el entorno, la máscara única y los límites pueden diferir.

No asuma que un perfil de shell se carga automáticamente.

Especifique las rutas requeridas en el archivo de la unidad.

No exponga secretos en la fuente de la unidad o en la línea de comando.

## Ejemplo práctico: el servicio está activo, pero el API caduca

1. Utilice una solicitud sintética para precisar el punto final y la marca de tiempo.
2. Inspeccione MainPID y reinicie el historial con `systemctl show`.
3. Busque en el diario tiempos de espera y errores de dependencia al mismo tiempo.
4. Inspeccione los estados de las conexiones salientes con `ss`.
5. Compare el recuento `/proc/<pid>/fd` con su límite.
6. Inspeccione por subproceso CPU y los estados bloqueados.
7. Envíe una solicitud de diagnóstico limitada al punto final descendente.
8. Pruebe la hipótesis de que el grupo de subprocesos o el grupo de conexiones están agotados.
9. Decida si reiniciar después de agotar el tráfico.
10. Después de la recuperación, verifique el usuario SLI y las métricas de recursos.

Si reiniciaste, no lo registres como si resolvieras la causa raíz.

Registre `symptoms mitigated by restart; cause unconfirmed` por separado.

## Lista de verificación de verificación

### Preservación de pruebas

- [] Se registró la marca de tiempo del síntoma y el alcance del impacto.
- [] Se comprobaron los cambios recientes y la versión del artefacto.
- [] Se recopiló el diario y el estado del proceso antes de reiniciar.
- [ ] Se verificaron políticas de volcado de memoria y de información confidencial.
- [] La salida del comando garantizada no incluía secretos.

### Procesos y recursos

- [] Verificó el árbol de procesos y el propietario.
- [ ] Distinguido CPU, carga y I/O espera.
- [] Verificó los límites del host y del grupo c.
- [] Se comprobó la composición de la memoria y los eventos OOM.
- [] Descriptores comprobados y estados de socket.
- [] Comprobamos tanto los bytes del disco como los inodos.

### Operaciones de servicio

- [ ] El usuario y el entorno de ejecución de la unidad son explícitos.
- [] Se probó el cierre elegante con SIGTERM.
- [] Las tormentas de reinicio son limitadas.
- [ ] La preparación se distingue de la supervivencia del proceso.
- [] Se comprobó la retención del diario y la sincronización horaria.
- [] Funcionalidad verificada de cara al usuario después de la recuperación.

## Fallos y limitaciones comunes

### Comenzando con `kill -9`

Esto evita los ganchos de limpieza y diagnóstico.

También hay que considerar la posibilidad de corrupción en el Estado compartido.

### Mirando solo las métricas del host

Los contenedores y los servicios systemd pueden agotar los recursos dentro de los límites del cgroup.

### Suponiendo que no haya ningún registro significa que no ocurrió ningún evento

Los registros se pueden perder debido a una falla antes del vaciado del búfer, muestreo, límites de velocidad o almacenamiento completo.

Verifique métricas, eventos del kernel y seguimientos.

### Intentando eliminar un proceso en estado `D` inmediatamente con una señal

El manejo de la señal puede retrasarse hasta que se libere la espera ininterrumpida del núcleo.

Investigue el I/O subyacente y el estado del dispositivo.

### Ejecución de seguimiento ilimitado en producción

La propia herramienta de diagnóstico puede crear latencia y problemas de disco.

Defina el alcance, la duración, los filtros y la reversión antes de su uso.

## Referencias oficiales

- [Proyecto de páginas de manual de Linux](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [señal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.servicio](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [Documentación del cgroup v2 del kernel de Linux](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## Conclusión

El diagnóstico de Linux no se trata de memorizar comandos; se trata de leer la evidencia expuesta por el núcleo en los límites correctos.

Pruebe hipótesis conectando procesos, descriptores, memoria, sistemas de archivos, señales, cgroups y el administrador de servicios.

Incluso cuando sea necesario reiniciar, primero conserve la evidencia y verifique la recuperación a través de la funcionalidad de cara al usuario para reducir los incidentes repetidos.
