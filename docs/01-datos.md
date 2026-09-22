# Fuentes de datos

Periodo disponible: **mayo – agosto 2026**. Siete centros con ventas; Puerto Real
aparece en visitas, averías y preventivos pero no tiene ventas.

## Ficheros de origen (`data/raw/`, no versionados)

| Fichero | Contenido |
|---|---|
| `ventas.csv` | 1.040.702 líneas de venta, may–ago, todos los centros **salvo agosto de Getafe, Illescas y Albacete**. Separador `;`, coma decimal, fecha sin hora. |
| `ventas_agosto_getafe_illescas_albacete.xlsx` | 84.085 líneas: el agosto que falta en el CSV, con hora. Su último día de julio se descarta al consolidar porque ya viene en el CSV. |
| `visitas.xlsx` | 16.017 visitas de reposición, may–ago, 8 centros. |
| `averias.xlsx` | 785 tareas técnicas, may–ago, 24 columnas (modelo, tipo de máquina, técnico, cierre). |
| `preventivos.xlsx` | 463 mantenimientos preventivos, ene–sep. |
| `dashboard_david_sanpablo.html` | Dashboard de referencia de David Alonso. Lleva 20 MB de datos incrustados (solo San Pablo Sur) y de ahí sale el censo de máquinas con ubicación. |

## Tablas consolidadas (`data/processed/`)

`scripts/prepare_data.py` normaliza todo a CSV UTF-8 comprimido, con fechas ISO y
punto decimal:

| Tabla | Filas | Columnas |
|---|---|---|
| `ventas.csv.gz` | 1.124.774 | centro, maquina, fecha, hora, articulo, cantidad, importe |
| `visitas.csv.gz` | 16.017 | centro, maquina, fecha, hora, pdv, ubicacion, ruta, empleado, vehiculo, id |
| `averias.csv.gz` | 785 | centro, maquina, fecha_alta, hora_alta, fecha_cierre, horas_resolucion, numero, modelo, tipo_maquina, ubicacion, categoria, operacion, estado, tecnico |
| `preventivos.csv.gz` | 463 | centro, maquina, fecha, hora, pdv, ubicacion, operacion, estado, realizada_por |
| `censo_maquinas.csv` | 125 | centro, maquina, ubicacion (solo San Pablo Sur) |

Ventas consolidadas: **778.370,65 €** y 1.124.774 unidades.

| Centro | may | jun | jul | ago | Importe |
|---|---:|---:|---:|---:|---:|
| Getafe | 143.742 | 167.692 | 137.932 | 60.988 | 350.910,09 € |
| San Pablo Sur | 68.964 | 71.328 | 67.691 | 36.806 | 187.074,12 € |
| Illescas | 28.903 | 28.579 | 25.472 | 11.266 | 62.271,71 € |
| Tablada | 27.002 | 26.751 | 27.941 | 10.503 | 60.593,64 € |
| CBC | 25.814 | 28.332 | 24.862 | 9.247 | 55.893,98 € |
| Albacete | 20.374 | 18.203 | 17.400 | 11.818 | 42.368,64 € |
| San Pablo Norte | 7.514 | 7.711 | 7.814 | 4.125 | 19.258,47 € |

La caída de agosto es real: coincide con el parón de verano, y los fines de semana
bajan a unas 200 líneas diarias en todos los centros.

## Cosas a tener en cuenta

- Cada línea de venta es **una unidad** (`cantidad` siempre 1); para volumen hay que contar filas o sumar.
- Solo el fichero de agosto trae **hora**; el resto de ventas es a nivel de día. Un análisis por franja horaria solo es posible en ese mes.
- El censo con ubicación legible solo cubre San Pablo Sur. Para los demás centros la ubicación hay que sacarla de visitas o averías.
- `denominacentro` (averías) y `Centro` (resto) usan los mismos nombres, así que cruzan bien. `maquina` es la clave común entre todas las tablas.

## Cómo regenerar

```bash
python3 scripts/prepare_data.py
```
