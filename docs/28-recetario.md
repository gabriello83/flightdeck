# El recetario: 138 bebidas, 612 líneas

`M2 · EXT_MAESTRO_RECETAS`, sin parámetros. Y con esto el coste del café deja de ser una media y
pasa a ser calculable máquina a máquina.

---

## La clave: la receta no dice qué café, dice cuánto café

Cada línea es **una cantidad de un tipo de materia prima**, no de un artículo concreto:

```
R04 · Café con leche normal        R12 · Café con leche premium
  café en grano   8 g                café en grano   8 g
  azúcar          3 g                azúcar          3 g
  vaso            1 u                vaso            1 u
  paletina        1 u                paletina        1 u
  leche           8 g                leche           8 g
```

**Son idénticas.** El «premium» no es otra receta: es la misma receta con **otro café cargado en el
carril**, y con otro precio de venta. Eso confirma exactamente lo que decías —que el café normal,
premium o descafeinado puede variar, y que el precio va ligado a la selección— y además explica por
qué el coste no puede estar en la receta: **depende de la máquina**.

De ahí sale la fórmula del coste:

> **coste de una bebida en una máquina = Σ (cantidad de la receta × `puc` del artículo cargado en el
> carril de esa materia prima en esa máquina)**

La receta la da M2. El artículo cargado lo da **M1 · EXT_MAESTRO_CARRILES**. El `puc` lo da
`stocks.articulos`.

### Y el método está validado

Aplicando `puc` del inventario del A3 a la receta de R04: 8 g de grano a 7,24 €/kg = 0,058 € · 3 g
de azúcar a 1,235 €/kg = 0,004 € · vaso 0,017 € · paletina 0,004 € · 8 g de leche a 3,62 €/kg =
0,029 €. **Total 0,112 €.**

El A11 dice que R04 costó **0,098 €** de media en septiembre. Un 13 % de diferencia, que es
justamente lo que se espera cuando cada máquina lleva un café y una leche distintos. **El método
reproduce el coste real.**

## Cómo está compuesto el recetario

138 bebidas: 127 con código `R…` y 11 numéricas, que son la familia sin lactosa y tres con
asterisco. Entre 1 y 6 líneas por bebida.

| materia prima | recetas que la usan | cantidades |
|---|---:|---|
| Vaso | 132 | 1 u |
| Paletina | 131 | 1 u |
| Azúcar | 119 | 3 g, 5 g |
| Leche | 74 | de 3 a 25 g |
| **Café en grano** | **56** | 6, 8, 9, 10 g |
| Chocolate | 32 | hasta 25 g |
| **Cápsula** | **28** | 1 u |
| Soluble | 19 | — |
| **Café soluble** | **16** | 1, 1,5, 2 g |
| Infusión | 5 | — |

**Las tres tecnologías de café conviven**: 56 recetas de grano, 28 de cápsula y 16 de soluble. No
hay ninguna línea de `tipomateriaprima = 1`; el café siempre entra como grano (12), soluble (11) o
cápsula (8).

`precio_venta` viene a **0 en las 612 líneas**: la receta no lleva precio, el precio está en la
tarifa y en el canal, como ya sabíamos.

## Detalles que se ven leyendo el recetario

- **El cappuccino es café con leche más 1 g de chocolate.** R05 = R04 + chocolate. Explica que
  cappuccino y café con leche tengan costes casi iguales y precios distintos.
- **Hay dos descafeinados.** R17 lleva 1 g de café soluble; R71 a R77 llevan 8 g de grano. Son dos
  formas distintas de servirlo según la máquina, con costes muy distintos.
- **El chocolate va de 12 g (R30, con leche) a 25 g (R44, fuerte).** El «Chocolate fuerte» aparece
  dos veces, R44 y R61 — duplicado a revisar.
- **Las cápsulas no llevan línea de café**, sólo la cápsula: R54 es azúcar, vaso, paletina y
  cápsula. Y R65 a R70 son **sólo la cápsula**, sin vaso ni paletina: son las máquinas OCS donde
  el usuario pone su taza.
- **R53 «Solo Vaso»** y **R32 «Agua caliente»** existen como selecciones. Consumen vaso y paletina
  y no facturan casi nada, pero gastan.

## Entregable

[`carga/recetario_bebidas.xlsx`](../carga/recetario_bebidas.xlsx): las 138 bebidas en rejilla, el
detalle línea a línea, y el resumen por materia prima.

## Siguiente paso

**M1 · EXT_MAESTRO_CARRILES**, sin parámetros, que ya está escrito en el catálogo. Da, por máquina
y carril, el tipo de materia prima, el artículo cargado y su `puc`. Unas 7.600 filas.

Con M1 + M2 + el `puc` se calcula el coste real de cada selección en cada máquina, y con eso:

- costear la venta de café de **todo** el parque cruzando contra la telemetría, no sólo el 47 % que
  se lee por visita;
- comparar el coste de la misma bebida entre máquinas y ver dónde se está cargando café caro para
  venderlo a precio de normal;
- y cerrar de una vez el «43,7 % de ventas con coste conocido».
