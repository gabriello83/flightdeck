# El modelo de VenCloud, y qué se descarga cada noche

Esto es la especificación de la carga. Sustituye a cualquier lista anterior.

---

## 1. Cómo está organizado VenCloud

Nueve esquemas, y cada uno responde a una pregunta distinta:

| esquema | qué guarda |
|---|---|
| **`vending`** | la operación: la visita y sus hijas, rutas, puntos de venta |
| **`recursos`** | los activos: máquinas, sus canales y carriles, vehículos, empleados, almacenes |
| **`stocks`** | el género: artículos, recetas, los tres diarios de movimiento, traspasos, inventarios |
| **`comercial`** | clientes y centros |
| **`general`** | delegaciones |
| **`facturacion`** | la recaudación oficial y su desglose de IVA |
| **`sat`** | tareas técnicas, visitas, materiales y su log de eventos |
| **`telemetry`** | dispositivos y alarmas de máquina |
| **`configuracion`** | criterios de alarma, rentabilidad, catálogo SAT |

### La espina es `vending.partesvisita`

137 columnas y once tablas hijas colgando de `partevisitaid`. De ahí salen seis de las nueve áreas
del cuadro de mando. Todo lo que pasa en una máquina pasa por un parte.

### Y hay tres cadenas que cierran el círculo

1. **El género**: `diarmovalm` → `diarmovveh` → `diarmovmaq`. Enlazadas por id entre almacén y
   vehículo; entre vehículo y máquina el enlace no está relleno, pero las cuentas cuadran al
   dígito (6.271 + 1.822 = 8.093 en un día; 140.479 en el mes).
2. **El dinero**: `partesvisita` (bolsa) → `partesvisitaauditmonbil` (teórico) →
   `facturacion.prefacrecauda` (contado). Con un tramo ciego: la entrega a Loomis no se registra.
3. **El producto**: `maquinascanales` y `maquinascarriles` (planograma) → `articulosdetalle`
   (receta) → `articulos.puc` (coste). Es lo que permite costear el café máquina a máquina.

### Dos convenciones que hay que respetar siempre

- **«Sin referencia» es 0, no nulo.** Siempre `coalesce(campo,0) = 0`.
- **`01/01/1900` es el centinela de «nunca»** — sin cerrar, sin verificar, sin inventariar.

---

## 2. Las 30 tablas que se descargan

### Incrementales · se bajan cada noche por fecha

| tabla | informe | clave de fecha | filas/mes |
|---|---|---|---:|
| `vending.partesvisita` | A1 | `fechaini` | ~88.000 |
| `vending.partesvisitareposiciones` | A2 | madre | ~205.000 |
| `vending.partesvisitarecinventarios` | A3 | madre | ~1.000 |
| `vending.partesvisitaauditmonbil` | A7 | madre | ~200.000 |
| `vending.partesvisitaaudittubos` | A8 | madre | ~305.000 |
| `vending.partesvisitadevolclientes` | A10 | madre | ~200 |
| `vending.partesvisitaventas` | A11 | madre | ~188.000 |
| `facturacion.prefacrecauda` | B3 | **`fecha`** (escritura) | ~48.000 |
| `facturacion.prefacrecaudadetalle` | B4 | madre | ~78.000 |
| `stocks.diarmovalm` | C1 | `fecha` | ~73.000 |
| `stocks.diarmovveh` | C2 | `fecha` | ~147.000 |
| **`stocks.diarmovmaq`** | C3 | `fecha` | **~580.000** |
| `stocks.traspasosstock` | C4 | `fechacrea` | ~1.400 |
| `stocks.regularizacionesstock` | C5 | `fecha` | ~35 |
| `stocks.planesretornoprod` + detalle | C8 | `fechacrea` | ~1.400 |
| `stocks.infinventarioresumenes` | C9 | `fecha` | ~3.500 |
| `stocks.infinventarioelementosprods` | C10 | madre | ~50.000 |
| `vending.rutascontrol` | D5 | `fechaini` | ~1.500 |
| `sat.tareatecnica` | D7 | `fecha` | ~3.400 |
| `sat.tareatecnicaeventoslog` | D8 | madre | ~10.500 |
| `sat.tareatecnicavisita` | D9 | madre | ~1.700 |
| `sat.tareatecnicavisitamaterial` | D10 | madre | ~100 |

**~2 millones de filas al mes, unas 66.000 al día.** El 30 % es `diarmovmaq`, que va por
quincenas en la carga inicial y por día en la nocturna.

### Maestros · foto completa, se regeneran enteros

| tabla | informe | filas |
|---|---|---:|
| `vending.rutas` | D1 | 161 |
| `vending.rutasdetalle` | D2 | 5.258 |
| `vending.rutasdetallecriterios` | D3 | 4.019 |
| `vending.rutasoperarios` | D4 | 129 |
| `vending.rutasfondosfijos` | D6 | 7.794 |
| `configuracion.satoperaciones` | D11 | — |
| `recursos.maquinascarriles` | M1 | 15.088 |
| `stocks.articulosdetalle` | M2 | 612 |
| `recursos.maquinas` + `maquinascanales` | informe 77 / planograma | 4.498 / ~100.000 |
| `vending.pdvs`, `comercial.clientescentros`, `general.delegaciones`, `recursos.empleados`, `recursos.vehiculos`, `recursos.almacenes`, `stocks.articulos` | maestros de apoyo | pequeños |

Los maestros son pequeños y cambian poco: **una regeneración completa cada noche** es más simple y
más segura que un incremental, y no cuesta nada.

### Casos especiales

- **A3B y A3C** (cumplimiento y último inventario) no son tablas, son **vistas calculadas** sobre
  el histórico. Se regeneran enteras cada noche.
- **`vending.partesvisitadevolclientes`** lleva nombre y DNI: **va a un prefijo propio de S3 con
  acceso restringido** y no entra nunca en la consola de cliente.

## 3. Las once que NO se descargan

`partesvisitainvcanales` · `partesvisitacontajes` · `partesvisitacontajesdetalle` ·
`partesvisitaincidencias` · `recogidasbolsasrec` · `recogidasbolsasrecdetalles` ·
`pdvstransbancariasdetalles` · `partesvisitaauditcashlessgroups` · `planrecogida` +
`planrecogidadetalle` · `plancargarutavehiculo` + detalle

Diez están vacías y una (`plancargarutavehiculo`) la usa una ruta de 58. Si algún día se empiezan
a usar, el informe ya está escrito en el catálogo.

## 4. Reglas de la carga

1. **Toda fila lleva su `id`.** La carga es un *upsert* por id, así que repetir una noche no
   duplica nada.
2. **Las hijas de la visita se filtran por la fecha de la madre**, para que todas las tablas de una
   noche contengan el mismo conjunto de visitas y cuadren entre sí.
3. **Excepción: `prefacrecauda` va por su propia `fecha`**, la de escritura, porque el período
   contable se cierra semanas después. Para informes se agrupa por `anho`/`mes`, nunca por `fecha`.
4. **Un mes no está cerrado hasta el final del mes siguiente.** El mes en curso se marca como
   provisional y se mide con telemetría, no con `prefacrecauda`.
5. **Partición en S3 por `anio=/mes=/dia=`** sobre la fecha del informe, con una ventana de
   reproceso de tres días para recoger lo que llegue tarde.
