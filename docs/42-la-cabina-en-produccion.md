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

## Lo que todavía no se puede usar

**Los euros de merma.** Las líneas cuadran —6.092 de caducidad en el periodo, ~1.600 al mes contra
las 1.154 medidas en septiembre— pero la valoración sale a **3,38 € por unidad** cuando el cuaderno
de septiembre daba 0,63. Siete veces más. Dos hipótesis: que `puc` sea precio por envase y no por
unidad (es una trampa ya documentada para el café), o que en septiembre el campo estuviera vacío en
los artículos que más caducan. **No distinguibles sin mirar el crudo.** Hasta entonces, las líneas
de merma sirven; los euros, no.

Y siguen abiertas de antes: el signo de `dif_inventario`, las 1.277 máquinas en más de una ruta
activa, y los costes de los 59 artículos frescos de marca propia.
