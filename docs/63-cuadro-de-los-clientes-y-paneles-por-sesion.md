# 63 · El cuadro de los clientes, encendido o apagado, y los paneles de cada sesión

Lo pidió Gabriele el 19 de octubre de 2026, al crear perfiles en la consola:

- **Clientes:** elegir si el perfil tiene o no el cuadro de mando y, si lo tiene, qué ve dentro.
- **Personal de Serunion:** en «Sesiones que ve», cada sesión y, marcada, lo que se ve dentro de
  ella.

## Clientes: el cuadro de mando

En **Perfiles → Nuevo perfil** (o Editar), con el tipo «cliente», sale **«Cuadro de mando ·
Activado»**, puesto de serie. Debajo siguen **«Qué ve en el cuadro de mando»**, las partes de
docs/49, que sólo salen con el cuadro encendido.

Apagarlo es quitarle la sesión `cuadro`: el perfil se guarda con `sesiones: []`. Eso ya lo
respetaba todo:

- `/api/cuadro` contesta 403.
- `/cuadro/` dice «Tu perfil todavía no tiene el cuadro de mando activado. Pídeselo a Serunion
  Vending.»
- Los agregados lo siguen calculando, porque el cálculo va por el ámbito (docs/46). Volver a
  encenderlo no necesita esperar a la noche.

En la lista de perfiles, la columna Sesiones de un cliente dice «Cuadro de mando» o «sin cuadro».

## Personal: los paneles de cada sesión

Cada sesión de «Sesiones que ve» que dibuja paneles propios en `/panel/` lleva debajo **«En el
panel ve:»**, con sus paneles. Salen al marcar la sesión, todos puestos de serie, y se desmarca
lo que ese perfil no deba ver.

| sesión | paneles |
|---|---|
| Resumen | Visitas por día, Visitas por centro, Patrón semanal, Duración de la visita |
| Venta y consumo | Recaudación por mes, Efectivo sin telemetría, Reposición del periodo |
| Servicio recibido | Merma por motivo, Caducidad por artículo |
| Disponibilidad | Disponibilidad y averías, Máquinas reincidentes |
| Instalaciones y altas | Lo que hay instalado, Altas recientes, Instalaciones a medias, Instalaciones a medias, una tabla por clase |

Las demás sesiones no tienen paneles propios en `/panel/`. Dan cuadrados del informe operativo
(lo dice cada casilla, docs/61) o pantallas de la consola.

- **Se guarda lo que se quita** (`paneles_ocultos` en `PERFIL#…`), como `cuadro_ocultas`: un
  panel nuevo sale a todos sin tocar ningún perfil.
- **Se quita en la página, no en el fichero.** Los paneles de una sesión salen de los mismos
  bloques del panel. Quitar un bloque por un panel dejaría a los otros con ceros que no son
  ceros. Para que un dato no llegue al navegador, se quita la sesión entera.
- El catálogo vive en `autorizacion.PANELES_SESION`, y `test_autorizacion.py` comprueba que
  diga lo mismo que `app/panel/index.html`.

## Despliegue

`api.zip` y `alarmas.zip` (llevan `autorizacion.py`), y las páginas `consola/` y `panel/` con
`Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas ni en los agregados.
