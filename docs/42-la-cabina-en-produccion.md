# La cabina en producción · 02/10/2026

El sistema está corriendo. VenCloud → S3 → agregados → panel, sin intervención, en una cuenta de
AWS creada para esto y separada de todo lo demás.

## Lo que hay dentro

120 días, del **4 de junio al 1 de octubre de 2026**, sin un solo día ausente.

| | |
|---|---:|
| partes de visita leídos | 377.599 |
| **visitas reales** | **94.053** |
| máquinas | 3.114 |
| centros | 429 |
| tareas de SAT sobre máquina real | 9.345 |
| jornadas de ruta | 5.689 |
| recaudación, cuatro periodos contables | jun–sep |

La carga nocturna tarda unos **90 segundos** y los agregados **84**.

## La comprobación que importa

Durante la campaña sacamos cifras a mano, informe a informe, con el motor de informes de VenCloud.
La cabina las calcula ahora sola, por otro camino —API, S3, Lambda— y con otro código. **Coinciden
al céntimo.**

| agosto de 2026 | la cabina | medido a mano en la campaña |
|---|---:|---:|
| registros de recaudación | 48.443 | 48.443 |
| efectivo | 428.003,41 € | 428.003,41 € |
| total con banco | 965.283,49 € | 965.283,49 € |
| efectivo sin telemetría | 122.327,35 € | 122.327,35 € |

Y lo que no es una igualdad exacta, porque son ventanas distintas, cae donde debe: mediana de
visita **6,52 min** contra los 6,80 del 25 de septiembre, GPS **51,5 %** contra 50,9 %, matrícula
ficticia **23,5 %** contra 24 %.

El patrón semanal sale solo del dato, sin que nadie se lo haya dicho:

| lunes | martes | miércoles | jueves | viernes | sábado | domingo |
|---:|---:|---:|---:|---:|---:|---:|
| 1.086 | 996 | 1.069 | 1.009 | 1.058 | **173** | **82** |

## Dos errores que encontró el propio sistema

**Junio daba −7.521.760.075,56 € de efectivo.** Una sola fila corrupta, cuando una recaudación
media son 8,80 €. Las filas con importes imposibles se apartan **y se cuentan**: junio publica
ahora 469.652,69 € con un `filas_imposibles: 1` y su nota al lado. Apartarlas en silencio habría
cambiado un número absurdo —que se ve— por uno plausible y falso, que no.

**Y uno mío, de semanas atrás.** [33-tanda-c-resultados.md](33-tanda-c-resultados.md) publicaba
**8,29 M € de existencias**. Son nueve meses de cierres mensuales sumados: la cifra real del
cierre de agosto es **912.923,87 €**, un noveno. Se delataba en mi propia tabla —30.493 elementos
de tipo M cuando el parque son 3.161 máquinas— y yo había escrito dos párrafos más abajo «~3.300
elementos valorados al mes» sin ver lo que implicaba.

Las dos cosas las destapó tener el dato puesto al lado de lo que ya sabíamos. Es exactamente para
lo que sirve una cabina.

## Los euros de merma: resuelto, y no era un fallo

Me preocupaba que la caducidad del periodo saliera a 9,96 € por línea cuando el cuaderno de
septiembre daba 2,06. Bajamos un día de crudo —`stock_maquina` del 15/08— y la duda se cierra:

| | € por línea de caducidad |
|---|---:|
| 15 de agosto, del crudo | 2,00 € |
| septiembre, medido a mano | 2,06 € |
| el periodo entero, en el panel | 9,96 € |

**El método de valoración es correcto**: el día suelto y septiembre coinciden. Lo que cambia es
**qué** se caduca. El `puc` de ese día tiene mediana 0,63 € y máximo 23,32:

| puc | artículo |
|---:|---|
| 0,63 | un snack |
| 16,87 | CAFÉ TORELLI PIACERE |
| 22,18 | CAFÉ SALZILLO GRANO DESCAFEINADO |
| 23,32 | CAFÉ SOLUBLE LIOFILIZADO DESCAFEINADO |

**Un envase de café cuesta 35 veces lo que un snack.** Un mes en el que se retire café caducado
parece un desastre con exactamente las mismas líneas que uno en el que no. Por eso el panel publica
ahora `merma.caducidad_por_articulo`, con los 25 primeros por euros y su coste por unidad: el total
en euros no se puede leer sin ese desglose.

Y de paso, `puc` es igual a `precio_coste` en este informe (la razón es 1,00 en el p10 y en el p90),
así que no hay ninguna duda de qué campo usar.

### `dif_inventario` en la máquina: no se usa

De las 9.314 filas del día, **ninguna** lleva la marca. Los 1.257 movimientos de almacén y 581 de
vehículo que vimos en [32-diarios-de-stock.md](32-diarios-de-stock.md) son de C1 y C2: el descuadre
se marca en los diarios de almacén y vehículo, no en el de máquina. La pregunta del signo sigue
abierta, pero ya sabemos dónde no hay que buscarla.

## Lo que sigue abierto

Las 1.277 máquinas en más de una ruta activa, los costes de los 59 artículos frescos de marca
propia, y el signo de `dif_inventario` en los diarios de almacén y vehículo.
