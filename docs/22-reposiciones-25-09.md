# Las líneas de reposición, 25/09/2026

Extracción `EXT_VISITA_REPOSICIONES` (bloque A2). **8.187 filas, 2 segundos.** Cuadra con la
cabecera del A1 en los cuatro contadores y en el importe, sin una sola diferencia por parte.

---

## 1. El cuadre, exacto

| comprobación | A2 | A1 | partes descuadrados |
|---|---:|---:|---:|
| unidades `CM` ↔ `cal_cm` | 154.312 | 154.312 | **0** |
| unidades `RC` ↔ `cal_rc` | 163 | 163 | **0** |
| unidades `RM` ↔ `cal_rm` | 169 | 169 | **0** |
| unidades `RR` ↔ `cal_rr` | 28 | 28 | **0** |
| coste `RC` ↔ `cal_impcostecaducidad` | 85,26 € | 85,26 € | **0** |
| coste `RR` ↔ `cal_impcosterotura` | 8,42 € | 8,42 € | **0** |
| `CM − RC − RM − RR` ↔ `cal_impcarga` | 29.265,01 € | 29.265,13 € | **0** |

1.064 partes con línea, **0 huérfanos** y **0 partes del sistema**. Confirmado: los partes
automáticos no mueven producto, sólo leen máquina.

43 visitas reales no cargaron nada. Mediana de **5 líneas por visita**, media 7,7, máximo 52.

## 2. Tres cosas que sólo se ven cruzando las dos tablas

**`cal_cm` son unidades brutas.** Confirmado: 154.312 exactas, parte a parte. Renombrado bien.

**`cal_impcarga` es carga NETA.** No es el valor de lo que se mete, es lo que se mete menos todo
lo que se saca: `CM − RC − RM − RR`. Los 34 partes que parecían descuadrar eran exactamente los
que tenían retirada. Para «valor cargado» hay que sumar las líneas `CM`, no leer el campo.

**Qué son RC, RM y RR.** `RC` alimenta el coste de caducidad y `RR` el de rotura, exactos los dos.
`RM` no alimenta ningún campo de coste de la cabecera — los 94,80 € no aparecen en ninguna parte,
aunque sí se restan de la carga. Lectura: `CM`/`RM` son el par cargar/retirar de máquina, y
`RC`/`RR` son las dos retiradas con pérdida. `RM` no tiene campo de coste porque **no es pérdida**:
el producto vuelve al almacén. Queda por confirmar con la tabla de devoluciones.

## 3. Las unidades engañan: dos de cada tres son consumibles de café

1.263 líneas (95.108 unidades, 5.547,86 €) vienen **sin `etiq_canal`**: azúcar, paletinas, vasos,
café en grano, cápsulas, leche. Son carriles de máquina caliente, no canales.

| | unidades | coste | € por unidad |
|---|---:|---:|---:|
| Con canal (producto vendible) | 59.564 | 24.094,10 € | 0,405 |
| Sin canal (consumible de café) | 95.108 | 5.547,86 € | 0,058 |

**El 62 % de las «unidades cargadas» son sobres de azúcar y paletinas.** Cualquier indicador de
unidades tiene que separar las dos cosas o no dice nada.

Y la separación es limpia: **282 máquinas sólo carriles, 738 sólo canales, 0 mixtas**. Las dos
tablas de planograma no se solapan nunca en la misma máquina.

## 4. `etiq_canal` es la etiqueta del planograma, y `cod_canal` no sirve

`cod_canal` vale 0 en 1.679 filas. `etiq_canal` trae la etiqueta buena, y no siempre es numérica:

| formato | filas |
|---|---:|
| numérica (`11`, `44`, `61`) | 6.073 |
| `V##` | 502 |
| `A##` | 176 |
| `VI###` | 117 |
| dos letras (`DC`, `EA`, `FA`, `EF`…) | ~20 |

Confirma la regla de [19-precio-y-planograma.md](19-precio-y-planograma.md): se cruza por
`etiqueta`, nunca por `numero`, y el campo es **texto**, no entero.

## 5. Hallazgo: 59 artículos se cargan sin coste

379 líneas de carga con `precio_coste = 0`: **3.824 unidades, el 2,5 % de lo cargado, en 188 de
los 1.064 partes**. 59 referencias distintas, y la mayoría son los frescos de marca propia —
Ñaming Go!, Ñaming Delicious, Ñaming Brioche, LM Croissant, LM Bloomer — más vasos, paletinas y
alguna cápsula.

De esas referencias **no se puede calcular margen**: entran a coste cero, así que el beneficio
sale inflado justo en la familia de mayor precio de venta. Hay que pedir que se carguen los costes
de los frescos en `stocks.articulos`.

## 6. Lo que esto desbloquea

Con A1 + A2 ya se puede calcular, por máquina y por mes:

- carga bruta valorada y carga neta,
- caducidad y rotura en euros, con el artículo y el canal exactos,
- coste de servicio (visitas × 8 €),
- y por tanto **margen real por máquina**, en cuanto se resuelvan los costes que faltan.

Lo que falta para cerrar el círculo es el inventario (A3/A4): con carga y venta pero sin stock
inicial no se puede medir la rotura de stock por canal.
