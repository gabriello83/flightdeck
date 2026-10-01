# El constructor de alarmas y el asistente de IA

---

# 1. Umbrales configurables

Nada de números escritos en el código. Cada regla tiene su umbral y vive en tres niveles, de menos
a más específico:

| nivel | quién lo pone | dónde vive |
|---|---|---|
| **Por defecto del sistema** | nosotros, con el dato medido | catálogo de reglas |
| **Por perfil** | el administrador | `reglas_negocio` del perfil |
| **Por usuario** | el propio usuario, si el admin se lo permite | preferencias |

Ya está hecho para el primero: **el umbral de rentabilidad de AIRBUS es un campo**, llega en
`perfil.umbral_rentabilidad_mes`, sale por defecto a 350 € porque lo fijó el administrador, y el
usuario lo cambia en pantalla y el panel se recalcula solo. El mismo patrón vale para los demás.

---

# 2. El constructor de alarmas, en el panel de administrador

Una alarma es **una fila de datos**, no código. El admin la crea, la edita, la duplica o la apaga
sin que nadie toque nada.

## La ficha de una alarma

```json
{
  "alarma_id": "frio-vehiculo",
  "nombre": "Frío del vehículo por encima del umbral",
  "activa": true,
  "severidad": "critica",
  "regla": {
    "fuente": "jornadas",
    "campo": "temperatura_inicio",
    "operador": ">",
    "umbral": 8,
    "unidad": "°C"
  },
  "agrupar_por": "vehiculo",
  "ventana": "dia",
  "ambito": { "delegaciones": [], "clientes": [] },
  "silencio_horas": 24,
  "destinatarios": [
    { "tipo": "rol",    "valor": "responsableven", "canal": "whatsapp" },
    { "tipo": "rol",    "valor": "calidad",        "canal": "correo" },
    { "tipo": "correo", "valor": "operaciones@serunion.es", "canal": "correo" }
  ],
  "plantilla_whatsapp": "frio_vehiculo_v1",
  "asunto_correo": "Cadena de frío: {{vehiculo}} arrancó a {{valor}} °C",
  "cuerpo": "El vehículo {{vehiculo}} de la ruta {{ruta}} inició jornada el {{fecha}} con el frigorífico a {{valor}} °C, por encima del umbral de {{umbral}} °C. Reponedor: {{empleado}}."
}
```

## Qué ve el admin en pantalla

Un formulario de siete bloques, sin escribir una línea:

1. **Nombre y severidad** — crítica, alta, media o baja.
2. **Qué vigilar** — desplegable de fuentes (visitas, jornadas, recaudación, stock, SAT,
   telemetría) y, dentro, de campos. Sale del catálogo de informes, así que **sólo se ofrecen
   campos que existen de verdad**.
3. **Condición** — operador y umbral, con la unidad puesta.
4. **Agrupación y ventana** — por máquina, ruta, vehículo, centro o delegación; del día, la semana
   o el mes.
5. **Ámbito** — a qué delegaciones o clientes aplica. Vacío quiere decir todo.
6. **Destinatarios y canal** — por rol (responsable de vending, de SAT, calidad), por persona o
   por correo suelto. **Cada destinatario elige canal: WhatsApp, correo, o sólo bandeja.**
7. **Mensaje** — asunto y cuerpo con variables `{{...}}`, y **vista previa con datos reales de
   ayer** antes de guardar.

Y dos cosas que evitan el desastre operativo:

- **«Probar ahora»**: evalúa la regla contra el último día cargado y dice *«esta alarma habría
  disparado 115 veces ayer»*. Sin eso, se crea una regla con el umbral mal puesto y a la mañana
  siguiente hay 115 WhatsApps.
- **Silencio** (`silencio_horas`): no se repite el mismo aviso del mismo elemento hasta pasadas N
  horas. Sin esto, una máquina muda avisa cada hora durante tres días y la gente silencia el
  canal entero.

## Cómo se entrega

| canal | cómo | cuándo |
|---|---|---|
| **Bandeja** | sesión 10, siempre | todas |
| **Correo** | Amazon SES | agrupado por destinatario, inmediato o resumen diario |
| **WhatsApp** | Meta Cloud API | sólo críticas y altas |

WhatsApp exige **plantillas aprobadas** por Meta para iniciar conversación: no se puede mandar
texto libre a un número que no ha escrito antes. Así que cada alarma lleva su `plantilla_whatsapp`
y el cuerpo sólo rellena variables. **Hay que darlas de alta con antelación** — tardan uno o dos
días en aprobarse.

Y los teléfonos salen solos: `recursos.empleados` ya tiene `telefono`, `responsablesat`,
`responsableven` y `delegacionid`. La sesión 15 del admin sirve para corregir los que falten.

## Qué se guarda de cada envío

Quién, cuándo, por qué canal, con qué valor disparó y si se entregó. Dos razones: **saber si el
aviso llegó** cuando alguien diga que no se enteró, y **medir qué alarmas se ignoran siempre**,
que son las que hay que reajustar o apagar.

---

# 3. El asistente de IA

## La decisión de fondo: no le damos la base de datos

Lo fácil sería darle acceso al almacén y dejar que escriba consultas. **No lo vamos a hacer**, por
dos razones, y la segunda pesa más que la primera:

**Seguridad.** Un modelo al que se le pide discreción no es un control de acceso. Si puede
consultar, puede equivocarse de cliente.

**Corrección.** Un modelo escribiendo SQL contra estas tablas volvería a caer en todas las trampas
que nos costó semanas encontrar: contaría los partes del sistema como visitas, sumaría la merma de
los tres diarios, leería `cal_impcarga` como carga bruta cuando es neta, mezclaría la fecha de
escritura con el periodo contable y contaría `00SE0000` como una máquina. Daría cifras que parecen
razonables y están mal.

## Lo que sí hace: herramientas ya filtradas

El asistente recibe **funciones**, no tablas. Cada una la ejecuta la Lambda, que resuelve el ámbito
desde el token de Cognito **antes** de consultar nada. El modelo no puede pedir otro cliente
porque la herramienta no sabe devolverlo.

| herramienta | devuelve |
|---|---|
| `indicadores(periodo)` | las cifras de cabecera del panel |
| `serie(metrica, periodo, agrupacion)` | la serie temporal |
| `ranking(dimension, metrica, orden, n)` | mejores o peores por máquina, centro, ruta o artículo |
| `maquinas(filtro)` | listado con su situación |
| `incidencias(periodo, filtro)` | averías y su estado |
| `alarmas_activas()` | lo que está disparado ahora |
| `explica_alarma(id)` | la regla, su umbral y por qué saltó |

Son **los mismos agregados que pintan los paneles**. Así el asistente nunca puede contradecir a la
pantalla: leen lo mismo.

## El libro de reglas

En el prompt del sistema va todo lo que hemos aprendido en estas semanas. Es lo que convierte al
asistente en alguien que conoce la casa:

- Los partes del sistema no son visitas.
- La merma se cuenta una vez, en la máquina.
- El mes en curso está incompleto: le falta la tarjeta, que es el 55 % — nunca compararlo con un
  mes cerrado sin avisar.
- El viernes vende un 28 % menos que el martes: no se compara contra «ayer».
- `00SE0000` no es una máquina.
- La venta sale de telemetría; donde no hay telemetría, no hay cifra.
- Y **la lista de lo que no se puede medir**: tiempo de máquina parada, coste de repuestos, plan
  de ruta contra real, inventario por canal.

Esa última lista es la más importante. **El asistente tiene que saber decir «eso no está
medido»**, y decir por qué. Un asistente que improvisa un número cuando no lo tiene destruye la
confianza en todo el cuadro de mando.

## Reglas de conducta

1. **Sólo cifras que haya devuelto una herramienta.** Si no la tiene, la pide; si no existe, lo
   dice.
2. **Siempre con su periodo y su cobertura** — «en los 123 días del periodo, sobre las 547 máquinas
   con telemetría».
3. **No aconseja sobre personas.** Puede decir que una ruta tarda más; no juzga a un reponedor.
4. **No escribe en VenCloud.** Abrir una incidencia es un botón de la sesión 10, con su
   confirmación, no algo que el modelo decida.
5. **Cada respuesta enlaza al panel** de donde sale, para que se pueda comprobar.

## Qué modelo y qué cuesta

**Claude Opus 5.5** (`claude-opus-5-5`), con `thinking: {type:"adaptive"}` y `effort: "medium"`,
que es su valor por defecto y va sobrado para preguntas de cuadro de mando.

El libro de reglas y la definición de herramientas son idénticos en cada pregunta, así que van con
**prompt caching**: se pagan una vez y después se leen a precio de caché.

| | tokens | coste |
|---|---:|---|
| Libro de reglas + herramientas (en caché) | ~5.000 | $0,20/MTok al leer |
| Pregunta y resultados de herramienta | ~2.500 | $4/MTok |
| Respuesta | ~600 | $20/MTok |
| **Por pregunta** | | **~2 céntimos** |

Mil preguntas al mes salen por unos **20 €**. Para lo que cuesta la plataforma entera, es ruido —
y el modelo es un parámetro de configuración, así que si algún día interesa cambiarlo es una línea.

## Dónde vive

Dentro de `digivend.es`, como todo lo demás: el navegador llama a `/api/asistente` del mismo
dominio, y es **la Lambda** la que habla con la API de Claude. El navegador del cliente no llama a
nadie fuera, que es exactamente el requisito de red de AIRBUS.

## Qué no va a hacer en la primera versión

- No manda mensajes ni abre incidencias por su cuenta.
- No recuerda conversaciones anteriores entre sesiones.
- No sube ficheros ni los analiza.
- No entra en devoluciones, que llevan nombre y DNI.
