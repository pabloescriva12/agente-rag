"""
Agente RAG sobre el corpus de la asociacion DNI Valencia.

Contrato (opcion A del enunciado):
    from consultar import consultar
    consultar(pregunta: str, conversation_id: str | None = None) -> dict

El diccionario devuelto contiene: respuesta, fuentes, chunks, metricas, trazas.

La indexacion se hace una unica vez al primer import; las consultas posteriores
reutilizan el vector store persistente en ./chroma_db.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import chromadb
import requests
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Carga el .env (si existe y si python-dotenv esta instalado) ANTES de leer las
# variables de entorno. Antes el .env no se cargaba nunca, asi que cambiar de
# backend a PoliGPT desde el .env no surtia efecto.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # sin python-dotenv seguimos usando las variables del sistema

# ----------------------------------------------------------------------------
# Configuracion. Se puede sobreescribir con variables de entorno (.env)
# ----------------------------------------------------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api")
# El default ahora coincide con README y .env.example. Elegimos qwen2.5:7b
# como modelo de uso: es mas lento que el 3b en CPU pero responde de forma
# notablemente mas fiable (contradicciones, faceta de la pregunta, sintesis).
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

# nomic-embed-text fue entrenado con prefijos de tarea ("search_query:" para la
# consulta y "search_document:" para los documentos). Sin ellos la calidad de
# recuperacion baja de forma apreciable. Activamos los prefijos automaticamente
# si el modelo de embeddings es de la familia nomic.
USAR_PREFIJOS_NOMIC = "nomic" in EMBED_MODEL.lower()

# Backend del LLM: "ollama" (por defecto) o "poligpt". Para el benchmark
# nos viene bien poder cambiarlo via env sin tocar codigo.
LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama").lower()

POLIGPT_BASE_URL = os.environ.get("POLIGPT_BASE_URL", "https://api.poligpt.upv.es/v1")
POLIGPT_API_KEY = os.environ.get("POLIGPT_API_KEY", "")
POLIGPT_MODEL = os.environ.get("POLIGPT_MODEL", "poligpt")

BASE_DIR = Path(__file__).parent
CORPUS_DIR = BASE_DIR / "base_conocimiento"
CHROMA_DIR = BASE_DIR / "chroma_db"

# Parametros de chunking. Probamos al principio con 500/100 (lo que recomienda
# el manual) pero los chunks Q:/A: se cortaban a veces por la mitad asi que
# subimos a 700/120 + pre-procesado del FAQ.
CHUNK_SIZE = 700
CHUNK_OVERLAP = 120

TOP_K = 5  # cuantos chunks pasamos finalmente al LLM

# Recuperamos mas candidatos de los que pasamos al LLM para luego seleccionar
# con diversidad de fuentes. Clave para las contradicciones (si pedimos pocos
# por distancia, los mas cercanos pueden venir todos del mismo lado).
# NOTA (limitacion conocida): en preguntas COMPARATIVAS del tipo "¿en que se
# diferencian X e Y?", el termino "diferencia" copa la recuperacion semantica y
# los trozos que describen X e Y no entran en los candidatos. Subir TOP_K no lo
# soluciona. La mejora natural seria recuperacion hibrida (BM25 + semantica) o
# multi-consulta (buscar X e Y por separado); ver informe.
N_CANDIDATOS = 15

# Frase de rechazo cuando no encontramos info. El enunciado pide algo asi.
FRASE_NO_LO_SE = "No tengo esa informacion en mis fuentes."


# ----------------------------------------------------------------------------
# Carga del corpus + pre-procesado de los Q:/A:
# ----------------------------------------------------------------------------
def _cargar_documentos() -> list[dict[str, str]]:
    """Lee los 16 .txt de base_conocimiento/ y devuelve una lista de dicts."""
    docs = []
    for path in sorted(CORPUS_DIR.glob("*.txt")):
        docs.append({
            "nombre": path.name,
            "texto": path.read_text(encoding="utf-8"),
        })
    return docs


# Regex para detectar pares Q:/A:. Captura desde 'Q:' hasta el siguiente 'Q:'
# o el final del texto. Lo usamos para agrupar cada pregunta con su respuesta
# como un chunk natural y que el retriever no nos los parta a la mitad.
# La primera version no era greedy y se quedaba con la primera linea de A:
# nada mas; con esta cogemos el cuerpo completo.
PATRON_QA = re.compile(r"Q:\s*.+?(?=\n+Q:|\Z)", re.DOTALL)


def _chunkear_documento(texto: str, nombre: str) -> list[dict[str, Any]]:
    """
    Devuelve los chunks del documento.

    Para ficheros con formato Q:/A: agrupamos pregunta+respuesta como una
    unidad. Para el resto usamos el splitter de LangChain por longitud.
    """
    pares_qa = PATRON_QA.findall(texto)

    # Heuristica: si la mayor parte del texto esta en formato Q:/A:, vamos por
    # esa via. Si no, usamos el splitter generico.
    longitud_total = len(texto)
    longitud_qa = sum(len(p) for p in pares_qa)

    chunks: list[dict[str, Any]] = []

    if pares_qa and longitud_qa / max(longitud_total, 1) > 0.5:
        # Documento mayoritariamente Q:/A:
        for i, par in enumerate(pares_qa):
            # El lookahead del regex se extiende hasta el siguiente "Q:", asi que
            # los titulos de seccion ("===== ... =====") que hay entre bloques se
            # quedan pegados al final del chunk anterior. Los quitamos para no
            # meter ruido en el contexto.
            par_limpio = re.sub(r"\n\s*=+[^\n]*=+\s*$", "", par.strip()).strip()
            if par_limpio:
                chunks.append({
                    "texto": par_limpio,
                    "fuente": nombre,
                    "indice": i,
                    "tipo": "qa",
                })
    else:
        # Documento narrativo: usamos splitter recursivo
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        for i, trozo in enumerate(splitter.split_text(texto)):
            if trozo.strip():
                chunks.append({
                    "texto": trozo.strip(),
                    "fuente": nombre,
                    "indice": i,
                    "tipo": "narrativo",
                })

    return chunks


# ----------------------------------------------------------------------------
# Cliente Ollama (embeddings + generacion)
# ----------------------------------------------------------------------------
def _embedding_ollama(texto: str, tipo: str = "document") -> list[float]:
    """
    Pide a Ollama el vector de embedding de un texto.

    Args:
        texto: el texto a vectorizar.
        tipo: "document" para los chunks del corpus, "query" para la pregunta.
              Solo afecta si el modelo es de la familia nomic (que usa prefijos
              de tarea).
    """
    if USAR_PREFIJOS_NOMIC:
        prefijo = "search_query: " if tipo == "query" else "search_document: "
        texto = prefijo + texto

    resp = requests.post(
        f"{OLLAMA_URL}/embeddings",
        json={"model": EMBED_MODEL, "prompt": texto},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def _generar_ollama(prompt: str) -> tuple[str, dict[str, Any]]:
    """Genera con Ollama y devuelve (texto, metricas)."""
    t0 = time.time()
    resp = requests.post(
        f"{OLLAMA_URL}/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 500},
        },
        timeout=300,
    )
    latencia = time.time() - t0
    resp.raise_for_status()
    datos = resp.json()

    # Las metricas de Ollama vienen en la propia respuesta
    metricas = {
        "tokens_entrada": datos.get("prompt_eval_count", 0),
        "tokens_salida": datos.get("eval_count", 0),
        "latencia_s": round(latencia, 3),
        "modelo": LLM_MODEL,
        "backend": "ollama",
    }
    # tokens/s lo calculamos a partir de eval_duration (nanosegundos)
    eval_duration_ns = datos.get("eval_duration", 0)
    if eval_duration_ns > 0 and metricas["tokens_salida"] > 0:
        metricas["tokens_por_segundo"] = round(
            metricas["tokens_salida"] / (eval_duration_ns / 1e9), 2
        )
    else:
        metricas["tokens_por_segundo"] = 0.0

    return datos["response"], metricas


def _generar_poligpt(prompt: str) -> tuple[str, dict[str, Any]]:
    """Genera con PoliGPT (OpenAI-compatible) y devuelve (texto, metricas)."""
    # Importamos aqui para que el proyecto pueda funcionar sin tener el paquete
    # openai instalado si solo se usa Ollama.
    from openai import OpenAI

    if not POLIGPT_API_KEY:
        raise RuntimeError(
            "POLIGPT_API_KEY no esta configurada. "
            "Define la variable de entorno o anyade .env"
        )

    client = OpenAI(base_url=POLIGPT_BASE_URL, api_key=POLIGPT_API_KEY)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=POLIGPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
    )
    latencia = time.time() - t0
    texto = resp.choices[0].message.content or ""

    usage = getattr(resp, "usage", None)
    tokens_entrada = getattr(usage, "prompt_tokens", 0) if usage else 0
    tokens_salida = getattr(usage, "completion_tokens", 0) if usage else 0

    metricas = {
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "latencia_s": round(latencia, 3),
        "modelo": POLIGPT_MODEL,
        "backend": "poligpt",
        "tokens_por_segundo": round(tokens_salida / latencia, 2) if latencia > 0 else 0,
    }
    return texto, metricas


# ----------------------------------------------------------------------------
# Indexacion (se ejecuta una sola vez)
# ----------------------------------------------------------------------------
_coleccion = None  # cache modulo: la primera consulta indexa, las demas reusan


def _construir_indice():
    """
    Indexa los 16 .txt si la coleccion de Chroma esta vacia.

    Lo hacemos perezosamente: la primera llamada a consultar() dispara la
    indexacion, las siguientes solo consultan.
    """
    global _coleccion

    if _coleccion is not None:
        return _coleccion

    CHROMA_DIR.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    coleccion = client.get_or_create_collection(
        # v2: el espacio de embeddings cambio al anyadir los prefijos nomic y al
        # limpiar los headers, asi que usamos un nombre nuevo para forzar una
        # reindexacion limpia y no mezclar vectores viejos con nuevos.
        name="dni_corpus_v2",
        metadata={"hnsw:space": "cosine"},  # similitud coseno
    )

    # Si ya hay chunks indexados, no re-indexamos.
    if coleccion.count() > 0:
        _coleccion = coleccion
        return coleccion

    print("[indexacion] coleccion vacia, indexando corpus...")

    documentos = _cargar_documentos()
    todos_los_chunks: list[dict[str, Any]] = []
    for doc in documentos:
        todos_los_chunks.extend(_chunkear_documento(doc["texto"], doc["nombre"]))

    print(f"[indexacion] {len(documentos)} documentos -> {len(todos_los_chunks)} chunks")

    # Indexamos en lotes pequenyos para no saturar Ollama
    LOTE = 32
    for i in range(0, len(todos_los_chunks), LOTE):
        sub = todos_los_chunks[i : i + LOTE]
        ids = [f"{c['fuente']}__{c['indice']}__{c['tipo']}" for c in sub]
        textos = [c["texto"] for c in sub]
        metadatos = [
            {"fuente": c["fuente"], "indice": c["indice"], "tipo": c["tipo"]}
            for c in sub
        ]
        embeddings = [_embedding_ollama(t, tipo="document") for t in textos]

        coleccion.add(
            ids=ids,
            embeddings=embeddings,
            documents=textos,
            metadatas=metadatos,
        )

    print(f"[indexacion] terminada. {coleccion.count()} chunks en el indice.")
    _coleccion = coleccion
    return coleccion


# ----------------------------------------------------------------------------
# Construccion del prompt
# ----------------------------------------------------------------------------
PROMPT_SISTEMA = """Eres el asistente de la asociacion DNI Valencia (Damos Nuestra Ilusion).
Respondes en espanol, de forma clara, natural y concisa, usando UNICAMENTE la
informacion del contexto que aparece mas abajo. Sigue estas reglas:

1. Construye la respuesta a partir del contexto. PUEDES combinar y resumir la
   informacion de varios fragmentos para responder (por ejemplo, para explicar
   en que se diferencian dos proyectos o que requisitos hacen falta). Lo que NO
   puedes es anyadir datos que no esten en el contexto, ni inventar cifras,
   horarios, telefonos, direcciones o el significado de siglas.

2. Responde solo a lo que se pregunta: si preguntan "donde", da el lugar; si
   preguntan "cuando" o "a que hora", da el momento; etc.

3. CONTRADICCIONES: si el contexto ofrece dos valores distintos para el mismo
   dato que se pregunta (por ejemplo dos horas distintas, o dos lugares
   distintos, para la misma actividad), no elijas uno solo ni los promedies:
   menciona AMBOS y aclara que las fuentes no coinciden. No senyales
   contradicciones en datos por los que no se te ha preguntado, ni inventes una
   discrepancia que no este en el contexto.

4. Solo si en el contexto NO hay nada relevante para la pregunta, responde
   literalmente: "{frase_no_lo_se}". Si el contexto si trae informacion sobre
   el tema, respondela aunque no este redactada igual que la pregunta.

5. Escribe en lenguaje natural. No incluyas en tu respuesta las etiquetas Q: ni
   A:, ni numeros de fragmento, ni nombres de archivo: las fuentes se muestran
   por separado."""


def _construir_prompt(
    pregunta: str,
    chunks: list[str],
    fuentes: list[str] | None = None,
) -> str:
    """
    Une la pregunta y los chunks recuperados en un prompt unico.

    Cada fragmento se etiqueta con el archivo del que procede, para que el LLM
    pueda citar la fuente y, sobre todo, distinguir versiones contradictorias
    ("segun X.txt... pero segun Y.txt...").
    """
    if fuentes is None:
        fuentes = ["?"] * len(chunks)

    contexto = "\n\n---\n\n".join(
        f"[fuente: {fuentes[i]}]\n{c}"
        for i, c in enumerate(chunks)
    )
    sistema = PROMPT_SISTEMA.format(frase_no_lo_se=FRASE_NO_LO_SE)
    return f"""{sistema}

CONTEXTO:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta}

RESPUESTA:"""


# ----------------------------------------------------------------------------
# Limpieza de la respuesta y seleccion de chunks
# ----------------------------------------------------------------------------
def _limpiar_respuesta(texto: str) -> str:
    """
    Red de seguridad: quita de la respuesta los nombres de archivo del corpus y
    las referencias a "fragmento N" que a veces se le cuelan al modelo. Las
    fuentes deben ir solo en la lista aparte, no dentro del texto. Sustituye por
    expresiones neutras para no romper la gramatica.
    """
    import re as _re

    texto = _re.sub(
        r"\b(del|al)\s+(?:archivos?|fragmentos?)\s+\d{2}_\w+\.txt",
        lambda m: ("de" if m.group(1).lower() == "del" else "a") + " una de las fuentes",
        texto, flags=_re.I,
    )
    texto = _re.sub(
        r"\b(?:el|la|los|las)\s+(?:archivos?|fragmentos?)\s+\d{2}_\w+\.txt",
        "una de las fuentes", texto, flags=_re.I,
    )
    texto = _re.sub(
        r"\b(?:archivos?|fragmentos?)\s+\d{2}_\w+\.txt",
        "una de las fuentes", texto, flags=_re.I,
    )
    texto = _re.sub(
        r"\b(?:el|los|en el|en los)?\s*fragmentos?\s+\d+(?:\s*y\s*\d+)*",
        "el contexto", texto, flags=_re.I,
    )
    texto = _re.sub(r"\(?\b\d{2}_\w+\.txt\b\)?", "una de las fuentes", texto)
    texto = _re.sub(r"\bel contexto\s+del\s+contexto\b", "el contexto", texto, flags=_re.I)
    texto = _re.sub(r"\b(una de las fuentes)(\s+\1)+\b", r"\1", texto, flags=_re.I)
    texto = _re.sub(r"\s{2,}", " ", texto).strip()
    return texto


def _normalizar(texto: str) -> str:
    """Minusculas + sin tildes, para comparaciones robustas."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _seleccionar_diverso(
    docs: list[str],
    metas: list[dict[str, Any]],
    distancias: list[float],
    k: int,
    min_fuentes: int = 3,
) -> tuple[list[str], list[dict[str, Any]], list[float]]:
    """
    Selecciona k chunks priorizando la cercania (distancia) pero garantizando un
    minimo de fuentes distintas.

    Asi las preguntas de SINTESIS pueden usar varios fragmentos del archivo mas
    relevante (p. ej. tres trozos de 10_proyectos.txt para explicar RESIS vs
    COLES), mientras que las preguntas con CONTRADICCIONES siguen viendo al menos
    varias fuentes, de modo que ambas versiones lleguen al modelo.
    """
    from collections import Counter

    orden = sorted(range(len(docs)), key=lambda i: distancias[i])
    elegidos = orden[:k]  # top-k por distancia (puede repetir fuente)

    def n_fuentes(idx: list[int]) -> int:
        return len({metas[i].get("fuente") for i in idx})

    # Si no hay suficientes fuentes distintas, cambiamos los peores duplicados
    # por el mejor chunk de fuentes aun no representadas.
    if n_fuentes(elegidos) < min_fuentes:
        for i in orden[k:]:
            if n_fuentes(elegidos) >= min_fuentes:
                break
            presentes = {metas[j].get("fuente") for j in elegidos}
            if metas[i].get("fuente") in presentes:
                continue
            cuenta = Counter(metas[j].get("fuente") for j in elegidos)
            quitables = [
                j for j in sorted(elegidos, key=lambda x: -distancias[x])
                if cuenta[metas[j].get("fuente")] > 1
            ]
            if quitables:
                elegidos.remove(quitables[0])
                elegidos.append(i)

    elegidos.sort(key=lambda i: distancias[i])

    return (
        [docs[i] for i in elegidos],
        [metas[i] for i in elegidos],
        [distancias[i] for i in elegidos],
    )


# ----------------------------------------------------------------------------
# Funcion principal (contrato del enunciado)
# ----------------------------------------------------------------------------
def consultar(pregunta: str, conversation_id: str | None = None) -> dict:
    """
    Procesa una pregunta y devuelve respuesta + fuentes + metricas.

    Args:
        pregunta: texto de la pregunta del usuario.
        conversation_id: opcional, por ahora no lo usamos (sin memoria de chat).

    Returns:
        dict con claves: respuesta, fuentes, chunks, metricas, trazas.
    """
    t_total = time.time()
    trazas: list[dict[str, Any]] = []

    # 1) Asegurar que el indice esta listo
    coleccion = _construir_indice()
    trazas.append({"paso": "indexacion", "estado": "ok"})

    # 2) Embedding de la pregunta + retrieval
    t0 = time.time()
    embedding_pregunta = _embedding_ollama(pregunta, tipo="query")
    # Pedimos mas candidatos de los que pasaremos al LLM y luego seleccionamos
    # con diversidad de fuentes (clave para contradicciones y sintesis multi-doc).
    n_pool = min(N_CANDIDATOS, coleccion.count())
    resultados = coleccion.query(
        query_embeddings=[embedding_pregunta],
        n_results=n_pool,
    )
    t_retrieval = time.time() - t0

    cand_docs = resultados["documents"][0]
    cand_metas = resultados["metadatas"][0]
    cand_dists = resultados.get("distances", [[0.0] * len(cand_docs)])[0]

    docs_recuperados, metadatas_recuperados, distancias = _seleccionar_diverso(
        cand_docs, cand_metas, [float(d) for d in cand_dists], TOP_K
    )

    trazas.append({
        "paso": "retrieval",
        "k": TOP_K,
        "candidatos": len(cand_docs),
        "fuentes_distintas": len({m.get("fuente") for m in metadatas_recuperados}),
        "latencia_s": round(t_retrieval, 3),
    })

    # 3) Construir prompt (cada fragmento etiquetado con su archivo fuente)
    fuentes_por_chunk = [m.get("fuente", "?") for m in metadatas_recuperados]
    prompt = _construir_prompt(pregunta, docs_recuperados, fuentes_por_chunk)
    trazas.append({"paso": "prompt", "longitud_chars": len(prompt)})

    # 4) Generacion con el backend que toque
    if LLM_BACKEND == "poligpt":
        texto_respuesta, metricas_llm = _generar_poligpt(prompt)
    else:
        texto_respuesta, metricas_llm = _generar_ollama(prompt)

    trazas.append({"paso": "generacion", **metricas_llm})

    # 5) Limpieza de la respuesta (a veces el LLM repite el prefijo "RESPUESTA:")
    texto_respuesta = texto_respuesta.strip()
    for prefijo in ("RESPUESTA:", "Respuesta:", "respuesta:"):
        if texto_respuesta.startswith(prefijo):
            texto_respuesta = texto_respuesta[len(prefijo):].strip()

    # Quitar nombres de archivo / referencias a "fragmento N" que se cuelen en
    # el texto (deben ir solo en la lista de fuentes).
    texto_respuesta = _limpiar_respuesta(texto_respuesta)

    # 6) Fuentes: deduplicadas pero preservando el orden de aparicion
    fuentes_ordenadas: list[str] = []
    vistas: set[str] = set()
    for meta in metadatas_recuperados:
        f = meta["fuente"]
        if f not in vistas:
            fuentes_ordenadas.append(f)
            vistas.add(f)

    # Si el modelo dijo que no sabe, no tiene sentido citar fuentes que no
    # contenian la informacion. Vaciamos la lista en ese caso. Comparamos sin
    # tildes ni mayusculas: el modelo suele responder "informacion" con tilde
    # ("informacion") y antes la comparacion fallaba y citaba fuentes igualmente.
    marcador_rechazo = _normalizar(FRASE_NO_LO_SE.split(".")[0])
    if marcador_rechazo in _normalizar(texto_respuesta):
        fuentes_ordenadas = []

    metricas_globales = {
        **metricas_llm,
        "latencia_total_s": round(time.time() - t_total, 3),
        "latencia_retrieval_s": round(t_retrieval, 3),
        "chunks_recuperados": len(docs_recuperados),
        "distancias": [round(float(d), 4) for d in distancias],
    }

    return {
        "respuesta": texto_respuesta,
        "fuentes": fuentes_ordenadas,
        "chunks": list(docs_recuperados),
        "metricas": metricas_globales,
        "trazas": trazas,
    }


# ----------------------------------------------------------------------------
# Permite probar desde la linea de comandos: python consultar.py "tu pregunta"
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python consultar.py \"tu pregunta\"")
        sys.exit(1)

    pregunta = " ".join(sys.argv[1:])
    resultado = consultar(pregunta)
    print("\n=== RESPUESTA ===")
    print(resultado["respuesta"])
    print("\n=== FUENTES ===")
    for f in resultado["fuentes"]:
        print(f"  - {f}")
    print("\n=== METRICAS ===")
    print(json.dumps(resultado["metricas"], indent=2, ensure_ascii=False))
