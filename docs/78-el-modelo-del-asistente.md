# 78 · El modelo del asistente

Gabriele, 24-oct-2026, sobre gastar menos en Vendi: probar Haiku y Sonnet con las mismas
preguntas reales que Opus y dejar el modelo más barato que conteste bien.

## Cómo se elige

Por orden, gana el primero que haya:

1. **Una pregunta suelta de un administrador** puede llevar `"modelo"` en `POST /api/pregunta`.
   Sirve para comparar modelos con datos reales sin cambiárselo a nadie. Si lo manda otro perfil,
   o pide un modelo que no está en la lista, no se le hace caso y contesta el de siempre.
2. **La consola**: Plataforma > El asistente > **Modelo** > Guardar. Se guarda en la
   configuración (`asistente_modelo`) y vale desde la siguiente pregunta de cualquiera. Con
   «El de la Lambda» se borra.
3. **La variable `MODELO` de la Lambda** `digivend-asistente`, que es `claude-opus-5-5`.

El modelo se fija al empezar una pregunta: si se cambia mientras alguien espera una respuesta
por pasos, esa respuesta termina con el modelo con el que empezó.

La consola existe porque cambiar la variable de la Lambda pide un permiso de AWS
(`lambda:UpdateFunctionConfiguration`) que el usuario `claude-digivend` no tiene, y así el
cambio se hace y se deshace desde la propia plataforma, en un minuto.

## Los tres

| Modelo | Entrada | Salida | Cache, lectura | Cache, escritura |
|---|---|---|---|---|
| `claude-opus-5-5` | 4,00 | 20,00 | 0,20 | 5,00 |
| `claude-sonnet-5-5` | 2,00 | 10,00 | 0,20 | 2,50 |
| `claude-haiku-5-5` | 0,10 | 0,50 | 0,01 | 0,125 |

Son dólares por millón de tokens, y están en `autorizacion.MODELOS_ASISTENTE`. Haiku cobra todo
cinco veces más cuando una petición pasa de 100.000 tokens. El gasto que enseñan Utilizo
(docs/77) y la respuesta de cada pregunta se calcula con los precios del modelo que contestó.
Antes se calculaba siempre con los de Opus, que con otro modelo habría enseñado un gasto que no
era.

Haiku no tiene respaldo en el servidor (con `fallbacks` contesta 400), así que a Haiku se le
pregunta sin él. Cada vuelta deja en el log de la Lambda con qué modelo se hizo.

Se prueba con `python3 infra/api/test_asistente.py` y `python3 infra/api/test_api.py`.
