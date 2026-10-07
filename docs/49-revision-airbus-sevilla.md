# Revisión en AIRBUS Sevilla · 19-24 de octubre

Petición de Manolo (regeneraciones): tener preparados los planogramas y precios de **Tablada, San
Pablo Norte y San Pablo Sur**. Se revisan datos DEX, planogramas, cantidades, precios y
dosificaciones del café. La tarifa de AIRBUS es **una sola, la definitiva, y vale para los tres
centros**: está en `data/tarifa_airbus.csv` (175 artículos, con los cafés R01…R36).

## Cómo se prepara

1. Pegar **M7 · EXT_AIRBUS_PLANOGRAMA** ([17](17-sql-extraccion-completa.md)) en VenCloud y exportar
   a CSV. Es el planograma de los tres centros, sin tarifa.
2. Opcional, para los cafés: **M2 · EXT_MAESTRO_RECETAS** ([28](28-recetario.md)), también a CSV.
3. Contrastar:

   ```sh
   python3 infra/airbus_tarifa.py planograma.csv recetas.csv
   ```

   Sale una línea por canal que no cumple (precio distinto, artículo fuera de la tarifa o canal
   activo sin artículo), el resumen por centro y los cafés cuyo precio de venta no coincide.

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
