# Integración con VenCloud

## Qué es VenCloud

VenCloud es el ERP de vending de **EAC Software / Macrosistemas**. Serunion —el operador
que presta el servicio en los centros de Airbus, y que aparece como cliente
`10002-SERUNION, SA` en todas nuestras tablas— trabaja con la versión VenCloud PRO.

## La API de WebReports externos

Servicio WCF que publica los informes de VenCloud por número. **Todos los parámetros van
en la ruta**: ni query string ni cuerpo.

```
POST {endpoint}/GetReportV2/{token}/{empresa}/{informe}[|filtro1|filtro2...]
```

| | |
|---|---|
| Endpoint | `https://vencloudpro.eac.es/2311_api/webservices//VenCloudExternalApi/VenCloudExternalApi.svc` |
| Empresa | `2311` |
| Método | POST |
| Respuesta | JSON, con forma variable según el informe |

Los filtros, si los hay, se concatenan al número de informe separados por `|`.

El token **no está en el repositorio**. Se lee del entorno (`VENCLOUD_TOKEN`), hay una
plantilla en `.env.example`, y `.env` está en `.gitignore`. El cliente además enmascara el
token en todo lo que imprime o guarda, para que no acabe en un log o en un fichero de
descarga.

## Cliente

`scripts/vencloud.py`, solo biblioteca estándar, ejecutable en cualquier máquina:

```bash
export VENCLOUD_TOKEN=...
python3 scripts/vencloud.py informe 1                     # un informe
python3 scripts/vencloud.py informe 12 2026-05-01 2026-05-31   # con filtros
python3 scripts/vencloud.py catalogo 1 40                 # recorre números y apunta qué devuelve cada uno
```

Guarda la respuesta cruda en `data/vencloud/` (fuera del control de versiones) y resume
filas, columnas y primer registro. Reintenta con espera creciente en fallos de red y 5xx,
nunca en 4xx.

## Lo que falta por averiguar

Se resuelve con una tanda de llamadas, no hace falta documentación:

1. **Qué número es cada informe**: cuál da ventas, visitas, incidencias, preventivos y
   censo de máquinas. Para eso está `catalogo`.
2. **Formato de los filtros**: orden, formato de fecha (`dd/mm/aaaa` o ISO) y cómo se
   indican centro y máquina.
3. **Si el filtro va con la barra codificada** (`%7C`) o literal. IIS rechaza una u otra
   según configuración, así que el cliente admite las dos: `VENCLOUD_FILTRO_CRUDO=1`
   fuerza el envío literal.
4. **Límites**: tamaño máximo de respuesta, rango de fechas por llamada, paginación y
   peticiones por minuto. El cliente espera un segundo entre llamadas mientras no se sepa.
5. **Zona horaria** de las fechas devueltas.

## Estado

El host `vencloudpro.eac.es` está **bloqueado por la política de red del entorno** de esta
sesión, así que las llamadas no salen desde aquí. El cliente está escrito y probado en su
manejo de errores; en cuanto el host esté permitido —o ejecutándolo desde una máquina con
salida a internet— se puede levantar el catálogo de informes y empezar la ingesta.

## Arquitectura de la ingesta

```
VenCloud API ──► ingesta programada ──► almacén ──► API propia ──► cuadro de mando
  (informes)      (cada noche)          (DuckDB)    (agregados)      (navegador)
```

La ingesta queda detrás de una interfaz con dos implementaciones, ficheros exportados y
API, de modo que el resto del sistema no se entera de cuál está activa y la integración no
bloquea la construcción del cuadro de mando.
