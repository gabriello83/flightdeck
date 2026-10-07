# Revisión en AIRBUS Sevilla · 19-24 de octubre

Petición de Manolo (regeneraciones): tener preparados los planogramas y precios de **Tablada, San
Pablo Norte y San Pablo Sur**. Se revisan datos DEX, planogramas, cantidades, precios y
dosificaciones del café. La tarifa de AIRBUS es **una sola, la definitiva, y vale para los tres
centros**: está en `data/tarifa_airbus.csv` (175 artículos, con los cafés R01…R36).

## Cómo se prepara

El planograma no se pide con un SQL cada vez: vive en S3, como el resto de maestros. `M7 ·
EXT_MAESTRO_PLANOGRAMA` ([17](17-sql-extraccion-completa.md)) es el informe que lo lleva allí
(`maestros/planograma`), de todo el parque, y se filtra al leer por `centro`.

**Pendiente de una sola vez:** crear M7 en VenCloud y apuntar su número de informe. Hasta entonces
no puede entrar en `infra/manifiesto.json`: `test_manifiesto.py` impide arrancar la extracción con
un informe sin número, y es lo correcto. Con el número, se añade al manifiesto y desde esa noche
está en S3.

Contraste con la tarifa, con el CSV de `maestros/planograma` (y, para los cafés, el de
`maestros/recetas`, que ya está en S3):

```sh
python3 infra/airbus_tarifa.py planograma.csv recetas.csv
```

Sale una línea por canal que no cumple (precio distinto, artículo fuera de la tarifa o canal
activo sin artículo), el resumen por centro y los cafés cuyo precio de venta no coincide. Sólo mira
los tres centros de AIRBUS Sevilla.

Como la tarifa es la misma para los tres, «iguales en los tres sitios» se cumple por construcción:
lo que se comprueba es que **cada centro la cumpla**. Los canales que salgan con otro precio son los
que hay que regenerar antes del 19.

## Dosificación del café

`M2` da la dosis de la receta (p. ej. 8 g de grano) y `M1 · EXT_MAESTRO_CARRILES`
([29](29-carriles-y-coste-del-cafe.md)) qué café y qué leche lleva cada carril.

## Lo que no está, y se dice

- **DEX.** Llega a VenCloud, pero este repositorio no tiene ninguna tabla ni columna de DEX
  modelada: ni `estructura_columnas.xlsx` ni los informes extraídos la recogen. No se ha inventado
  ninguna. Hace falta una sonda (como M6) que localice dónde se guarda, o un ejemplo del dato.
- **Dosificación real de la máquina.** Lo que tiene configurado cada máquina no está en la base: se
  contrasta en la visita, contra la receta de M2.
- **Accesos y autorizaciones** (tres personas y el vehículo del correo): son gestión con Airbus, no
  datos de la plataforma. Los datos personales no se guardan en el repositorio.
