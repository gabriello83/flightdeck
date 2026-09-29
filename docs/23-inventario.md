# El inventario de máquina: por qué el A3 no vale tal cual

`EXT_VISITA_INVENTARIO` lanzado sobre el 25/09/2026 devuelve **40 filas y 2 máquinas**, de 1.061
visitadas. No es un fallo del informe: el inventario no se hace en cada visita.

## La norma, y lo que sale de contrastarla

La regla de casa es doble:

1. **Inventario de todas las máquinas cada tres meses.**
2. **Inventario de la máquina antes de instalarla.**

Eso convierte al inventario en un **indicador de cumplimiento**, no en un dato de stock más. Y el
contraste es inmediato: el parque operativo son **3.200 máquinas** (informe 77), así que la norma
pide 3.200 inventarios por trimestre. Un trimestre tiene unos 63 días laborables:

| | inventarios/día laborable |
|---|---:|
| Lo que pide la norma | **~51** |
| Lo que hubo el 25/09 | **2** |

Un día no es una muestra, y hay que decirlo: puede que los inventarios se concentren en campañas
de fin de trimestre en vez de repartirse. Pero hay un segundo indicio que apunta a lo mismo. Los
`id` del 25/09 van del 207.179 al 207.218, o sea que la tabla lleva unas **207.000 líneas de toda
la historia**. A las 20 líneas por inventario que se ven ese día, son del orden de **10.000
inventarios en total** — y la norma pide 12.800 al año. Toda la historia de la tabla cabe en menos
de un año de cumplimiento.

La sonda A3Z lo cierra sin discusión: líneas e inventarios por mes. Si hay picos trimestrales, se
verán; si la línea es plana y baja, el incumplimiento es estructural.

**Esto deja de ser un problema de extracción y pasa a ser un indicador de la cabina.** El A3B
reescrito lo calcula: máquinas sin inventario, máquinas con el inventario caducado a más de 90
días, y máquinas instaladas sin inventario inicial.

## El diseño que sale de ahí

El inventario **no es un dato incremental por fecha, es un estado**: lo que importa de cada máquina
es su último inventario, sea de cuando sea.

- **A3** sigue en la carga nocturna, para ir trayendo los inventarios nuevos según se hacen.
- **A3B** (`EXT_INVENTARIO_CUMPLIMIENTO`) da una fila **por máquina del parque**, tenga inventario
  o no, con la fecha del primero, la del último y cuántos lleva. Arranca de `recursos.maquinas` y
  no de los inventarios, porque las máquinas que nunca se han inventariado son justo las que hay
  que ver y de otro modo no aparecerían.
- **A3C** (`EXT_INVENTARIO_ULTIMO`) da las líneas de ese último inventario. Es la foto de stock de
  la cabina, y se regenera entera cada noche.

Los tres están en [17-sql-extraccion-completa.md](17-sql-extraccion-completa.md).

## Lo que enseñan las 40 filas

Las dos máquinas son de tipología distinta, y eso ya confirma el corte del A2: `19CE1805` inventaría
**11 materias primas** de café (grano, cacao, azúcar, leche, vasos, paletinas, té, capuccinos) y
`12SE2020` inventaría **29 artículos** de snack y frío. Carriles y canales, sin mezcla.

**`cantidad` viene a 0 en las 40 filas**, y `stock_recomendado` también. Lo único relleno es
`capacidad_max` y `dif_capacidad`.

**Y `dif_capacidad` no es `capacidad_max − cantidad`.** En los artículos discretos coincide con la
capacidad (KIT KAT: capacidad 22, dif 22), pero en las materias primas es fraccionaria:

| artículo | capacidad_max | cantidad | dif_capacidad |
|---|---:|---:|---:|
| CACAO SOLUBLE TEYCOVAL | 4 | 0 | **3,6** |
| AZUCAR 1KG | 4 | 0 | **3,5** |
| PALETINAS MADERA 90MM | 550 | 0 | 550 |
| VASO PAPEL 6OZ | 650 | 0 | 650 |

Si fuera una resta daría 4 y 4. Da 3,6 y 3,5, o sea que el sistema sabe que quedan 0,4 kg de cacao
y 0,5 kg de azúcar. Lectura provisional: **`cantidad` es lo que teclea el reponedor** (aquí no
contó nada, de ahí el 0) y **`dif_capacidad` es lo que falta para llenar según el stock teórico**
del sistema.

Con dos máquinas no se puede cerrar la interpretación. Se cierra con el A3C, que trae el último
inventario de todo el parque: si ahí `cantidad` también viene mayoritariamente a 0, el campo no se
usa y el stock hay que deducirlo de `dif_capacidad`.

## Y el inventario por canal (A4) está vacío

`EXT_VISITA_INVCANALES` sobre el 25/09 devuelve **0 filas**. No es un error: el informe se ejecuta
y no hay nada. Y el mismo día sí hubo dos inventarios por artículo.

O sea que `partesvisitarecinventarios` y `partesvisitainvcanales` **no son complementarias**: el
inventario se guarda en una o en la otra, según el flujo o el dispositivo. Con un día no se sabe
si la segunda está muerta del todo o sólo poco usada, y de eso depende una cosa importante: si no
hay inventario por canal, **la rotura de stock por canal no se puede medir con datos de visita**.

Las dos sondas A3Z y A4Z resuelven la duda de un tiro: una fila por mes sobre cada tabla.

**Si A4 resulta estar muerta**, el camino alternativo ya lo tenemos y no depende del inventario:
`maquinascanales` da el planograma y el stock recomendado por canal, el A2 da lo que se repone en
cada canal y con qué frecuencia, y la telemetría da lo que se vende. Canal que se repone al tope
en cada visita es canal que se está quedando vacío entre visitas.

## Escala

Los `id` del 25/09 van del 207.179 al 207.218. La tabla lleva ~207.000 líneas **de toda la
historia**, contra los 4,7 millones de reposiciones. A ~30 líneas por inventario son unos 7.000
inventarios en total, repartidos entre unas 2.000 máquinas: **tres o cuatro inventarios por máquina
en toda su vida**.

Por eso el A3C debería devolver del orden de 50.000–60.000 filas, y por eso conviene lanzar antes
el A3B, que es pequeño y ya dice cuántas máquinas tienen inventario y de qué antigüedad.
