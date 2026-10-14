# 52 · La telemetría de fuera: Nayax, Prodelfi y Nebula contra VenCloud

> `infra/telemetria.py` (leer y cruzar), `infra/api/lambda_api.py` (`/api/admin/telemetria`,
> `/api/telemetria`), `infra/operativo.py` (`pon_telemetria`, `telemetria_del_dia`,
> `detalle_telemetria`), `infra/lambda_agregados.py` (`lee_telemetria_externa`),
> `infra/plantilla-web.yaml` (`s3:PutObject` en `externo/telemetria/*`), `app/consola/`
> (pestaña Telemetría), `app/telemetria/` y el cuadrado de `app/operativo/`.

Lo pidió Gabriele el 14 de octubre de 2026, después de hacer a mano el listado de telemetría por
PDV y el fichero de importación para VenCloud: *«todo lo que se ha hecho ahora tendrá que salir
dentro del cuadrante telemetría y hacer los diferentes análisis: máquinas con telemetría que no
transmiten datos en Nayax; máquinas que están en Nayax y no están en VenCloud; máquinas que tienen
Prodelfi pero no entra la telemetría correctamente o el dato electrónico; lo mismo con Nebula»*.
Los ficheros los sube él **desde la consola**.

## El problema

VenCloud sabe qué máquinas le mandan venta por telemetría (informe 179) y cuáles le mandan su
lectura (DEX: partes de SYSTEM con `estado_lectura` 2). Lo que no sabe es cuáles **deberían**
mandarla. Su campo `telemetria` del censo dice 40 en 40 máquinas, cuando el 14 de octubre había
2.504 con un sistema de cobro conectado. Eso sólo lo saben los sistemas: Nayax, Prodelfi y Nebula
(los lectores Coges). Hasta ahora el cuadrado de telemetría medía el DEX sobre esas 40, que no son
el parque.

## Cómo llegan los ficheros

En `/consola/ → Telemetría → Subir ficheros…` se suben los cuatro, tal y como salen de cada
sistema, de uno en uno o todos a la vez:

| fichero | de dónde sale | se reconoce por |
|---|---|---|
| Nayax | MachineStatus (.xlsx) | `Jerarquía Operador` / `ID Máquina (Operador)` |
| Prodelfi | Máquinas (.xlsx) | `Código Máquina` y `Tipo Comunicación` |
| Nebula (Coges) | devices (.csv) | `Id telemetría` y `Nombre` |
| Grupos de Prodelfi | RadGridExport (.xls) | sólo `Código` y `Nombre` |

Se reconoce cuál es cada uno **por sus columnas**, no por el nombre del fichero. Los lee la API al
subirlos —no la noche— para que, si no es el fichero que tiene que ser, quien lo sube se entere en
el acto y con el motivo («le faltan columnas: …», «Columnas leídas: …»). Se guardan dos cosas en el
bucket de datos, en `externo/telemetria/<sistema>/`: el original tal cual en `originales/` (para
poder releerlo si cambian las reglas) y lo leído en `actual.json`, que es lo que usa la noche. El
último de cada sistema sustituye al anterior.

Los ficheros tienen sus rarezas, y el lector las conoce:

- **Nayax** trae un `styles.xml` que openpyxl no sabe abrir, y celdas sin referencia (`r="A1"`).
  El lector no usa estilos: las fechas vienen como texto (`14/10/2026 13:10:19`).
- **Prodelfi** llama a su hoja `sheet.xml` y no `sheet1.xml`; se busca por la relación del libro.
- **Nebula** es un CSV con BOM y una primera columna sin nombre.
- **Los grupos** se descargan como `.xls` pero son XML de Excel 2003.

Sin dependencias: va dentro de la Lambda de la API y de la de agregados, que no instalan nada.

## El cruce, con las reglas que se decidieron una a una

La noche cruza los ficheros con el censo de instalaciones de VenCloud, **entero** (si un final de
matrícula es único se mira en todo el parque, no en el trozo de un perfil). El cruce es por
matrícula (`24CE4790`), que es lo único que comparten los cuatro.

- **Nayax**: la matrícula del ID de operador o, si ahí no está, del nombre.
- **Prodelfi**: las filas **«Sin comunicación» no cuentan para nada** (Gabriele, 14-oct). La
  matrícula sale de la descripción, en tres pasos:
  1. completa (`NECTA 24CE4790`) y existe en VenCloud;
  2. tipo y número sin el año (`CE4507`, sobre todo RTVE);
  3. sólo cuatro cifras (`… 0777`), y nunca si la descripción ya trae una matrícula.

  En 2 y 3 se buscan las máquinas con ese final y se queda la del cliente del grupo: por el nombre
  del grupo (fichero de grupos) contra cliente y centro de VenCloud si se reconoce, o por estar en
  un centro donde ya hay otra máquina del grupo cruzada por matrícula completa. Si queda más de
  una, o ninguna, no se asocia. Los grupos 138–140 son «Radio Television» aunque se llamen de
  otra forma (`ALIAS`); la 17677 («155EO771») es la 15SE0771 (`MANUAL`).
- **Amazon ZAZ1 (centro 500013) y Amazon BCN4 Figueres (174003)**: todas sus máquinas llevan
  Prodelfi aunque la descripción no lo diga, **menos las cafeteras (CE), que no tienen sistema de
  pago** (`CENTROS_TODO_PRODELFI`).
- **Nebula**: la matrícula del nombre del dispositivo.
- **Una máquina con dos sistemas**: si el Nayax comunicó el día de la exportación, es de Nayax;
  si no, manda el otro (un Nayax callado en una máquina con Prodelfi no es el que tiene que mandar
  el dato).

Con los ficheros del 14 de octubre sale lo mismo que el listado hecho a mano: **2.504 máquinas
con telemetría** (Nayax 2.170, Prodelfi 304, Nebula 30) y las 334 del fichero de importación para
VenCloud, máquina a máquina. Lo que no se ha podido cruzar: 83 filas de Nayax, 130 de Prodelfi
(sólo las que son máquina: terminal vending, Summum, Imperium; los TPV y portales no) y 5 de Nebula.

## El cuadrado

Con ficheros, el universo son **las máquinas que tienen telemetría según los ficheros**, dentro
del ámbito del perfil. De ellas, cuántas mandaron ese día **venta por telemetría** a VenCloud y
cuántas su **DEX**. Las dos cifras viajan siempre; la grande (y el semáforo) es la venta
(`TELEMETRIA_PRINCIPAL` en `operativo.py`), con el DEX debajo. El 13 de octubre: venta 76,7 %,
DEX 38,8 %, las dos 37,8 %.

Sin ningún fichero subido, el cuadrado sigue como estaba (DEX sobre las máquinas del censo con
telemetría). Un perfil sin ninguna máquina en los ficheros lo dice («sin dato»), no da un cero.

## La página

El cuadrado lleva a `/telemetria/?dia=…`, con una pestaña por sistema y los cuatro análisis:

| pestaña | qué enseña |
|---|---|
| Nayax | máquinas con Nayax que ese día no mandaron venta, DEX o las dos, con la última comunicación que traía el fichero |
| Prodelfi | ídem, con el código de Prodelfi, su descripción y cómo se cruzó |
| Nebula (Coges) | ídem, con el dispositivo y su última venta |
| No están en VenCloud | lo que trae un sistema y no se ha podido cruzar con ninguna máquina instalada, con el motivo |

Cada pestaña filtra (sin venta o sin DEX, sin venta, sin DEX, ni una ni otra, todas), busca, y se
descarga en CSV. Para cada máquina sale el último día de la semana en que sí mandó; más atrás no se
guarda y se dice («antes del …»).

**Ojo con leer «sin venta» como «no transmite»**: un día sin venta puede ser un día sin ventas
(domingo, centro cerrado). El DEX no depende de que se venda. Por eso la página deja elegir el día
y enseña el último en que la máquina sí mandó.

## El ámbito

Como todo lo demás, se aplica al escribir: la noche escribe `cabina/<perfil>/telemetria.json` con
las máquinas de ese perfil, y `/api/telemetria` sirve el del perfil de la sesión, sin parámetro con
el que pedir otro. La página la ve quien ve el cuadrado (sesión de instalaciones, nivel de
operaciones o más). **Lo que está en un sistema y no en VenCloud no tiene centro**, así que no es
de ningún cliente: sólo sale en el perfil sin ámbito.

## Permisos

La API escribía hasta ahora sólo en DynamoDB. Para guardar los ficheros necesita `s3:PutObject`, y
**sólo en `externo/telemetria/*`** del bucket de datos, en su rol y en la frontera de la pila web.
`test_permisos.py` comprueba que no sea más que eso: un PutObject en todo el bucket le dejaría
pisar los paneles de cualquier perfil. La Lambda de agregados ya podía leer todo el bucket.
