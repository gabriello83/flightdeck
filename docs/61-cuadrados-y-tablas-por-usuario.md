# 61 · Cuadrados y tablas por usuario

Lo pidió Gabriele el 19 de octubre de 2026: que el administrador elija, para cada usuario del
panel de Serunion, a qué cuadrados del informe general operativo entra y, dentro de cada
cuadrado, qué tablas ve.

## Lo que había

Todo se decidía **por perfil**: las sesiones del perfil daban los bloques del panel, y los
bloques, los cuadrados (`autorizacion.cuadrados_de`). Dos usuarios del mismo perfil veían
exactamente lo mismo, y no había forma de quitar una tabla de una página. Lo único parecido era
«Qué ve en el cuadro de mando» (docs/49), y es del cuadro de los clientes, también por perfil.

## Lo que hay

En la consola, **Usuarios → Editar**, debajo del perfil, sale **«Qué ve en el informe
operativo»**: los cuadrados que ve su perfil, cada uno con sus tablas, todo marcado de serie. Se
desmarca lo que ese usuario no deba ver. En la lista de usuarios, la columna «Informe operativo»
dice «Todo lo de su perfil» o, por ejemplo, «4 de 5 cuadrados · 1 tabla quitada».

Tres reglas:

1. **Quitar, nunca dar.** El usuario hereda lo de su perfil; se le puede quitar, no añadir. Lo
   que el perfil no ve no sale en la lista, y aunque se mandara a mano, `cuadrados_de` parte de lo
   del perfil y sólo resta.
2. **Se guarda lo que se quita** (`cuadrados_ocultos`, `tablas_ocultas` en la ficha
   `USUARIO#…`), como `cuadro_ocultas`: un cuadrado o una tabla nueva le sale a todo el mundo sin
   tocar a nadie.
3. **El ámbito sigue siendo del perfil.** Los ficheros se escriben por perfil por la noche
   (CLAUDE.md, «el ámbito se aplica al escribir»); lo del usuario se aplica al servir, sobre el
   fichero de su perfil, y sólo quita.

## Cómo se aplica

`autorizacion.con_usuario(perfil, usuario)` se llama en la API justo después de leer la sesión: a
partir de ahí, cada regla que mira el perfil mira ya el del usuario. Así:

- **Un cuadrado quitado** no sale en `/api/operativo` y su página contesta 403
  (`/api/rutas`, `/api/incidencias`…), por la misma comprobación de siempre.
- **Una tabla quitada** no se dibuja (`/api/yo` trae `tablas_ocultas`) y, **si sus datos no los
  usa nada más de la página, no salen del servidor** (`autorizacion._SOLO_DE_UNA`):

| cuadrado | tabla | lo que deja de llegar |
|---|---|---|
| Rutas | Máquinas no visitadas | la lista máquina a máquina de cada día (`visitas`) |
| Rutas | Festivos por delegación | el control de festivos |
| Incidencias | Lista de incidencias y su ficha | el texto, la ubicación y el punto de venta de cada una |
| Furgonetas | Furgonetas con visitas | los vehículos de cada día |
| Furgonetas | Visitas sin vehículo | las visitas sin vehículo de cada día |
| Revisión clientes | cada una de sus cinco | su lista |

Las demás (los gráficos de incidencias y devoluciones, «Por delegación», «Visitas por ruta»)
salen de las mismas filas que las que sí se ven: quitarlas del fichero dejaría a las otras con
ceros que no son ceros, así que no se dibujan pero sus filas siguen llegando. Con nada quitado, el
fichero sale tal cual, sin abrirlo, como antes.

## Qué tablas tiene cada cuadrado

En la consola sólo se eligen tablas en las páginas que tienen más de una (`autorizacion.TABLAS`, que
lleva también las de una sola tabla para la estrella de preferidos, docs/62):

- **Rutas**: Visitas por ruta, Estado de las visitas, Máquinas no visitadas, Por delegación,
  Festivos por delegación.
- **Incidencias**: Total por zona, Los 10 centros con más averías técnicas, Lista de incidencias
  y su ficha (la hoja «Incidencias abiertas»; sin ella no hay hojas).
- **Devoluciones**: Por mes y canal, Por canal y por origen, Por zona y delegación, Los 15
  centros, Las 15 máquinas, Por técnico, Sin cerrar (la segunda hoja).
- **Furgonetas**: Furgonetas con visitas, Visitas sin vehículo, Por delegación (las tres
  pestañas) y el día a día.
- **Revisión clientes**: Sin planograma, Sin tarifa, Precio distinto, Planogramas creados,
  García y Marcos.

Almacenes, Tarifas, Telemetría y Utilizo tienen una sola tabla, y Puntos de venta, Ventas y
Reposiciones llevan al panel: en esos, quitar la tabla es quitar el cuadrado.

## Lo que no cambia

- El **panel** (`/panel/`) sigue yendo por las sesiones del perfil. Quitarle a un usuario el
  cuadrado de Ventas lo quita del informe operativo, no la sesión «Venta y consumo» del panel.
- El **cuadro de mando** de los clientes sigue eligiéndose por perfil (docs/49).
- Un usuario guardado antes de esto ve lo mismo que su perfil.

## Despliegue

Sin cambios en la pila ni en los agregados: `api.zip` (y `alarmas.zip`, que lleva la misma
`autorizacion.py`), y las páginas `consola/`, `operativo/`, `rutas/`, `incidencias/`,
`devoluciones/`, `furgonetas/` y `revision/`, con `Cache-Control: no-cache`, más la invalidación
de CloudFront.
