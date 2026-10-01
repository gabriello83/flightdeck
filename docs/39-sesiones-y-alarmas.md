# La plataforma: sesiones, perfiles y alarmas

Diseño de la consola a partir de todo lo medido. Cada sesión y cada alarma de esta lista **sale de
una tabla que ya hemos extraído y de un número que ya hemos comprobado**; no hay nada aquí que
dependa de un dato que no tengamos.

---

## 1. Aviso de alcance

Login, alta de usuarios, chat con IA, envío de WhatsApp y alta de incidencias en VenCloud **no son
una página estática**. Necesitan servidor. La arquitectura mínima:

| pieza | para qué |
|---|---|
| **Cognito** | login, contraseñas, recuperación, sesión |
| **DynamoDB** | usuarios, perfiles, ámbitos y catálogo de informes por perfil |
| **API Gateway + Lambda** | sirve sólo los datos del ámbito del usuario; escribe en VenCloud |
| **S3 + CloudFront** | la página y los agregados de la cabina |
| **Lambda nocturna** | la carga de las 30 tablas |
| **Lambda de alarmas** | evalúa las reglas y encola los avisos |
| **API de WhatsApp** | Meta Cloud API o Twilio |
| **Claude API** | el asistente, con el ámbito del usuario inyectado en cada pregunta |

**La regla de oro del filtrado**: el ámbito **no** se aplica en el navegador. La Lambda recibe el
token de Cognito, resuelve el ámbito del usuario y **devuelve sólo esas filas**. Si el filtro
estuviera en la página, cualquiera con el navegador abierto vería todo.

Lo mismo para el asistente: **no se le da la base entera y se le pide que filtre.** Se le pasan
únicamente los datos del ámbito, ya filtrados por la Lambda. Un modelo al que se le pide
discreción no es un control de acceso.

---

## 2. Las sesiones

Dieciséis, repartidas por perfil. Cada perfil ve las suyas **y las de los perfiles por debajo**.

### Visibles para el cliente — las que el admin le active una a una

| # | sesión | qué enseña | de dónde sale |
|---:|---|---|---|
| 1 | **Resumen** | venta del periodo, ticket medio, máquinas activas, cobertura del dato | telemetría + B3 |
| 2 | **Venta y consumo** | por centro, serie diaria, patrón semanal, perfil horario, top artículos | telemetría |
| 3 | **Servicio recibido** | visitas, unidades repuestas, frecuencia real contra la pactada | A1, A2, D3 |
| 4 | **Disponibilidad** | máquinas mudas, averías, tiempo de respuesta | telemetría, D7, D8 |
| 5 | **Surtido y planograma** | qué hay en cada máquina, precios, canales sin artículo | `maquinascanales`, M1 |
| 6 | **Calidad y seguridad alimentaria** | caducidad, temperatura de vehículo, limpieza | C3, D5, A1 |

### Añade el perfil de operaciones

| # | sesión | qué enseña | de dónde sale |
|---:|---|---|---|
| 7 | **Rutas y jornada** | km, duración, GPS, visitas por ruta, jornadas abiertas | D5, D1–D4, A1 |
| 8 | **Recaudación y efectivo** | teórico contra contado, bolsas, efectivo sin dato electrónico | A7, B3, A1 |
| 9 | **Stock y merma** | balance, movimientos, caducidad por eslabón, inventario | C1–C3, C9 |
| 10 | **Avisos y acciones** | bandeja de alarmas, **envío de WhatsApp** y **alta de incidencia** | motor de alarmas |

### Añade el perfil de dirección

| # | sesión | qué enseña | de dónde sale |
|---:|---|---|---|
| 11 | **Rentabilidad** | margen por máquina, centro y cliente; coste de servicio y de SAT | A11, M1, M2, A1, D9 |
| 12 | **Cumplimiento** | inventario, lectura electrónica, verificaciones, campos sin configurar | A3B, A7, C8, D3 |

### Sólo administrador

| # | sesión | qué hace |
|---:|---|---|
| 13 | **Usuarios y permisos** | alta con nombre, correo y contraseña; perfil; **ámbito múltiple** por cliente, centro o delegación |
| 14 | **Catálogo de informes** | qué sesiones y qué gráficos ve cada perfil y cada usuario |
| 15 | **Teléfonos y mensajes** | teléfono de cada técnico y reponedor, y las plantillas de WhatsApp |
| 16 | **Estado de la carga** | última noche, filas por tabla, errores, retraso del dato |

**El ámbito es múltiple y aditivo**: a un usuario se le pueden dar «cliente AIRBUS» + «centro
Getafe» + «delegación Madrid-Leganés» a la vez, y verá la unión.

---

## 3. Las alarmas

Veinte reglas. Entre paréntesis, **lo que da hoy el dato real** — así se ve de entrada cuánto
ruido haría cada una y dónde poner el umbral.

### Seguridad alimentaria · las que no admiten demora

| alarma | regla | hoy | fuente |
|---|---|---|---|
| **Frío del vehículo** | temperatura al arrancar > 8 °C | **115 de 1.288 jornadas · 8,9 %**, máximo 26 °C | D5 |
| **Caducidad por ruta** | producto caducado del mes por encima del umbral | 1.154 líneas · 2.374,53 €/mes | C3 |
| **Caducidad reincidente** | mismo artículo caducado 3+ veces en la misma máquina | frescos Ñaming a la cabeza | C3 |

### Dinero

| alarma | regla | hoy | fuente |
|---|---|---|---|
| **Bolsa sin dato electrónico** | se recauda y no hay lectura de monedero | **93 % de las bolsas** | A1 + A7 |
| **Efectivo ciego** | PDV sin telemetría con efectivo > X €/mes | **122.327 €/mes en 504 PDVs** | B3 |
| **Descuadre teórico-contado** | diferencia > X % o > X € en una bolsa | medible en el 2,9 % | A7 vs B3 |
| **Bolsa sin contar** | recogida hace más de N días y sin aparecer en recaudación | Loomis pasa 1–2 veces/semana | A1 + B3 |
| **Máquina con demasiado efectivo** | efectivo acumulado estimado > 100 € sin recaudar | la regla **no está configurada en ninguna máquina** | telemetría + D3 |

### Disponibilidad y SAT

| alarma | regla | hoy | fuente |
|---|---|---|---|
| **Máquina muda** | sin venta en N horas dentro de su franja | respeta `criteriosalarmasnovtas` | telemetría |
| **Máquina reincidente** | 5+ incidencias en 30 días | **1.317 con 5+, 198 con 20+**; una con 355 | D7 |
| **Avería estancada** | abierta más de N horas | p90 **94,4 h**, máximo 522 h | D8 |
| **Ticket que rebota** | cambia de área 3+ veces | **58 % cambia de área** al menos una vez | D8 |
| **Monedero averiado** | 2+ devoluciones en la misma máquina en 30 días | 15.583 devoluciones en 9 meses | D7 + A10 |

### Servicio y rutas

| alarma | regla | hoy | fuente |
|---|---|---|---|
| **Visita no realizada** | día marcado en el criterio y sin parte | 955 máquinas **sin día marcado** | D3 + A1 |
| **Parte mal cerrado** | duración > 4 h o < 2 min | **189 partes < 2 min** en un día | A1 |
| **Jornada abierta** | sin cerrar pasadas 14 h | **28 abiertas**, máximo 179 h | D5 |
| **Inventario caducado** | último inventario de máquina > 90 días | **91,4 % fuera de norma**, 23,8 % nunca | A3B |
| **Retorno sin verificar** | abierto más de N días sin verificación | **100 % · los 231 de nueve meses** | C8 |

### Stock y configuración

| alarma | regla | hoy | fuente |
|---|---|---|---|
| **Artículo sin coste** | se carga o se vende un artículo con `puc` = 0 | **59 artículos**, casi todos frescos | A2, C3 |
| **Canal sin artículo o sin precio** | canal activo mal configurado | — | `maquinascanales` |
| **Cambio excesivo en tubos** | más de X € parados en una máquina | p99 **143,95 €**, máximo 827 € | A8 |
| **Campo clave sin configurar** | `limite_recaudacion`, `coste_visita`, `coste_unidad` | los tres a cero | D3, D9, D10 |

### Cómo se entrega cada alarma

| severidad | quién la recibe | cómo |
|---|---|---|
| **Crítica** (frío, descuadre de dinero) | supervisor de delegación y calidad | WhatsApp inmediato + bandeja |
| **Alta** (máquina parada, avería estancada) | responsable de ruta o SAT | WhatsApp + bandeja |
| **Media** (inventario, verificaciones) | responsable de delegación | bandeja y resumen diario |
| **Baja** (configuración) | administrador | resumen semanal |

El destinatario se resuelve solo: `recursos.empleados` ya tiene `telefono`, `responsablesat`,
`responsableven` y `delegacionid`. La sesión 15 sirve para corregir y completar esos teléfonos.

---

## 4. El perfil de AIRBUS

**No tengo el cuadro de mando que envió David.** No me lo has pasado y no quiero inventarme qué
lleva. Mándamelo —el fichero, un enlace o unas capturas— y lo reproduzco tal cual, que es lo que
pides.

Mientras tanto, esto es lo que **yo** configuraría para AIRBUS con lo que ya tenemos medido, y que
se puede ajustar en cuanto vea el de David:

**Ámbito**: cliente AIRBUS — nueve centros: Getafe, San Pablo Sur, San Pablo Norte, Tablada, CBC,
Illescas, ITC, Albacete y Albacete Parque Científico. 547 máquinas.

**Sesiones activas**: 1 Resumen · 2 Venta y consumo · 4 Disponibilidad · 5 Surtido y planograma.

**Sesiones desactivadas y por qué**: *Servicio recibido* y *Calidad* se activan cuando el dato de
visita de esos centros esté más completo, y nunca *Recaudación* ni *Stock*, que son internas.

**La razón de la selección está en el dato**: en AIRBUS **sólo el 3,2 % de la venta es efectivo**,
así que la recaudación no es su problema; lo suyo es **disponibilidad y surtido**. Y pesa: AIRBUS
es un tercio de la compañía y Getafe es el primer centro del país.

Ya tenemos construido `app/cabina.html` con cuatro luces de anunciador, ingreso del mes, ocho
avisos redactados y siete análisis, y 778.370,65 € de venta de AIRBUS entre mayo y agosto. **Esa
página es el punto de partida del perfil**, y cuando vea la de David ajusto lo que falte.
