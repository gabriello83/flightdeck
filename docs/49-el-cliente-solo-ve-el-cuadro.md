# 49 · Un cliente sólo ve el cuadro, y la consola decide qué partes

> `infra/api/autorizacion.py` (`SESIONES`, `SECCIONES_CUADRO`, `recorta_cuadro_*`),
> `infra/api/lambda_api.py` (`/api/yo`, `/api/cuadro`, `/api/admin/perfiles`), `app/cuadro/`,
> `app/consola/`, `app/panel/`, `app/index.html`.

Lo pidió Gabriele el 8 de octubre de 2026: *«todos los usuarios que tienen perfil cliente pueden
tener sólo el mando de control, y en el perfil podré elegir qué puede ver en el mando de control»*.

## Un cliente sólo tiene el cuadro

Las seis sesiones del panel que eran de cliente (Resumen, Venta y consumo, Servicio recibido,
Disponibilidad, Surtido y planograma, Calidad) piden ahora **operaciones**. No hay una regla nueva:
es el mismo techo por tipo de siempre (`sesiones_de`), así que se aplica en un único sitio y la
consola lo pinta sola, tachadas con «· desde operaciones».

Lo que eso arrastra, sin tocar nada más:

| | un cliente, antes | un cliente, ahora |
|---|---|---|
| `/api/yo` → `sesiones` | las que tuviera marcadas | sólo `cuadro`, si lo tiene marcado |
| `/api/panel` | su panel recortado | ningún bloque: ni servicio, ni dinero, ni sat |
| `/api/serie` | sus filas con los bloques de sus sesiones | el índice (las fichas de sus centros, que usa el filtro del cuadro) y filas sólo con la fecha |
| entrada (`/`) | al cuadro si lo tenía, si no al panel | **siempre al cuadro** |
| `/panel/` | su panel | le manda al cuadro |
| el asistente | contestaba con su panel | ya no tiene panel del que contestar |

Un cliente al que no se le ha marcado el cuadro entra y lee «Tu perfil todavía no tiene el cuadro de
mando activado». En la consola, un perfil de cliente **nuevo** trae el cuadro marcado de serie.

## Qué partes del cuadro ve

En la consola, al editar un perfil que tiene marcado «Cuadro de mando», sale **«Qué ve en el cuadro
de mando»** con una casilla por parte, en el orden de la página. Todas puestas de serie.

El perfil guarda las que se le **quitan** (`cuadro_ocultas`), no las que ve. Así, el día que el cuadro
tenga una parte nueva, sale a todos sin tener que editar cada perfil. Un perfil sin ese campo, como
el de AIRBUS hoy, lo ve todo.

| parte | datos que necesita |
|---|---|
| Indicadores | venta, visitas, incidencias |
| Evolución diaria | venta, visitas, incidencias |
| Mapa de centros | venta, visitas, incidencias |
| Visitas realizadas por máquina | visitas |
| Mix de artículos | venta |
| Incidencias por operación | incidencias |
| Rendimiento por máquina | venta, visitas, incidencias |
| Detalle de incidencias | incidencias |
| Máquinas sin venta | venta |
| Máquinas con venta baja | venta |
| Máquinas por centro | venta |
| Listado de visitas | visitas |
| Mantenimientos preventivos | — |
| Conclusiones | venta, visitas, incidencias |

## Lo que no se ve tampoco se sirve

Esconder una tarjeta en la página no basta: el mes del cuadro lleva la venta, las visitas y las
incidencias juntas, y con las herramientas del navegador se verían. Así que la API sirve la **unión
de los datos de las partes que el perfil ve**, y nada más:

- Si ninguna parte que le queda usa la venta, el índice sale sin la cabecera `ventas` y sin el importe,
  las unidades y la fuente de cada mes, y cada mes sale sin `ventas` ni `articulos`. Igual con las
  visitas y las incidencias.
- Si lo ve todo, el fichero sale tal cual, sin leerlo como JSON, como hasta ahora.
- Las partes que mezclan los tres datos (indicadores, evolución, mapa, rendimiento, conclusiones)
  piden los tres: con uno de menos enseñarían ceros que no son ceros.

Consecuencia que hay que tener presente al marcar: **quitar «Mix de artículos» no quita la venta** si
siguen puestos los indicadores, que la enseñan. Para que a un cliente no le llegue la venta hay que
quitarle todas las partes que la piden (la tabla de arriba).

La página, con lo que le llega: esconde las tarjetas que no ve; una fila que se queda sin ninguna
desaparece, y una que pierde alguna reparte el ancho entre las que quedan. Sin venta no salen el
filtro de artículo, el aviso de venta parcial ni el «enlace de fuentes» del pie, y el Excel sólo
lleva las hojas de los datos que recibe.

## Desplegarlo

Nada de CloudFormation ni de S3 `config/`: sólo código.

1. **Lambda de la API.** `Lambda → digivend-api → Code → Upload from → .zip file` → `api.zip` →
   **Save**.
2. **Lambda de alarmas.** `Lambda → digivend-alarmas → Code → Upload from → .zip file` →
   `alarmas.zip` → **Save**. Lleva la misma `autorizacion.py`.
3. **Las páginas**, en `S3 → digivend-web-…`, con `Content-Type: text/html; charset=utf-8` y
   `Cache-Control: no-cache`: `index.html` (la entrada), `cuadro/index.html`, `consola/index.html` y
   `panel/index.html`. Luego `CloudFront → Invalidations → Create invalidation` → `/*`.
4. **Comprobarlo.** Entrar con un usuario de AIRBUS: tiene que ir directo al cuadro, sin el botón
   «Panel de servicio». En la consola, `Perfiles → AIRBUS → Editar`: salen las casillas del cuadro,
   todas puestas.
