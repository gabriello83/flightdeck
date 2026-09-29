# Los tres diarios de stock, 25/09/2026

C1, C2 y C3 lanzados sobre un solo día. Los tres vivos, y la cadena cuadra.

| informe | filas en un día | proyección a 25 días |
|---|---:|---:|
| C1 · almacén | 2.922 | ~73.000 |
| C2 · vehículo | 7.325 | ~183.000 |
| **C3 · máquina** | **25.056** | **~626.000** |

C1 y C2 entran de una vez en el mes. **C3 hay que partirlo por semanas.**

---

## 1. La cadena cuadra, aunque le falte un enlace

Lo que sí está enlazado por identificador:

| enlace | filas | casan |
|---|---:|---:|
| C1 → C2 (`mov_vehiculo_id`) | 880 | **880** |
| C2 → C1 (`mov_almacen_id`) | 880 | **880** |
| **C3 → reposición (`reposicion_id`)** | **8.187** | **8.187** |

**Las 8.187 líneas de reposición del A2 están las 8.187 en C3, y no falta ninguna.** Los motivos
coinciden uno a uno: CM 8.093, RC 58, RM 28, RR 8. La correspondencia es total.

Y lo que **no** está enlazado: `mov_maquina_id` viene nulo en las 7.325 filas de C2, y
`mov_vehiculo_id` nulo en las 25.056 de C3. **El eslabón vehículo → máquina no tiene clave.**

Pero la cadena no está rota, sólo hay que reconstruirla contando:

```
C2 carga a máquina (CM)      6.271
C1 carga directa (CM)      + 1.822
                           -------
                             8.093   =   C3 motivo CM: 8.093
```

**Exacto.** 6.271 cargas salen del vehículo y 1.822 van directas del almacén a la máquina. Sumadas
dan justo las líneas de carga de máquina. Así que la trazabilidad completa se puede reconstruir
por artículo, fecha y ruta, aunque no haya `id` que seguir.

## 2. La merma estaba medida a la mitad

Veníamos midiendo caducidad y rotura sólo en la máquina, desde las líneas `RC`/`RR` del A2. Los
diarios enseñan que **se tira producto en los tres eslabones**:

| eslabón | caducidad | rotura | retirada |
|---|---|---|---|
| Almacén | 6 líneas · 9,46 € | 2 · 1,80 € | 23 · 86,21 € |
| **Vehículo** | **52 líneas · 95,49 €** | 6 · 6,62 € | 5 · 14,10 € |
| Máquina | 58 líneas · 104,96 € | 8 · 8,43 € | 28 · 100,31 € |
| **TOTAL DÍA** | **116 líneas · 209,91 €** | **16 · 16,85 €** | **56 · 200,62 €** |

**La caducidad real del día es el doble de lo que decíamos**: 209,91 € contra los 104,96 € que se
ven desde la máquina. Casi todo lo que falta se tira en el vehículo, y eso sólo se ve aquí.

Proyectado a 19 días laborables, unos **4.000 € al mes de caducidad**, la mitad de ellos en
furgoneta. Es poco dinero, pero es un indicador de planificación de carga: producto que sube al
vehículo y no llega a venderse.

Nota de método: el A2 valoraba la caducidad en 85,26 € con `precio_coste`, y aquí sale 104,96 €
con `puc`. Son dos bases de coste distintas. **Para merma hay que usar `puc`**, que es el coste de
reposición, y decirlo en el cuadro de mando.

## 3. C3 también registra las ventas, con su coste

16.829 filas de tipo `VEN`: 12.400 unidades y **6.852,53 € de coste** en 636 máquinas.

No cubre el parque —la telemetría vio 54.139 transacciones y 1.917 máquinas ese día—, así que son
un tercio de las máquinas y un 23 % de las unidades. Pero es **coste de venta real, artículo a
artículo**, y complementa a la telemetría en lugar de repetirla: son las máquinas cuyo stock se
lleva por unidad.

241 de esas filas traen `puc` a cero, el mismo agujero de los artículos sin coste.

## 4. Detalles de uso

- **Los tipos de movimiento son distintos en cada diario.** C1: `CM`, `SV`, `CO`, `IN`, `RM`,
  `SA`, `EA`, `RC`. C2: `CM`, `EA`, `RE`, `RC`, `OR`, `RR`, `RM`, `SA`. C3 sólo tres —`VEN`,
  `MOV`, `INV`— y el detalle va en `motivo`. **En C3 hay que agrupar por `motivo`, no por
  `tipo_mov`.**
- `dif_inventario` marca 24 filas en C1 y 40 en C3 — estas últimas son exactamente el inventario
  de las dos máquinas del día, así que el campo señala las regularizaciones por recuento.
- Valor movido en un día: **46.904,41 € en almacén** (22 almacenes) y **48.876,78 € en vehículo**
  (38 vehículos).
- Los traspasos llevan documento legible —«Traspaso: 41969 - 25/09/2026»— y `origen_destino` dice
  la contraparte («Vehículo: 9763NCJ»). Se puede auditar sin joins.

## 5. Fechas para el mes

- **C1 y C2**: 01/09/2026 – 25/09/2026 de una vez.
- **C3**: por semanas — 01–07, 08–14, 15–21, 22–25. Cuatro lanzamientos de unas 150.000 filas.
