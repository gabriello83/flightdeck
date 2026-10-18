# 59 · La revisión de clientes

Lo pidió Gabriele el 18 de octubre de 2026: un cuadrado **Revisión clientes** en el informe
general operativo (`/operativo/`) y detrás una página (`/revision/`) con lo que está mal
configurado máquina a máquina, filtrable por **delegación, cliente y centro**.

## Lo que enseña

| | qué es | de dónde sale |
|---|---|---|
| **Cuadrado** | el número de **máquinas sin planograma**; al lado, los planogramas creados ayer y cuántas máquinas tienen productos sin tarifa o precio distinto. Sin semáforo: es una cuenta, no un porcentaje | |
| **Sin planograma** | máquina instalada marcada «sin planograma» en VenCloud o sin un solo canal con artículo | la regla del bloque de instalaciones (`reglas.sin_planograma`), sobre el censo M5 |
| **Sin tarifa** | una fila por máquina con productos para los que VenCloud no encuentra precio, con el **nivel** del que sacan el precio los demás (punto de venta, centro, cliente, estándar…). Las de **tarifa estándar** van señaladas en ámbar, con el nombre de la tabla y a quién está asignada. Pulsando la matrícula, los productos sin tarifa con lo que cobran hoy | el detalle de tarifas (docs/52), vuelto por máquina |
| **Precio distinto** | una fila por máquina con cuántos productos cobran distinto de su tarifa, de cuántos comprobados, y la **diferencia más grande** (lo cobrado menos la tarifa, con su signo). Pulsando, los productos y cada medio de pago | lo mismo |
| **Planogramas creados** | las máquinas que la noche anterior no tenían planograma y en esta sí, por día, con el **usuario** que lo creó cuando llegue | el censo de esta noche contra el de la anterior |

Cada tabla y cada máquina tiene su **Excel**. El de sin tarifa lleva las tres columnas amarillas
para que la delegación ponga el precio, como el de la página de tarifas.

## Por qué «sin tarifa» no es la cuenta del bloque de instalaciones

El bloque de instalaciones marca «sin tarifa» la máquina que no tiene **ningún id de tarifa** en
el punto de venta, el centro ni el cliente (432 a 18-oct). Esa regla cuenta la tarifa estándar
asignada al **centro**, que VenCloud no usa (docs/52), y no ve un producto suelto sin precio en
una máquina que sí tiene tarifa. Aquí se cuenta lo que de verdad pasa al vender: el producto
repuesto en seis meses para el que la búsqueda de VenCloud no encuentra nada. Así coincide con la
página de tarifas, producto por producto.

A 18-oct-2026, en el interno: **301** máquinas sin planograma, **1.894** máquinas con algún
producto sin tarifa (10.603 productos; 184 máquinas sin ninguna tarifa en ningún producto, 416
cuyo nivel principal es una tarifa estándar) y **1.541** con precio distinto (12.055 productos).

## Los planogramas creados, y quién

VenCloud no guarda la historia del planograma: `recursos.maquinascanales` es el estado de hoy
(docs/04) y `fechaultcambioplanograma` no se rellena nunca (docs/09). Así que cada noche
`cabina/_revision/planogramas.json.gz` guarda las máquinas sin planograma, y la noche siguiente
las que ya lo tienen y siguen instaladas son **planogramas creados ayer**. Una máquina retirada
sin planograma no cuenta como creada. Se guardan dos meses. La primera noche no hay con qué
comparar: los creados empiezan a salir el día después del primer despliegue.

**Quién lo creó** sale del registro de actividad de VenCloud. Las tablas del planograma no
guardan usuario (sonda M14Z, 18-oct), pero `control.activitylog` apunta cada cambio de canal con
su usuario, y `control.veneventlog` avisa de cada cambio de planograma (sonda M14Y). El informe
`M14 · EXT_PLANOGRAMA_USUARIOS` (docs/17) baja cada noche los últimos siete días, y a cada
planograma creado se le pone el usuario que más tocó los canales de esa máquina desde la noche
anterior. Sin ese informe la página lo dice y no pone a nadie.

## Lo que escribe la noche

- `cabina/<perfil>/revision.json.gz`: las cuatro tablas del perfil, ya con sus productos. El
  interno son unos 9 MB de JSON y 0,5 MB comprimido; la API lo sirve comprimido tal cual
  (`/api/revision`), como las incidencias.
- `foto.revision` en `operativo.json`: lo que enseña el cuadrado.
- `cabina/_revision/planogramas.json.gz`: el estado de una noche a otra, de toda la red.

La API sirve sólo el del perfil de la sesión, con la misma regla que el cuadrado (sesión de
instalaciones, operaciones para arriba). Se prueba con `python3 infra/test_revision.py`.
