# 76 · El muñeco de cada usuario

Gabriele, 23-oct-2026: «Dar la posibilidad a los usuarios de cambiar imágenes a Vendi». Y luego:
«Vendi es el agente standard, se puede cambiar, recordarlo alguna vez cuando el usuario entra y
después de preguntarlo tres veces no lo preguntes más… un usuario te lo puede pedir escribiéndotelo».

## Los cinco

| Id | Nombre | Qué es |
|---|---|---|
| `vendi` | Vendi | la máquina de snacks azul, el de siempre |
| `tom` | Tom | el compañero de polo blanco, gafas y vaqueros, entero |
| `kiko` | Kiko | como Vendi, pero un grano de café |
| `furgo` | Furgo | la furgoneta de Serunion Vending de lado, blanca, con el bisonte detrás y la marca en la puerta |
| `bufy` | Bufy | la silueta del logo de Derichebourg, en su azul |

Todos son SVG dentro de `app/comun/asistente.js`: ni imágenes ni nada que pedir fuera del dominio.
Vendi, Tom y Kiko saludan con la mano. Furgo no tiene manos ni piernas: al saludar le giran las ruedas. Bufy tampoco tiene mano: al pasarle el ratón, al entrar y al
abrir el chat **se levanta de manos como un caballo**. El cuerpo gira sobre la cadera, las patas
traseras se quedan en el suelo y las delanteras patean el aire. Está hecho a partir del logo, en
tres trozos del mismo trazo, y los recortes se pisan un poco para que no se vea la costura. Lo
blanco del anillo y del ojo va pintado, no hueco, para que en modo oscuro siga pareciendo el logo.
Con «reducir movimiento» no se mueve ninguno.

## Cómo se elige

- En el chat, el botón **Muñeco** enseña los cinco, con el que lleva puesto marcado. Pulsar uno
  lo cambia en los tres sitios donde sale: el botón flotante, la cabecera del chat y el
  «Preguntar» de la página, si lo hay.
- **Pidiéndolo por escrito**: «ponme a Bufy». El modelo tiene la herramienta `muneco` y la
  respuesta trae `muneco`, con lo que la página lo cambia en el momento.
- El asistente se llama como el muñeco que lleva puesto: va en el contexto de cada pregunta, no
  en el recetario.

## El aviso

Al entrar, el bocadillo de hola dice que se puede cambiar el muñeco. Lo decide el servidor:

- solo si el usuario no ha elegido nunca ninguno;
- un día distinto cada vez;
- **tres veces como mucho**. Después no se dice más.

## Dónde vive

En DynamoDB, en `MUNECO#<correo>`, con `{"muneco", "elegido", "avisos", "ultimo_aviso"}`. Si
no hay nada, sale Vendi. La clave sale de la sesión, como la memoria (docs/75): nadie ve ni
cambia el de otro.

Va por `POST /api/pregunta`:

- `{"muneco": "ver"}` devuelve `{muneco, avisar}`. Si `avisar` es verdadero, ya cuenta como aviso
  dado.
- `{"muneco": "bufy"}` lo elige.

Ninguna de las dos es una pregunta: no llaman al modelo, no gastan y no cuentan en el límite del
día. La página guarda el muñeco en la pestaña (sessionStorage) para no volver a pedirlo en cada
página, y lo borra al salir.
