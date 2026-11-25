# Agente RAG - Asistente DNI Valencia

Practica de la asignatura **Inteligencia Artificial** del Grado en Tecnologias
Interactivas (UPV). Es un agente RAG (*Retrieval-Augmented Generation*) que
responde preguntas sobre la asociacion juvenil **Damos Nuestra Ilusion**
(DNI Valencia) usando su documentacion oficial.

**Autores:** Pablo Escriva y Carlos Carrasco

---

## Que hace

Dada una pregunta:

1. La convierte en un vector con un modelo de embeddings.
2. Busca los fragmentos mas parecidos en el corpus de DNI (16 .txt).
3. Selecciona los que pasan al modelo asegurando que haya varias fuentes
   distintas (esto importa para las preguntas con informacion contradictoria).
4. Monta un prompt con la pregunta y esos fragmentos como contexto.
5. Se lo envia al modelo de lenguaje (Ollama en local).
6. Devuelve la respuesta junto con las fuentes de las que ha salido.

Si la informacion no esta en el corpus, responde literalmente
*"No tengo esa informacion en mis fuentes"*. **No inventa.**

## Bandas y extras

- **Banda 5**: el pipeline RAG funciona de punta a punta y no inventa.
- **Banda 6**: cada respuesta indica de que ficheros sale la informacion.
- **Extra Frontend**: interfaz web con Streamlit (`frontend/app.py`).
- Arquitectura **single-agent**: todo el flujo vive en `consultar.py`.

No reclamamos la banda 7: preparamos un script de benchmark (`benchmark/`) pero
no llegamos a ejecutar la comparativa completa de cuatro modelos, asi que no la
declaramos. Ver `features.json`.

---

## Como ejecutarlo

### 1) Requisitos

- Python 3.10 o superior
- [Ollama](https://ollama.com) instalado y arrancado

### 2) Instalacion

```bash
cd agente-rag-gti

# Entorno virtual
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1        # Windows (PowerShell)

# Dependencias
pip install -r requirements.txt

# Modelos de Ollama
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 3) Variables de entorno (opcional)

Por defecto funciona con Ollama en local sin tocar nada. Si quieres cambiar el
modelo o el backend, copia `.env.example` a `.env` y editalo.

### 4) Probar el agente

```bash
# Linea de comandos
python consultar.py "¿Donde son los desayunos solidarios?"

# Frontend (Streamlit)
streamlit run frontend/app.py
```

La primera consulta **indexa el corpus** y tarda un poco (sobre un minuto en
CPU). Las siguientes reutilizan el indice guardado en `chroma_db/`.

---

## Estructura del repositorio

```
agente-rag-gti/
├── consultar.py            # toda la logica del agente (opcion A del contrato)
├── features.json           # declaracion de bandas y extras
├── requirements.txt
├── .env.example
├── .gitignore
│
├── base_conocimiento/      # 16 .txt del corpus de DNI (sin modificar)
│
├── frontend/
│   └── app.py              # interfaz Streamlit
│
├── benchmark/
│   ├── preguntas.json      # set de preguntas de prueba
│   ├── benchmark.py        # script que pasa el agente por varios modelos
│   └── postproceso.py      # genera una tabla a partir de los resultados
│
├── GRUPO.md                # integrantes y reparto del trabajo
├── AI_USAGE.md             # uso de herramientas de IA
├── informe.pdf             # informe de la practica
└── README.md               # este fichero
```

---

## Decisiones principales

El detalle esta en `informe.pdf`. En resumen:

- **Chunking** hibrido: los ficheros con formato `Q:/A:` los troceamos
  manteniendo cada par como un fragmento; los narrativos con
  `RecursiveCharacterTextSplitter` (700 caracteres, 120 de solape). Salen 272
  fragmentos en total.
- **Embeddings**: `nomic-embed-text` por Ollama, con los prefijos que el modelo
  espera para consultas y documentos.
- **Vector store**: ChromaDB persistente en disco, con distancia coseno.
- **Recuperacion**: en vez de coger solo los mas cercanos, recuperamos varios
  candidatos y elegimos garantizando que aparezcan varias fuentes. Asi, en las
  preguntas con datos contradictorios, el modelo ve las dos versiones.
- **Modelo por defecto**: `qwen2.5:7b` por Ollama. Probamos tambien `qwen2.5:3b`,
  que es mas rapido pero falla mas (se deja contradicciones o responde a otra
  cosa); el 7b es mas lento en CPU pero acierta bastante mas.
- **Prompt anti-alucinacion**: responde solo desde el contexto, muestra las dos
  versiones cuando las fuentes se contradicen y no escribe nombres de fichero en
  el texto (esos van en la lista de fuentes).

---

## Limitaciones conocidas

- **Sin memoria de conversacion**: cada pregunta se trata por separado.
- **Preguntas comparativas**: las del tipo "¿en que se diferencian X e Y?"
  fallan porque la palabra "diferencia" domina la busqueda y no se recuperan los
  trozos que describen cada cosa. Preguntando de otra forma ("¿que proyectos hay?")
  si responde bien. Mejora futura: busqueda hibrida (BM25 + semantica) o hacer
  varias busquedas y juntarlas.
- **Depende del modelo**: con un modelo mas grande o con GPU casi todos estos
  fallos desaparecerian.

---

## Profesores

Vicente Rivas Monferrer y Juan M. Alberola ([email removed])
