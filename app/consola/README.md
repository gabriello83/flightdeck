# Consola · acceso y panel de administración

`index.html` · 35 KB · sin una sola llamada fuera del dominio, como el panel de cliente.

## Lo primero, para que nadie se confunda

**Esta pantalla de acceso no valida contraseñas.** Es el recorrido del flujo, no el flujo. En
producción el acceso lo lleva **Cognito** y esta página **nunca ve la contraseña**: recibe un
token y lo manda en cada llamada a `/api`.

Lo dice la propia pantalla, debajo del formulario, para que nadie la despliegue creyendo que
protege algo. Se entra con `admin`, `operaciones` o `airbus` y cualquier contraseña.

La configuración se guarda en el navegador. En producción es DynamoDB a través de `/api`, del
mismo origen — el resto del código no cambia.

## Siete secciones

| sección | qué hace |
|---|---|
| **Usuarios** | alta con nombre, correo y contraseña inicial; perfil; alta/baja; asistente sí o no |
| **Perfiles** | ámbito múltiple (clientes + centros + delegaciones), sesiones visibles, umbrales y permisos |
| **Alarmas** | el constructor, con prueba y silencio |
| **Asistente de IA** | el interruptor, a tres niveles |
| **Teléfonos** | teléfonos de técnicos y reponedores, y el estado de las plantillas de WhatsApp |
| **Carga** | estado de la carga nocturna, tabla por tabla |
| **Consolas** | acceso a los paneles, y qué resolvería la Lambda con tu token |

Operaciones ve dos secciones (Consolas y Alarmas) y el cliente una. Las pestañas salen del perfil.

## El constructor de alarmas

Siete bloques, sin escribir una línea: **nombre y severidad · qué vigilar · condición · agrupación
y ventana · ámbito · destinatarios y canal · mensaje**.

Los campos a vigilar salen de un catálogo cerrado —seis fuentes con sus campos y su unidad—, así
que **sólo se puede construir una regla sobre un dato que existe**. Al cambiar de fuente, los
campos se recargan solos.

Y dos cosas que evitan el desastre operativo:

- **«Probar»** evalúa la regla contra el último periodo cargado con los números que medimos de
  verdad. La de frío contesta: *«con el umbral actual (> 8) habría disparado 115 de 1.288 jornadas»*.
  Si pasa de un cuarto de los casos, avisa de que son muchas y sugiere agrupar, subir el umbral o
  dejarla en bandeja antes de enchufar el WhatsApp.
- **Silencio en horas**: no se repite el mismo aviso del mismo elemento hasta pasadas N. Sin esto
  una máquina muda avisa cada hora durante tres días y la gente silencia el canal entero.

Vienen cinco alarmas cargadas, con los umbrales y los volúmenes reales medidos en el proyecto:
frío del vehículo (115 de 1.288 jornadas), bolsa sin dato electrónico (93 %), máquina reincidente
(1.317 de 2.722), inventario caducado (2.925 de 3.200) y máquina muda (61 de 547, apagada).

## El interruptor del asistente

A tres niveles, y **el de arriba manda**:

1. **Toda la plataforma** — si se apaga, nadie lo ve tenga el permiso que tenga.
2. **Por perfil** — qué perfiles lo tienen disponible.
3. **Por usuario** — excepciones sobre lo que dice el perfil.

Más un **límite de preguntas por usuario y día**, que es lo que corta el gasto si alguien se
desboca. Y la sección enumera lo que el asistente **no** hace, que es fijo y no configurable.

Se puede comprobar: apagando el interruptor global, la sección «Consolas» pasa a decir
*Deshabilitado* para el usuario que ha entrado.

## Comprobado

Renderizado en claro y oscuro: siete pestañas, el formulario de alarma con sus siete bloques, el
alta de usuario funcionando, la prueba de alarma devolviendo los números medidos, y el interruptor
global propagándose. Sin un solo error de consola.
