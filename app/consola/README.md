# Consola de administración

`index.html` · contra `/api/admin/*`, sin una sola llamada fuera del dominio.

## Lo primero, porque antes no era así

**Esta pantalla ya no es el prototipo.** La versión anterior no validaba contraseñas y guardaba
la configuración en el navegador; se decía en esta misma página para que nadie la desplegara
creyendo que protegía algo. Ahora el acceso lo lleva Cognito a través de `/api/acceso`, y todo lo
que se ve aquí sale de DynamoDB a través de `/api/admin/*`.

Y lo que decide quién entra no es esta página. Si alguien que no es administrador la abre, no es
que no vea los botones: es que **las rutas le contestan 403**. Lo de ocultar la pantalla es
cortesía, no seguridad.

## Lo que no lleva escrito

La consola **no tiene copiadas las reglas del modelo de permisos**. El techo de cada tipo de
perfil, el tipo mínimo de cada sesión y lo que cada tipo trae de serie los manda la API en
`GET /api/admin/perfiles`, desde el mismo `autorizacion.py` que luego los aplica.

Una copia aquí se quedaría vieja el día que cambiara esa pieza, y el síntoma sería el peor
posible: un administrador marcando una casilla que no hace nada, convencido de haber concedido
algo. Así, al cambiar el tipo de un perfil, las sesiones y los permisos que ese tipo no admite se
tachan **en el momento**, con el motivo escrito al lado («desde operaciones», «no en cliente»), y
además salen deshabilitados: no se pueden marcar ni por error.

## Seis secciones

| sección | qué hace |
|---|---|
| **Usuarios** | alta en Cognito con contraseña de un solo uso, perfil, bloqueo, límite de preguntas, nueva contraseña, baja |
| **Perfiles** | ámbito (clientes + centros + delegaciones), sesiones visibles, permisos con su techo, umbral de rentabilidad |
| **Plataforma** | el interruptor global del asistente, el límite de preguntas por día, el umbral general — y lo que el asistente **no** hace |
| **Teléfonos** | los de técnicos y reponedores; sin teléfono dado de alta un WhatsApp no sale y queda un aviso diciéndolo |
| **Carga** | lo que dejó escrito la carga nocturna: descargas, bytes, retraso, errores y filas por informe |
| **Cola de acciones** | los WhatsApp y las altas de incidencia que alguien pidió desde un panel |

Las alarmas no están aquí: viven en `/avisos/`, que es donde las usa quien las usa. La consola
enlaza allí en vez de tener un segundo sitio donde tocarlas.

## Dos detalles que son el trabajo de verdad

**Un informe a cero se marca en rojo.** Es la única señal que hay cuando algo cambia en VenCloud:
el informe se descarga igual, sin error, pero vacío. Si no se ve en esta pantalla, no se ve en
ninguna, y los paneles siguen enseñando la cifra del día anterior como si tal cosa.

**La cola dice que la incidencia no se ha dado de alta.** Dar de alta una incidencia en VenCloud
es una **escritura en el ERP**, y hasta tener el endpoint y el permiso confirmados no se inventa la
llamada: la petición se queda en la cola, visible, con quién la pidió y cuándo. Lo contrario sería
que alguien creyera haber abierto un parte que no existe.

## El ámbito sugiere lo que hay en los datos

En las tres casillas del ámbito, con la primera letra sale debajo una lista de lo que hay en
los datos y se va filtrando mientras se escribe (sin distinguir mayúsculas ni tildes). Flechas
para moverse, Intro o clic para elegir, Escape para cerrar la lista sin cerrar el diálogo. Lo
escrito a mano sigue valiendo.

Los nombres salen de las fichas de centro del histórico, que la consola ya tiene en memoria: no
hay ninguna llamada nueva. **Los centros se buscan por nombre pero se guarda su número**, porque
`en_ambito()` exige el centro exacto y el número no cambia cuando VenCloud renombra un centro;
los clientes se guardan por nombre, que allí basta con ser un trozo. Debajo de cada casilla se
lee con cuántos centros encaja cada valor (y qué centro es cada número), y en rojo el que no
encaja con ninguno: un ámbito mal escrito no da error, da un panel vacío.

## Comprobado en Chromium

Claro, oscuro y móvil. El alta de usuario, el guardado de configuración sobreviviendo a una
recarga, el error del servidor en un teléfono sin prefijo enseñado en el formulario, el techo
tachándose al cambiar de tipo, y un usuario que no es administrador viendo que no es su pantalla.
Sin errores de consola y sin una sola llamada fuera del dominio.
