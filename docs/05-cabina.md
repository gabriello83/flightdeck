# Cabina — interfaz de la cuenta AIRBUS

Primera pantalla del cuadro de mando interno. Fichero: `app/cabina.html`, autocontenido
(los datos van embebidos, sin dependencias externas salvo las tipografías).

Publicada en https://claude.ai/artifact/Xh15cUdCvnc1anQBVPvFM8

## Qué enseña y por qué

El orden de la página sigue el de una cabina: **primero el estado, después el detalle**.

1. **Anunciador** (franja superior oscura): cuatro luces con lo que exige atención ahora —
   máquinas sin recaudar, máquinas mudas, sin reposición y cobertura de telemetría.
2. **Ingreso del mes**: septiembre, con el reparto entre tarjeta (telemetría) y efectivo
   (recaudación). Es la cifra buena, la del informe 68, no la de los audits.
3. **Avisos de operación**: ocho avisos ordenados por severidad. Cada uno **redacta el
   mensaje** para el responsable de ruta, el supervisor o calidad, con el dato concreto
   dentro. Botón de copiar; el envío por WhatsApp todavía no está conectado.
4. **Análisis**: venta por centro, patrón semanal, serie diaria, máquinas mudas,
   rendimiento por máquina, servicio técnico, rutas y surtido.

## Decisiones de diseño que vienen del análisis

- **El patrón semanal tiene panel propio.** Como el viernes vende un 28% menos que el
  martes, comparar contra «ayer» daría una falsa alarma cada semana. El panel lo dice
  explícitamente para que nadie construya encima esa comparación.
- **Cada cifra de venta lleva su cobertura al lado.** La venta sale de la telemetría, no de
  `cal_totimpvtas`, precisamente porque la cobertura de aquella va del 0% al 86% según
  delegación.
- **El pie enumera lo que no se puede medir todavía** —margen, rotura de stock, limpieza y
  temperatura— en vez de enseñar un indicador que mediría el registro y no el trabajo.
- Colores de serie validados con el script de la guía de visualización: azul y naranja
  pasan las seis comprobaciones en claro y en oscuro, incluida separación para daltonismo.
  Los colores de estado (verde, ámbar, rojo) van siempre con etiqueta, nunca solos.

## Lo que falta para la siguiente iteración

- **Envío real por WhatsApp** al responsable de la ruta y alarmas escaladas al supervisor.
  Hoy el panel redacta y tú pegas.
- **Datos en vivo** desde la API de VenCloud: ahora las cifras están embebidas y hay que
  regenerarlas con `scripts/prepare_data.py`.
- **Filtro por centro y por ruta**, que con nueve centros ya hace falta.
- **Ficha de máquina**: serie diaria, visitas, averías y planograma de una máquina concreta.
