# Revisión en AIRBUS Sevilla · 19-24 de octubre

Petición de Manolo (regeneraciones): tener preparados los planogramas y precios de **Tablada, San
Pablo Norte y San Pablo Sur**. Se revisan datos DEX, planogramas, cantidades, precios y
dosificaciones del café. La tarifa de AIRBUS tiene que ser **la misma en los tres centros**.

## Qué sale de aquí

| necesidad | informe | dónde |
|---|---|---|
| planograma y precio por canal, de los tres centros | `M7 · EXT_AIRBUS_PLANOGRAMA` | [17](17-sql-extraccion-completa.md) |
| ¿es la tarifa igual en los tres? | `M8 · EXT_AIRBUS_TARIFA_IGUAL` | [17](17-sql-extraccion-completa.md) |
| dosificación del café (gramos por bebida) | `M2 · EXT_MAESTRO_RECETAS` | [28](28-recetario.md) |
| qué café y qué leche lleva cada carril | `M1 · EXT_MAESTRO_CARRILES` | [29](29-carriles-y-coste-del-cafe.md) |

M7 y M8 se pegan tal cual en VenCloud (sin parámetros). En M8, `igual` = `no` o `sin tarifa` son las
filas a corregir **antes** del 19. `tarifa_ef` vacía significa que no hay tarifa, no que valga cero.

## Lo que no está, y se dice

- **DEX.** Llega a VenCloud, pero este repositorio no tiene ninguna tabla ni columna de DEX
  modelada: ni `estructura_columnas.xlsx` ni los informes extraídos la recogen. No se ha inventado
  ninguna. Hace falta una sonda (como M6) que localice dónde se guarda para escribir su informe.
- **Dosificación real de la máquina.** M2 da la dosis de la receta (p. ej. 8 g de grano); lo que
  tiene configurado cada máquina no está en la base. Se contrasta en la visita, contra M2.
- **Accesos y autorizaciones** (tres personas y el vehículo del correo): son gestión con Airbus, no
  datos de la plataforma. Los datos personales no se guardan en el repositorio.
