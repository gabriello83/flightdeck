# Flightdeck

Cuadro de mando del servicio de vending de **AIRBUS**, planteado como la cabina de un
avión: instrumentos siempre a la vista, lecturas primarias grandes, alertas por severidad
y sin tener que navegar para saber si algo va mal.

El servicio lo presta Serunion y se gestiona en VenCloud (ERP de EAC Software), de donde
salen los datos.

## Estado

Fase de datos terminada. Hay un conjunto consolidado de mayo a agosto de 2026 —
**1.124.774 líneas de venta, 778.370,65 €, 549 máquinas, 7 centros**— y un análisis
exploratorio que ya ha dado hallazgos accionables. Falta construir la aplicación.

| Documento | Contenido |
|---|---|
| `docs/01-datos.md` | Fuentes, tablas consolidadas y límites del dato |
| `docs/02-analisis-exploratorio.md` | Qué da de sí el dato y qué se ha encontrado |
| `docs/03-vencloud-api.md` | Qué hace falta para integrar la API de VenCloud |

## Datos

```bash
python3 scripts/prepare_data.py   # data/raw/ -> data/processed/
python3 scripts/analisis.py       # informe exploratorio por consola
```

Los ficheros de origen viajan comprimidos en `data/raw/` y el preparador los lee tal cual,
así que el repositorio es autosuficiente: clonar y ejecutar reproduce las tablas.

## Hallazgos que marcan el diseño

- **El día de la semana manda**: el viernes vende un 28% menos que el martes y el fin de
  semana es un 6% de un día laborable. Nada se compara contra "ayer", sino contra el mismo
  día de la semana anterior.
- **Máquinas mudas**: 61 máquinas pasaron 3 o más días laborables seguidos sin vender nada
  entre mayo y julio, 594 días en total, y casi ninguna tenía incidencia abierta. Es la
  alerta principal de la cabina.
- **Rutas desequilibradas**: de 0,2 € a 617 € por visita; seis máquinas recibieron 55
  visitas sin vender nada.
- **La mitad de las incidencias no son averías**: 276 de 785 son devoluciones de dinero.
- **El servicio técnico responde mejor de lo que parecía**: el 58% de las incidencias se
  cierra el mismo día, pero un 9% tarda más de una semana.

Todo está desarrollado, con cifras y advertencias, en `docs/02-analisis-exploratorio.md`.

## Siguientes pasos

1. Pantalla de cabina: KPIs contra el mismo día de la semana anterior, alerta de máquinas
   mudas, incidencias abiertas y SLA.
2. Ficha de máquina: serie diaria de venta con visitas, averías y preventivos superpuestos.
3. Paneles de operación (rutas y reponedores), calidad de servicio (incidencias y
   devoluciones) y surtido (Pareto, cola larga y precios por centro).
4. Sustituir la carga manual por la ingesta desde la API de VenCloud, en cuanto haya
   credenciales. Pendiente de EAC Software o de sistemas de Serunion.

## Pendiente de pedir

- Que el informe de ventas **incluya la hora**: solo vino en el fichero de agosto y es lo
  que abre el análisis por franja horaria.
- Censo completo de máquinas (hoy solo hay ubicación de las 125 de San Pablo Sur, de 549).
- Medio de pago, planograma y capacidad, coste de compra, y el calendario laboral de cada
  centro.
