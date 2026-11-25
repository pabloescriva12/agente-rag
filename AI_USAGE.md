# Uso de herramientas de IA

Este documento declara qué herramientas de IA hemos usado durante la práctica,
sobre qué ficheros y con cuánta revisión por nuestra parte. Intentamos ser
concretos por herramienta y por fichero, como pide el enunciado.

## Resumen

Hemos usado IA sobre todo como ayuda para programar y para redactar, no para que
nos hiciera la práctica. Las decisiones de diseño (arquitectura, troceado,
elección de modelo, preguntas del benchmark) las hemos tomado nosotros. Donde
más nos ha ayudado la IA es en el código repetitivo, en encontrar fallos y en
darle forma a la prosa del informe.

## Detalle por herramienta

### ChatGPT (GPT-4o) — uso ocasional por web

- En `consultar.py` lo usamos para entender cómo sacar `prompt_eval_count` y
  `eval_duration` de la respuesta de Ollama y cómo pasar `eval_duration`
  (en nanosegundos) a tokens por segundo. La función `_generar_ollama` la
  escribimos nosotros después, pero las métricas vienen de esa consulta.
- En `benchmark.py` nos ayudó con la idea de recargar el módulo `consultar`
  entre iteraciones para cambiar de modelo. El código final lo reescribimos.
- En el informe lo usamos para revisar ortografía y poco más.

### Claude — apoyo puntual al principio

- Nos enseñó el patrón de la regex para trocear los ficheros Q:/A:, que luego
  adaptamos a nuestro caso (la heurística del 50% para decidir si un fichero es
  Q:/A: o narrativo).
- La estructura de secciones del README la sugirió Claude; el contenido lo
  pusimos nosotros.

### Claude — sesión de depuración del código

Cuando el agente ya funcionaba pero respondía mal a varias preguntas, usamos
Claude (su interfaz de chat) para encontrar y corregir los fallos. Fue un trabajo
de ida y vuelta: nosotros ejecutábamos las preguntas en la consola y en el
frontend, le pasábamos lo que salía y entre todos íbamos ajustando.

En `consultar.py`, de aquí salieron estos cambios:

- La forma de recuperar los fragmentos: en vez de coger solo los 5 más cercanos,
  recuperar más candidatos y seleccionar garantizando que haya varias fuentes
  (función `_seleccionar_diverso`). Esto arregló las preguntas con información
  contradictoria.
- Añadir los prefijos que nomic-embed-text espera en los embeddings.
- Cargar el `.env` (antes no se leía).
- Quitar las cabeceras de sección que se colaban dentro de los trozos Q:/A:.
- Comparar la frase de "no lo sé" sin tildes para que la detección funcione
  siempre.
- Reescribir el prompt del sistema (manejo de contradicciones, responder a lo
  que se pregunta y no escribir nombres de fichero en la respuesta).
- Un filtro (`_limpiar_respuesta`) que quita de la respuesta los nombres de
  fichero que a veces se le colaban al modelo.

En `requirements.txt`: subir ChromaDB a la versión 1.x para que instalara en
Windows sin tener que compilar nada.

Para ser honestos: el código de estas funciones lo escribió la IA. Nosotros lo
hemos leído, entendido y, sobre todo, validado probando una batería de preguntas
con los dos modelos (3b y 7b) y comprobando que el comportamiento era el
correcto. No lo hemos tecleado línea a línea, pero sabemos qué hace cada parte y
por qué está, que es lo que tendremos que explicar en la defensa. La IA también
nos ayudó a redactar el informe a partir de nuestras decisiones y resultados.

### GitHub Copilot — autocompletado en el editor

Activo durante el desarrollo, pero solo para autocompletados cortos (nombres de
variables, imports, completar diccionarios). Nada "grande" salió de Copilot sin
que escribiéramos el contexto y revisáramos la sugerencia.

## Qué NO hemos hecho con IA

- No le hemos pedido a ningún modelo que "haga la práctica entera". En la defensa
  tenemos que poder explicarlo todo.
- No hemos copiado el informe de ningún chat: está escrito con nuestras palabras
  y refleja decisiones que tomamos nosotros.

## Sobre el benchmark

El script `benchmark.py` es reproducible: con Ollama y los modelos descargados
se puede volver a ejecutar. Los números absolutos dependen del hardware, pero el
orden relativo entre modelos debería mantenerse. Los resultados de
`benchmark.json` deben salir de una ejecución real de los modelos antes de la
entrega.
