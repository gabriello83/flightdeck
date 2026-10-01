# M1 · Los carriles, y la decisión sobre cómo costear el café

15.088 carriles, 1.498 máquinas. Es la otra mitad del recetario: M2 dice **cuánto**, M1 dice **de
qué**.

---

## Decisión tomada: el coste va por máquina, no por media

> «Se tendrá que hacer una media de los precios de cada receta o se los calcula en base al precio
> del café que está en determinada máquina, mejor.»

**Por máquina.** Y los datos lo respaldan sin discusión: hay **13 cafés en grano distintos, de 5,99
a 22,176 €/kg**.

| café en grano | carriles | €/kg |
|---|---:|---:|
| CAFE GARIBALDI ESPRESSO BAR 1000GR | 635 | 7,28 |
| CAFE GRANO ROBUSTA 1KG | 610 | 7,89 |
| CAFÉ WALNUT NATURAL TUESTE ESP | 226 | 6,26 |
| CAFÉ TORELLI PIACERE | 167 | 16,29 |
| CAFÉ TORELLI ALLEGRIA | — | 14,70 |
| CAFE SALZILLO GRANO DESCAFEINADO | — | 22,18 |
| CAFE LIOF NATURAL 250G | — | 5,99 |

Traducido a los 8 g que pide la receta, y por máquina:

| | coste de 8 g |
|---|---:|
| Percentil 10 | 0,0501 € |
| Mediana | 0,0582 € |
| Percentil 90 | 0,1274 € |
| Máximo | 0,1774 € |

**Un café con leche cuesta 3,5 veces más en unas máquinas que en otras**, y al cliente se le cobra
lo mismo. Una media nacional taparía justo eso, que es el hallazgo.

## Pero no hay que recalcularlo desde los gramos

Hay un obstáculo práctico: **el `puc` es por envase, y el tamaño del envase sólo está en el
nombre** — «CAFE GARIBALDI ESPRESSO BAR **1000GR**» a 7,28 frente a «CAFE GRANO TUESTE INTENSO
**500G**» a 15,92. Sacar el €/g exigiría leer el nombre, que es frágil y se rompe con cada alta
nueva.

No hace falta, porque **el A11 ya trae `coste_unitario` calculado por VenCloud, parte a parte**, y
lo validamos: la receta de R04 con `puc` da 0,112 € y el A11 dice 0,098 €. Así que:

1. **Para las 766 máquinas que se leen por visita**, el coste por selección sale directo del A11.
   Es dato real, no estimación.
2. **Para el resto del parque**, se toma el coste que el A11 observa en máquinas **que llevan el
   mismo café** —eso lo dice M1— y se aplica. Es una imputación con fundamento, no una media.
3. **M1 + M2 quedan como la explicación y el control**: por qué una máquina cuesta más, y qué
   pasaría si se cambiara el café cargado.

Eso convierte el «43,7 % de ventas con coste conocido» en cobertura prácticamente total, y sin
depender de parsear nombres de artículo.

## El resto de materias primas, para dimensionar

| materia | artículos distintos | rango de `puc` |
|---|---:|---|
| Café en grano | 13 | 5,99 – 22,18 |
| Café soluble | 3 | 4,64 – 7,64 |
| Cápsula | 12 | 0,002 – 0,442 |
| **Leche** | 7 | 0,051 – **10,52** |
| Chocolate | 3 | 3,28 – 3,85 |
| Vaso | 10 | 0,014 – 0,043 |
| Paletina | 6 | 0,004 – 0,016 |
| Azúcar | 9 | 0,010 – 1,229 |

El chocolate es casi uniforme y las paletinas dan igual. **Donde se juega el coste es en el café y
en la leche**: la leche de avena a 10,52 contra el preparado lácteo básico a 1,81 es seis veces
más cara, y va en la misma receta.

## Tres cosas a limpiar que salen del maestro

- **844 carriles sin artículo asignado** y 919 con `puc` a cero. Esos no descuentan stock ni suman
  coste.
- **222 carriles declarados como `tipomateriaprima = 1` (café genérico) y todos vacíos**, en 94
  máquinas. Ninguna receta consume el tipo 1 —el café entra siempre como grano (12), soluble (11)
  o cápsula (8)—, así que son plazas muertas. **17 de esas máquinas no tienen ningún otro carril
  de café**: o no sirven café, o están mal configuradas.
- `virtual` viene a `false` en las 15.088 filas: campo sin usar. `extra` es `true` en 258.
