# El inventario de máquina: por qué el A3 no vale tal cual

`EXT_VISITA_INVENTARIO` lanzado sobre el 25/09/2026 devuelve **40 filas y 2 máquinas**, de 1.061
visitadas. No es un fallo del informe: el inventario no se hace en cada visita.

Eso obliga a cambiar el diseño. El inventario **no es un dato incremental por fecha, es un estado**:
lo que importa de cada máquina es su último inventario, sea de cuando sea.

- **A3** sigue en la carga nocturna, para ir trayendo los inventarios nuevos según se hacen.
- **A3B** (`EXT_INVENTARIO_ANTIGUEDAD`) da una fila por máquina con la fecha del último inventario.
  Es el que dice si el dato sirve o está muerto.
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

## Escala

Los `id` del 25/09 van del 207.179 al 207.218. La tabla lleva ~207.000 líneas **de toda la
historia**, contra los 4,7 millones de reposiciones. A ~30 líneas por inventario son unos 7.000
inventarios en total, repartidos entre unas 2.000 máquinas: **tres o cuatro inventarios por máquina
en toda su vida**.

Por eso el A3C debería devolver del orden de 50.000–60.000 filas, y por eso conviene lanzar antes
el A3B, que es pequeño y ya dice cuántas máquinas tienen inventario y de qué antigüedad.
