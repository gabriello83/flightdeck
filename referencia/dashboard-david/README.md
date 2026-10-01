# El cuadro de mando de David · AIRBUS San Pablo Sur

Guardado aquí como referencia para reproducir el perfil de AIRBUS. Dos ficheros:

- **`Dashboard_Servicio_Vending_SANPABLO.html`** — el original, 20,1 MB, con los datos dentro.
- **`plantilla-sin-datos.html`** — el mismo, 144 KB, con `EMBEDDED_DATA = null`. Es lo reutilizable:
  todo el código, ninguna cifra.

Generado el **11/09/2026**. Autocontenido: no carga ni una librería externa, lleva el logo de
Serunion en base64 y el mapa de España dibujado a mano. Accesible, con `aria-label` en cada panel.

---

## Qué alcance tiene

**Un solo centro: AIRBUS SAN PABLO SUR, 125 máquinas.** No es el cliente entero — nosotros tenemos
los nueve centros y 547 máquinas.

## Cómo se alimenta: arrastrando Excel

«Arrastra aquí todos los Excel». **Es una herramienta de carga manual**: se sueltan las
exportaciones y la página las procesa en el navegador. Ésa es la diferencia de fondo con lo que
estamos montando, que se alimenta solo desde S3.

Un fichero, `Dashboard filtrado.xlsx`, con cuatro hojas:

| hoja | filas | columnas |
|---|---:|---|
| **Ventas** | 244.789 | centro · máquina · fecha · artículo · unidades · importe |
| **Visitas** | 4.135 | fecha-hora · id · cod_pdv · ubicación · máquina · ruta · reponedor · vehículo · centro · cliente |
| **Averías** | 171 | fecha · nº · máquina · centro · ubicación · categoría · operación · estado · fecha cierre · técnico |
| **Preventivos** | 46 | estado · tipo · cod_pdv · ubicación · máquina · centro · técnico · fecha |

Más un censo de 125 máquinas con centro, matrícula y ubicación.

## Las catorce secciones

1. Indicadores clave (KPI grid, pulsables para filtrar)
2. Evolución diaria — con selector de métrica y de agrupación temporal
3. Mapa de centros — España peninsular y Baleares
4. Visitas realizadas por máquina
5. Mix de artículos
6. Incidencias por operación
7. Rendimiento por máquina
8. Detalle de incidencias
9. Máquinas sin venta
10. **Máquinas con venta inferior a 350 €/mes**
11. Máquinas por centro
12. Listado de visitas
13. Mantenimientos preventivos
14. Carga y estado de datos

---

## Lo que esto nos da

**Las cuatro hojas se corresponden una a una con informes que ya extraemos:**

| hoja de David | nuestro informe |
|---|---|
| Ventas | telemetría por máquina y artículo |
| Visitas | **A1** · cabecera de visita |
| Averías | **D7** con `tipo_tarea = 'A'` (23.577 en el año) |
| Preventivos | **D7** con `tipo_tarea = 'E'` (3.966 en el año) |

Es decir: **el cuadro de David se puede regenerar solo desde nuestro pipeline**, sin que nadie
arrastre un Excel, y para los nueve centros de AIRBUS en vez de uno.

Y el hallazgo de paso: el campo `tipo_tarea` del D7 separa **avería (A)** de **preventivo (E)**.
No lo habíamos interpretado, y es lo que hace falta para la sección 13.

## Lo que añadiríamos, y por qué

Su cuadro mide **venta, visita y avería**. Con lo que hemos medido, al perfil de AIRBUS le faltan:

- **Disponibilidad real** — máquinas mudas con la latencia de `criteriosalarmasnovtas`, no sólo
  «sin venta».
- **Surtido y planograma** — canales activos sin artículo o sin precio.
- **Frecuencia pactada contra real** — con los criterios del D3.
- **El umbral de 350 €/mes es suyo y hay que mantenerlo**: es una regla de negocio que no estaba
  en ningún sitio nuestro.

Lo que **no** lleva y hace bien en no llevar para un cliente: recaudación, stock y merma.
