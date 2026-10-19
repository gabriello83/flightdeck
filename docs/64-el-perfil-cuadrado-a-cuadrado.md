# 64 · El perfil, cuadrado a cuadrado

Lo pidió Gabriele el 19 de octubre de 2026 (por segunda vez): en **Perfiles → Nuevo perfil →
«Sesiones que ve»** se elige cada cuadrado del informe operativo por separado y, dentro de cada
uno, qué ve. Nada de sesiones que agrupen varios cuadrados, como «Instalaciones y altas», que
daba Revisión clientes, Tarifas, Telemetría, Puntos de venta y Utilizo de una vez.

## Lo que se ve en la consola

En «Sesiones que ve» (sólo para el personal; los clientes tienen el interruptor del cuadro de
mando, docs/63) salen:

1. **Los cuadrados del informe operativo**, uno a uno, en el orden de la página. Marcado el
   cuadrado, se marcan dentro sus tablas, todas puestas de serie. Los de una sola tabla lo dicen.
   Puntos de venta, Ventas y Reposiciones no tienen página propia y llevan al panel, así que
   dentro tienen sus paneles.
2. **Además del informe operativo:** Resumen y sus paneles, Servicio recibido, Disponibilidad,
   Avisos y acciones, y Cuadro de mando.

Almacenes y Utilizo salen apagados por debajo de dirección. Utilizo dice «sólo sin ámbito»:
con ámbito no le sale, como siempre (docs/60).

## Cómo se guarda

- `cuadrados` en `PERFIL#…`: los que ve. **Manda sobre las sesiones.**
  `autorizacion.cuadrados_de` lee de ahí los cuadrados del perfil. Un perfil guardado antes, sin
  esa lista, sigue sacándolos de sus sesiones como hasta ahora: no cambia nada hasta que se edita.
- `tablas_ocultas` en el perfil: las tablas quitadas. `con_usuario` las suma a las que se le
  quiten a cada usuario (docs/61), y la consola no le ofrece a un usuario las que su perfil ya no
  ve.
- Los cuadrados que llevan al panel (`autorizacion.PANEL_DE_CUADRADO`) dan su sesión: Puntos de
  venta da «Instalaciones y altas», y Ventas y Reposiciones dan «Venta y consumo». La pone el
  servidor. Los paneles de un cuadrado no elegido se quitan (`paneles_ocultos`, docs/63), aunque
  compartan sesión con uno elegido. Ventas sin Reposiciones no enseña «Reposición del periodo».
- Las sesiones que no salen en el formulario (Surtido, Calidad, Rutas y jornada, Efectivo,
  Stock, Rentabilidad, Cumplimiento) no tenían ni paneles ni cuadrados propios. Al guardar un
  perfil con el formulario nuevo, se quedan fuera.

## Despliegue

`api.zip` y `alarmas.zip`, y la página `consola/` con `Cache-Control: no-cache`, más la
invalidación. Sin cambios en las pilas ni en los agregados.
