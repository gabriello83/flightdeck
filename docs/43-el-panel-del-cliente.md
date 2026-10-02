# 43 · El panel del cliente

> `app/index.html` (acceso) y `app/panel/index.html` (panel), contra la API de verdad.
> Validado con el panel de AIRBUS: nueve centros, 120 días.

## Una página, no una por cliente

`app/airbus/index.html` era una página de AIRBUS: sus dieciséis paneles estaban escritos para
AIRBUS y leían un JSON fabricado a mano. La de ahora no sabe quién es AIRBUS.

**AIRBUS es un perfil, no una página.** El navegador pide `/api/yo` y `/api/panel`, y dibuja lo que
venga. Cada panel declara dos cosas:

```js
{ id:"centros", sesion:"resumen", bloque implícito: P.servicio, ... }
```

y se dibuja sólo si **el bloque llegó** y **el perfil tiene esa sesión**. Un cliente con otras
sesiones ve otros paneles sin que nadie toque una línea de la página. Un cliente nuevo no necesita
página nueva: necesita una fila en `perfiles.json` y un perfil en DynamoDB.

Esto no es una comodidad de programación. El recorte lo hace `autorizacion.recorta` **en el
servidor**: lo que no debe ver este perfil no sale de AWS. La página no oculta nada, porque no
recibe nada que ocultar. Y no hay ningún parámetro con el que pedir el panel de otro perfil: el
perfil sale de la fila de sesión, nunca de la petición.

## Lo que ve AIRBUS, y de dónde sale

Sesiones concedidas: `resumen`, `venta_consumo`, `disponibilidad`, `surtido`.

| Panel | Sesión | De dónde sale |
|---|---|---|
| Visitas por día | resumen | `servicio.visitas_por_dia` |
| Visitas por centro | resumen | `servicio.por_centro` |
| Patrón semanal | resumen | calculado en el navegador sobre `visitas_por_dia` |
| Duración de la visita | resumen | `servicio.duracion_min` |
| Recaudación por mes | venta_consumo | `dinero.periodos` |
| Efectivo sin telemetría | venta_consumo | `dinero.periodos[].pct_ciego` |
| Reposición del periodo | venta_consumo | `servicio.carga` |
| Merma por motivo | servicio | `servicio.merma` |
| Caducidad por artículo | servicio | `servicio.merma.caducidad_por_articulo` |
| Disponibilidad y averías | disponibilidad | `sat` |
| Máquinas reincidentes | disponibilidad | `sat.reincidentes` |

Lo que **no** llega al navegador de un cliente, aunque esté en el panel interno: `coste_servicio`
(lo que nos cuesta a nosotros atenderle) e `inventario.existencias` (nuestro stock). No es pudor:
es que no es dato suyo. Lo quita `recorta` antes de responder, y hay una prueba que lo vigila.

El `surtido` está concedido y no sale ningún panel: ese bloque todavía no lo calcula la Lambda de
agregados. Es correcto que no aparezca nada —mejor eso que un panel vacío que parece un cero.

## El fallo que apareció al enchufarlo

Al construir el panel con datos reales salió **0 € de recaudación y 0 unidades cargadas** para
AIRBUS. Las demás cifras eran buenas, que es lo que lo hacía peligroso: un panel con la mitad de
los números bien no parece roto, parece un mes flojo.

La causa: **sólo tres de los ocho informes traen columna `centro`** —`visita_cabecera`,
`stock_maquina` y `sat_averias`—. Los otros cinco traen `matricula` y nada más. Y el ámbito de un
perfil de cliente se declara por nombre de centro (`"clientes": ["AIRBUS"]`), así que
`en_ambito` miraba un campo que en esas filas no existe, no encajaban en ningún ámbito, y se caían
enteras.

Por qué no lo cazó la prueba: **la prueba se inventaba la columna**. Los datos de
`test_agregados.py` llevaban `"centro": "AIRBUS GETAFE"` en las filas de recaudación y de
reposición, donde el informe de verdad no lo lleva. La prueba verificaba un modelo de datos que no
era el nuestro. Ahora las filas de la prueba llevan exactamente las columnas que trae VenCloud, y
el que las lea verá cuáles son.

El arreglo es `MapaCentros`: mientras lee, aprende de qué centro es cada máquina a partir de los
informes que sí lo dicen, y las filas que no lo dicen se resuelven por su matrícula. No cuesta ni
una descarga más, porque sale de lo que ya se estaba leyendo. Las fuentes se reordenaron para que
los tres informes con `centro` vayan primero; como todas las reglas son cuentas y sumas, el orden
no cambia ningún resultado, y hay una prueba que lo demuestra.

El mapa **no se guarda entre ejecuciones**, a propósito: una máquina se cambia de centro, y un mapa
viejo le atribuiría la recaudación al cliente equivocado. Vale lo que diga la ventana que se está
agregando.

Las jornadas son la excepción que no tiene arreglo: son de una ruta y un vehículo, no de un centro,
y el informe no trae matrícula. No se pueden atribuir a un cliente. Tampoco hace falta: ese bloque
no llega a un perfil de cliente.

## Decisiones de dibujo

Las de siempre, y una nueva:

- **Un solo eje.** La recaudación lleva efectivo y banco apilados porque son la misma unidad. Nunca
  dos escalas en el mismo gráfico.
- **Los meses sin cerrar van con trama**, no sólo con color: se ven igual impresos en blanco y
  negro y para quien no distingue los tonos. Y debajo dice cuáles y por qué (falta el cobro por
  tarjeta, que se escribe al mes siguiente).
- **Cada gráfico lleva su tabla detrás**, plegada. Es la única forma de leer una cifra exacta y la
  única que funciona con un lector de pantalla. El verde de «Caducidad por artículo» tiene 2,74:1
  de contraste sobre el papel claro —por debajo de 3:1—, y por eso lleva obligatoriamente la cifra
  escrita en cada barra y su tabla.
- **El nombre largo se recorta en el gráfico y entero en la tabla.** Un texto de SVG no se corta
  solo: «AIRBUS PUERTO REAL» se metía por debajo de su barra.
- **En el móvil el eje va en miles** (`483 k€`), nunca el dato: ése va entero en la etiqueta.
- **Paleta de tres**, validada en claro y en oscuro con el validador, no a ojo.

## Qué se guarda dónde

| Qué | Dónde | Por qué |
|---|---|---|
| Modo claro/oscuro | `localStorage` | es de este aparato: en la pantalla del almacén se quiere oscuro y en el portátil claro |
| Orden de los paneles | servidor, `/api/orden` | viaja con la persona, no con el navegador |
| Sesión | cookie `HttpOnly` + fila con caducidad | se puede cerrar en el acto; un token firmado no |

## Lo que sigue sin existir

- El bloque `surtido`, que AIRBUS tiene concedido.
- Venta por máquina y por artículo para el cliente: hoy el panel da **servicio**, no venta. La
  venta está en `visita_ventas`, que se extrae pero todavía no se agrega.
- La consola de administración (`app/consola/`) sigue siendo el prototipo: no valida contraseñas
  contra Cognito.
- El asistente y las alarmas, que tienen API y pruebas pero no pantalla.

---

# El asistente y los avisos

## El asistente va dentro del panel, no en una página aparte

Un asistente al que hay que ir es un asistente que no se usa: la pregunta surge **mirando una
cifra**, y si para preguntarla hay que salir de la pantalla donde está la cifra, no se pregunta. Va
en un cajón lateral, sobre el panel, y el botón sólo aparece si `/api/yo` dice que está habilitado
para este usuario — los tres interruptores en serie (plataforma, perfil, usuario) los resuelve el
servidor.

La página **no le manda el panel**. Le manda la pregunta y los últimos turnos; el panel lo pone la
Lambda, que ya sabe de qué perfil es la sesión y le entrega exactamente el mismo recorte que recibió
este navegador. Si el dato no está en el panel de este usuario, el asistente tampoco lo tiene.

Las preguntas sugeridas salen de los bloques que han llegado, no de una lista fija: a un perfil sin
recaudación no se le ofrece preguntar por la recaudación.

Lo que vuelve se enseña como texto plano con saltos de línea. No hay intérprete de Markdown porque
no hay forma de traer uno sin llamar a un dominio externo, y escribir uno a mano para poner tres
negritas no vale lo que cuesta.

## Avisos y alarmas: `/avisos/`

Dos permisos, y se nota: `alarmas_ver` entra en la página, `alarmas_crear` es lo que enseña el botón
de «Nueva alarma» y los de editar y borrar. Quien sólo ve, sólo ve. El servidor lo vuelve a
comprobar en cada ruta: lo de la página es comodidad, no seguridad.

**El catálogo de lo que se puede vigilar no está escrito en la página.** Estaba dentro de la Lambda
de alarmas; se ha movido a `infra/api/catalogo.py`, que usan las dos: la que evalúa y la API, que lo
sirve en `/api/catalogo-alarmas`. Así el día que se añada una fuente aparece sola en el formulario,
en vez de quedarse una lista vieja en el navegador que nadie recuerda actualizar.

Y el catálogo dice **cuáles se pueden evaluar hoy**. Seis de las diecisiete apuntan a cifras que los
agregados todavía no calculan. Una alarma sobre una de ellas se puede crear —queda escrita y
esperando—, pero el formulario lo advierte antes y la lista la marca «sin datos aún» después. Lo
contrario sería dejar que alguien crea que una máquina está vigilada cuando no lo está.

En el móvil las tablas pasan a ser fichas: cinco columnas en 390 px no se leen, y los botones se
quedaban fuera de la pantalla.

---

# La consola de administración

Era el único trozo que seguía siendo el prototipo: no validaba contraseñas y guardaba la
configuración en el navegador. Ahora va contra `/api/admin/*`, y lo que decide quién entra no es la
página — a quien no es administrador las rutas le contestan 403.

**Lo que no lleva escrito es lo importante.** La consola no tiene copiadas las reglas del modelo de
permisos: el techo de cada tipo, el tipo mínimo de cada sesión y lo que cada tipo trae de serie los
manda la API desde el mismo `autorizacion.py` que luego los aplica (`niveles` e `implicitos` se
añadieron a `GET /api/admin/perfiles` para esto).

Una copia en el navegador se quedaría vieja el día que cambiara esa pieza, y el síntoma sería el
peor posible: un administrador marcando una casilla que no hace nada y creyendo que ha concedido
algo. Con esto, al cambiar el tipo de un perfil las sesiones y los permisos fuera de su techo se
tachan en el momento, con el motivo al lado, y salen deshabilitados.

Seis secciones: usuarios, perfiles, plataforma, teléfonos, carga y cola de acciones. Las alarmas no
se duplican aquí: viven en `/avisos/`, que es donde las usa quien las usa, y la consola enlaza allí.

Dos cosas de la sección de carga valen por sí solas:

- **Un informe a cero se marca en rojo.** Es la única señal que hay cuando algo cambia en VenCloud:
  el informe se descarga igual, sin error, pero vacío. Si no se ve aquí, no se ve en ninguna parte,
  y los paneles siguen enseñando la cifra de la víspera como si tal cosa. Con la mudanza de clientes
  de este fin de semana (docs/44), es la pantalla que hay que mirar el lunes.
- **La cola dice que la incidencia no se ha dado de alta.** Es una escritura en el ERP y todavía no
  está enchufada: la petición se queda a la vista, con quién la pidió. Lo contrario sería que
  alguien creyera haber abierto un parte que no existe.
