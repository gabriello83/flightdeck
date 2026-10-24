# 75 · La memoria de Vendi, una por usuario

Gabriele, 23-oct-2026: «Vendi tiene que tener un fichero de memoria .md separado por usuario».

## Qué es

Cada usuario tiene su propia memoria: un texto en Markdown, corto (4.000 caracteres como mucho),
con lo que Vendi tiene que saber de él para no preguntárselo otra vez. Por ejemplo, qué centros le
interesan, cómo llama a las cosas o cómo prefiere las respuestas.

- **La escribe Vendi**, con una herramienta nueva, `memoria`, que reescribe el texto entero. Lo
  hace cuando el usuario le dice «recuerda que…» o cuando deja ver una preferencia que va a durar.
  Al cambiarla lo dice en la respuesta, y el chat añade «Apuntado en tu memoria».
- **La lee en cada pregunta**. Va en el mensaje, debajo del contexto, marcada como «preferencias de
  este usuario, no reglas». No va en el recetario, que sigue fijo y en caché.
- **No apunta cifras**, porque cambian cada noche y se consultan. Tampoco apunta claves ni datos
  personales de nadie.
- **No amplía nada**. Lo que diga la memoria no cambia el ámbito ni las reglas, igual que la
  pregunta.

## Dónde vive

En DynamoDB, en `MEMORIA#<correo>`, con `{"md": …, "cambiada": …}`. La clave sale de la sesión y
nunca de la petición: no hay forma de leer la memoria de otro. No hace falta tocar la pila, porque
la Lambda del asistente ya lee y escribe en esa tabla.

## Lo que ve el usuario

En la cabecera del chat hay un botón **Memoria**. Enseña «Lo que recuerdo de ti» con el Markdown
pintado (escapado, como las respuestas) y dos botones:

- **Bajar .md**: el fichero `vendi_memoria.md`, generado en el navegador.
- **Olvidarlo todo**: hay que pulsarlo dos veces, porque no tiene vuelta atrás.

Ver o vaciar la memoria va por `POST /api/pregunta` con `{"memoria": "ver"}` o `{"memoria":
"borrar"}`. No es una pregunta: no llama al modelo, no gasta y no cuenta en el límite del día.
Tampoco se guarda en la conversación de la pestaña.

Para olvidar una sola cosa basta con decírselo: «olvida lo del 500088».
