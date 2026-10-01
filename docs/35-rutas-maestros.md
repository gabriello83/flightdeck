# Los maestros de ruta: vivos, pero configurados a medias

D1, D2, D3, D4 y D6, sin parámetros. Los cinco traen datos. Y el patrón que sale es el mismo que
ya vimos con el plan de carga: **la estructura está montada y sólo se rellena una parte**.

| informe | filas | rutas cubiertas |
|---|---:|---:|
| D1 · maestro de rutas | 161 | 161 (**92 activas**) |
| D2 · PDVs por ruta | 5.258 | **49** |
| D3 · criterios de visita | 4.019 | **44** |
| D6 · fondos fijos de vehículo | 7.794 | **34** |
| D4 · operarios asignados | 129 | 29 |

De 92 rutas activas, **49 tienen puntos de venta asignados, 44 tienen criterios de frecuencia y 34
tienen fondo fijo**. La configuración se va cayendo a cada nivel.

---

## 1. La ruta no tiene planificación horaria

En las **161 rutas**, sin una sola excepción:

| campo | valor |
|---|---|
| `hora_inicio` | `00:00` |
| `tiempo_ruta` | 0 |
| `min_visitas` / `max_visitas` | vacíos |

**No hay hora de salida, ni duración prevista, ni número de visitas objetivo.** Así que «ruta
planificada contra ruta real» no se puede medir, igual que pasaba con el plan de carga. Lo que sí
se puede es medir lo real: el D5 (jornadas) y la cabecera de visita dan horas y duraciones de
verdad.

128 de 161 tienen vehículo asignado; el resto lleva `xxxxxxx` de relleno. Sólo 3 rutas tienen
marcada visita en sábado y 1 en domingo — coherente con lo que ya medimos en recaudación, donde
los sábados no aparecen.

## 2. La regla de los 100 € en bolsa no está configurada en ninguna máquina

Esto es lo más importante del bloque.

`vending.rutasdetallecriterios` tiene los campos para gobernar la recaudación por máquina:
`criterio_recaudacion`, los siete días de la semana, y `limite_recaudacion`. Pues bien:

| campo | estado |
|---|---|
| `limite_recaudacion` | **0 en las 4.019 filas** |
| `criterio_recaudacion` | 0 en 3.962; sólo **57 máquinas** lo tienen |
| días de recaudación marcados | ninguno en 3.513 |

**La regla de recaudar por encima de 100 € en bolsa existe como norma y no está en el sistema en
ningún sitio.** Es exactamente el mismo hallazgo que ya salió en
[09-relleno-resultados.md](09-relleno-resultados.md) con `impminrecaudacion` y `actalarmasrentrec`
al 0 % en los 5.203 PDVs: **VenCloud trae el motor de alarmas de recaudación montado y nadie lo ha
configurado.**

No hay que construir nada nuevo para esa alarma. Hay que rellenar dos campos.

## 3. La frecuencia de visita sí está, en 3.011 máquinas

| días de visita a la semana | máquinas |
|---:|---:|
| 0 | **955** |
| 1 | 1.219 |
| 2 | 900 |
| 3 | 449 |
| 5 | 451 |
| resto | 45 |

**955 máquinas están asignadas a una ruta sin ningún día de visita marcado.** Un cuarto del total:
entran en la ruta pero no dicen cuándo. Y el reparto semanal —lunes 1.423, miércoles 1.401,
viernes 1.370, martes 1.311, jueves 1.274, sábado 58, domingo 14— confirma la semana de cinco días.

## 4. Una máquina, varias rutas

De las 5.252 asignaciones activas, **1.277 máquinas aparecen en más de una ruta activa**. Puede ser
legítimo —turno de mañana y de tarde, o ruta de fin de semana— pero es el 42 % del parque
asignado, que es mucho para ser sólo turnos. Merece una comprobación antes de usar la ruta como
dimensión de análisis, porque si una máquina cuelga de dos rutas, cualquier reparto de coste por
ruta la contará dos veces.

## 5. El fondo fijo del vehículo existe y es grande

7.794 líneas en 34 rutas y 543 artículos, con **1.856.347 unidades** de fondo teórico. 4.354 líneas
llevan `stock_limite` y 28 están bloqueadas.

Es el stock objetivo de cada furgoneta, y se puede contrastar contra el balance real del C9 —
569.796,62 € en vehículos— para ver qué rutas van por encima o por debajo de su fondo.

## 6. D4 no es la plantilla

129 asignaciones de 39 empleados a 29 rutas, con `desde` y `hasta` de uno o dos días. No es «quién
lleva cada ruta», son **sustituciones puntuales**. El titular está en D1 (`reponedor_titular`), y
quién hizo cada jornada de verdad está en D5 y en la cabecera de visita.

## 7. D5 da error: usar `select c.*`

`vending.rutascontrol`. El error es de validación, así que alguna de las columnas que puse no
existe —sospecho de `temperaturaini`, `coddispositivo` o las de GPS—. En vez de adivinar, el mismo
truco que funcionó con `prefacrecauda` y `auditmonbil`:

```sql
select c.*
from vending.rutascontrol c
where c.fechaini >= '{0}' and c.fechaini <= '{1} 23:59:59'
order by c.fechaini
```

Dos parámetros de fecha, 01/09 y 25/09. Devuelve los nombres reales de todas las columnas y con
eso se escribe el informe definitivo.
