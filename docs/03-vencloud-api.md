# Integración con VenCloud

## Qué es VenCloud

VenCloud es el ERP de vending de **EAC Software / Macrosistemas**. Serunion —el operador
que presta el servicio en los centros de Airbus, y que aparece como cliente `10002-SERUNION, SA`
en todas nuestras tablas— trabaja con la versión VenCloud PRO.

En los datos de averías hay una pista importante: varias incidencias figuran registradas
por el usuario **`VenCloudExternalAPI`**. Es decir, la API externa existe y ya se usa en
producción contra este mismo tenant.

## Lo que no sabemos todavía

EAC Software no publica documentación abierta de la API. Sin estos datos no se puede
escribir el conector:

1. **URL base** del entorno (producción y, si existe, preproducción).
2. **Autenticación**: clave de API, OAuth2, usuario y token… y cómo se renueva.
3. **Endpoints de los informes rápidos**: qué informe corresponde a ventas, visitas,
   incidencias, preventivos y censo de máquinas.
4. **Filtros admitidos**: rango de fechas, centro, delegación, máquina.
5. **Paginación y límites**: tamaño máximo de respuesta, número de peticiones por minuto,
   si hay un tope de filas o de rango de fechas por llamada.
6. **Formato y zona horaria**: JSON o CSV, y en qué huso vienen las fechas.
7. **Un usuario de solo lectura** dedicado a este proyecto, para no trabajar con las
   credenciales personales de nadie.

Quién puede darlo: EAC Software como fabricante, o el equipo de sistemas de Serunion como
propietario del tenant. Conviene pedirlo por escrito, indicando que es un acceso de solo
lectura para explotación de informes.

## Arquitectura propuesta

```
VenCloud API ──► ingesta programada ──► almacén ──► API propia ──► cuadro de mando
  (informes)      (cada noche)          (DuckDB)    (agregados)      (navegador)
```

- **Ingesta**: un proceso que cada noche pide a VenCloud el delta del día y lo normaliza
  con las mismas reglas que ya aplica `scripts/prepare_data.py`.
- **Almacén**: DuckDB sobre fichero. 1,1 millones de líneas por cuatro meses es un volumen
  pequeño; con un año de histórico seguirá siéndolo, y las consultas agregadas son
  inmediatas sin necesidad de montar un servidor de base de datos.
- **API propia**: expone solo agregados (por centro, máquina, día, artículo). Así el
  navegador nunca descarga el millón de filas.
- **Cuadro de mando**: aplicación web, en la línea de cabina de avión que busca el proyecto.

La pieza de ingesta se escribe **detrás de una interfaz**, con dos implementaciones: una
que lee los ficheros exportados a mano (lo que tenemos hoy) y otra que llama a la API
(cuando haya credenciales). El resto del sistema no se entera de cuál está activa, así que
la integración no bloquea la construcción del cuadro de mando.

## Mientras tanto

Con los informes exportados a mano ya se puede montar todo y tenerlo funcionando. El día
que lleguen las credenciales, lo único que cambia es de dónde salen los ficheros.

Una cosa que conviene pedir ya, aunque siga siendo exportación manual: que el informe de
ventas **incluya la hora**. Solo la trajo el fichero de agosto, y es lo que abre el
análisis por franja horaria (ver `02-analisis-exploratorio.md`).
