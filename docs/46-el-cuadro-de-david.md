# 46 · El cuadro de David, para el perfil de AIRBUS

> `app/cuadro/index.html` (la página), `infra/cuadro.py` (el cálculo), `/api/cuadro` (el servicio).
> Referencia: `referencia/dashboard-david/`.

AIRBUS ya conoce el cuadro de mando que le monta David para San Pablo Sur: catorce secciones,
filtros cruzados, mapa, y un Excel de cuatro hojas que se arrastra a mano. El perfil de AIRBUS
ahora entra a **ese mismo cuadro** —los mismos gráficos y tablas, el mismo código de dibujo— pero
alimentado cada noche desde VenCloud y con sus nueve centros, no uno.

## Qué es igual y qué cambia

La página es la de David. Se ha cambiado lo justo:

| | David | Aquí |
|---|---|---|
| De dónde salen los datos | arrastrando los Excel | `/api/cuadro`, calculado cada noche |
| Alcance | San Pablo Sur, 125 máquinas | los 10 centros de AIRBUS, 563 máquinas |
| Botones | cargar Excel, guardar HTML, HTML por centro, Excel, imprimir | Excel (si el perfil puede exportar) e imprimir |
| Nombre del centro | antepone «AIRBUS» | el de VenCloud, tal cual |
| Preventivos | su hoja | **sin fuente**, y lo dice |

Fuera «guardar copia HTML» y «HTML por centro»: metían los datos dentro de un fichero que viaja
solo, y en un portal de cliente el dato se sirve a quien tiene sesión, no se reparte.

## De dónde sale cada hoja

| hoja de David | nuestro informe | notas |
|---|---|---|
| **Ventas** | `telemetria_ventas` (A12) si está; si no, `visita_ventas` (A11) | ver abajo |
| **Visitas** | `visita_cabecera` (A1) | sólo visitas de persona (`reglas.visitas_reales`) |
| **Averías** | `sat_averias` (D7), series A **y** E | David mete las dos: «Reponer distribuidor automático» es serie E y está en su hoja |
| **Preventivos** | — | **no hay fuente** |
| censo | `m_instalaciones` (M5) | máquinas vivas del ámbito del perfil |

Comprobado contra su Excel en lo que se solapa (junio–agosto, San Pablo Sur): las averías cruzan
por número, y en las 122 que él marca «Finalizado» nuestro `tipo_estado` es 9 y la fecha de
cierre es nuestra `fecha_fin`. Las visitas salen del mismo orden: 3.970 en 120 días contra sus
4.135 en cuatro meses.

### La venta: hoy es parcial

`visita_ventas` es la venta que trae el parte, y tiene dos límites que el cuadro **avisa en
pantalla**:

- **Sólo trae las máquinas que se leen en el parte.** En AIRBUS, 365 de 563 en 120 días. De las
  125 de David, faltan 43, todas con telemetría. No hay forma de saber desde el censo cuáles van a
  faltar.
- **Fecha la venta el día de la lectura**, no el de la venta. La evolución diaria sale a picos.

Con eso, una máquina sin filas no es una máquina sin venta, así que mientras la fuente sea
parcial la página dice **«sin dato de venta»** en vez de «sin venta» (título, KPI, tablas).

La venta buena es la de telemetría, venta a venta y con su fecha: el informe **A12 ·
EXT_TELEMETRIA_VENTAS** (`docs/17`). Está escrito y la Lambda ya lo lee si existe
(`crudo/telemetria_ventas/`); falta crearlo en VenCloud. El día que haya telemetría, la del parte
deja de usarse ese día —serían las mismas ventas dos veces— y el aviso desaparece solo.

**8-oct-2026: creado en VenCloud como informe 179** y añadido con ese nombre al
manifiesto. La muestra del 7-oct trae 63.660 ventas de todo el parque, `id` único por fila, un
20,7 % sin artículo; de AIRBUS (por número de centro) 18.346 ventas en 531 máquinas en un solo
día, contra las 353 de 564 que da el parte en todo el mes.

### Preventivos: no hay de dónde leerlos

Los «Mantenimiento preventivo» de David (estado, PDV, ubicación, máquina, centro, «realizada
por», fecha y hora) no están en ningún informe que extraigamos. Lo comprobado:

- `tipo_tarea = 'E'` del D7 **no** son preventivos: son «Reponer distribuidor automático»,
  «Devolución dinero in situ», «Cambio de planograma». `docs/` lo daba por bueno sin mirarlo.
- La operación `8888888` («Preventivo Electrodomésticos Airbus») aparece una vez en todo el año.
- Ni `sat_eventos` ni `sat_visitas` traen el texto.

La tabla dice «Sin fuente de datos». Para tenerla hay que preguntar a David **de qué pantalla de
VenCloud exporta esa hoja**: con eso se escribe el informe.

## Cómo se calcula y cómo se sirve

`infra/cuadro.py` es un acumulador más de la Lambda de agregados, y se calcula para **todo perfil
de cliente** (los que tienen ámbito), sea de `perfiles.json` o de la consola (`docs/47`). Quién lo
**ve** lo decide una casilla: la sesión «Cuadro de mando», que se marca en la consola al editar el
perfil. Así activarlo para un cliente, también uno nuevo, es cosa de la consola, sin tocar ningún
fichero. El interno (ámbito vacío, todo el parque) no lo calcula; `"cuadro": false` en un perfil de
`perfiles.json` lo apaga a mano.

No va en `panel.json`. El cuadro filtra por día, máquina y artículo en el navegador, así que
necesita la venta a ese grano: unas 230.000 combinaciones en 120 días con la venta parcial, y del
orden del doble con telemetría. En el panel iría al contexto del asistente y rozaría los 6 MB de
respuesta de una Lambda. Va en `cabina/<perfil>/cuadro/`:

| fichero | qué lleva | tamaño (AIRBUS, 120 días) |
|---|---|---|
| `indice.json` | centros, máquinas, artículos, visitas, incidencias, fuente de la venta, lista de trozos | 0,5 MB |
| `ventas-AAAA-MM.json` | `[día, máquina, artículo, unidades, importe]` | 0,2–1,4 MB por mes |

Las máquinas y los artículos van una vez en el índice y las filas los citan por posición. Si un
mes pasara de 4,5 MB se parte por días (`ventas-AAAA-MM.2.json`) sin que nadie toque nada.

`/api/cuadro` devuelve el índice y `/api/cuadro?trozo=AAAA-MM` un trozo. La carpeta sale del
perfil de la sesión, como el panel; lo único que se pide es el trozo, y sólo se sirve uno que
**el índice cite**: no hay forma de componer otra clave. El fichero se devuelve tal cual, sin
abrirlo. Pide la sesión **«Cuadro de mando»** (`autorizacion.SESIONES["cuadro"]`), que el
administrador marca en la consola como cualquier otra.

El cuadro arranca en el último mes con dato y **no pasa del día anterior al cálculo**
(`generado`): los datos llegan cerrados hasta ayer, y el resto del mes no son días sin venta, son
días que no han llegado. Ni el filtro ni la evolución diaria los pintan a cero.

Quien tiene esa sesión entra directo al cuadro al iniciar sesión; desde el cuadro hay un botón al
panel de servicio y desde el panel otro al cuadro.

Los trozos de meses que salen de la ventana se quedan en S3: borrarlos pediría
`s3:DeleteObject` al rol de agregados, que no lo tiene ni lo necesita para nada más. No se ven:
la API sólo sirve los que cita el índice de esa noche.

## Desplegarlo

Ficheros en `paquetes/` y la página en `app/cuadro/`. En orden:

1. **Lambda de agregados.** `Lambda → digivend-agregados → Code → Upload from → .zip file` →
   `agregados.zip` → **Save**. Lleva ahora tres ficheros: `lambda_agregados.py`, `reglas.py` y
   `cuadro.py`.
2. **Lambda de la API.** `Lambda → digivend-api → Code → Upload from → .zip file` → `api.zip` →
   **Save**.
3. **La web.** `S3 → digivend-web-…`:
   - en la raíz, `index.html` (el acceso, que ahora manda al cuadro a quien lo tiene);
   - en `panel/`, `index.html` (el botón «Cuadro de mando»);
   - **Create folder** `cuadro` y dentro `index.html`.

   Tras subir, mira que el nombre sea `index.html` y no `index (1).html`: el navegador renombra
   las descargas repetidas y CloudFront no sirve otro nombre.
4. **CloudFront.** `CloudFront → la distribución → Invalidations → Create invalidation` →
   `/index.html`, `/panel/*`, `/cuadro/*` → **Create invalidation**.
5. **Los agregados, a mano.** `Lambda → digivend-agregados → Test → {}` → **Test**. En el
   resultado, `cuadros.cli-airbus` debe decir `fuente: visita_ventas` y unas 365 máquinas con
   venta de 563; en S3, `cabina/cli-airbus/cuadro/indice.json` y cinco `ventas-2026-MM.json`.
6. **Activarlo en el perfil.** `dashboard.digivend.es/consola/ → Perfiles → AIRBUS → Editar` → marca
   **Cuadro de mando** → **Guardar**. Es la única llave: quitarla lo esconde en el acto.
7. **Entrar como AIRBUS.** Debe abrir `/cuadro/` con el aviso amarillo de venta parcial.

## Lo que falta

- **El relleno de la telemetría hacia atrás** (informe 179): hasta entonces, los días anteriores
  al 8-oct-2026 siguen con la venta del parte y su aviso.
- **Preventivos**: saber de qué pantalla los exporta David.
- **ITC** sale «sin coordenadas» en el mapa: el mapa de David sólo sitúa los centros que conocía, y
  no se inventa una posición.
