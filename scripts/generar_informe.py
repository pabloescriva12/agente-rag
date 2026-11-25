"""
Genera informe.pdf con el contenido del informe de la practica.
Lo escribimos como script aparte para poder iterar rapido y reutilizarlo si
hay que regenerar el PDF tras editar texto.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)


SALIDA = Path(__file__).parent.parent / "informe.pdf"

# Estilos
styles = getSampleStyleSheet()

estilo_titulo = ParagraphStyle(
    "TituloPrincipal",
    parent=styles["Title"],
    fontSize=18,
    textColor=colors.HexColor("#1a3d6e"),
    spaceAfter=6,
    alignment=TA_CENTER,
)
estilo_subtitulo = ParagraphStyle(
    "Subtitulo",
    parent=styles["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#555555"),
    alignment=TA_CENTER,
    spaceAfter=18,
)
estilo_h1 = ParagraphStyle(
    "H1",
    parent=styles["Heading1"],
    fontSize=14,
    textColor=colors.HexColor("#1a3d6e"),
    spaceAfter=8,
    spaceBefore=14,
)
estilo_h2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=11.5,
    textColor=colors.HexColor("#1a3d6e"),
    spaceAfter=4,
    spaceBefore=10,
)
estilo_cuerpo = ParagraphStyle(
    "Cuerpo",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)
estilo_codigo = ParagraphStyle(
    "Codigo",
    parent=styles["Code"],
    fontSize=8.5,
    leading=11,
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#dddddd"),
    borderWidth=0.5,
    borderPadding=4,
    leftIndent=4,
    rightIndent=4,
    spaceAfter=8,
)
estilo_cita = ParagraphStyle(
    "Cita",
    parent=styles["Normal"],
    fontSize=9.5,
    leading=13,
    leftIndent=14,
    textColor=colors.HexColor("#444444"),
    fontName="Helvetica-Oblique",
    spaceAfter=6,
)


def p(texto, estilo=estilo_cuerpo):
    return Paragraph(texto, estilo)


def construir():
    doc = SimpleDocTemplate(
        str(SALIDA),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    story = []

    # Portada
    story.append(p("Agente RAG: Asistente Inteligente de Conocimiento", estilo_titulo))
    story.append(p(
        "Practica de Inteligencia Artificial &middot; Grado en Tecnologias Interactivas &middot; UPV<br/>"
        "<b>Pablo Escriva &amp; Carlos Carrasco</b>",
        estilo_subtitulo,
    ))

    # 1. Introduccion
    story.append(p("1. Introduccion y eleccion de arquitectura", estilo_h1))
    story.append(p(
        "Esta practica construye un agente RAG (<i>Retrieval-Augmented Generation</i>) "
        "capaz de responder preguntas sobre la asociacion juvenil <b>DNI Valencia</b> "
        "(Damos Nuestra Ilusion). El corpus son 16 ficheros .txt con informacion oficial "
        "de la asociacion: filosofia, proyectos (desayunos solidarios, RESIS, COLES), "
        "logistica y dos FAQ extensos."
    ))
    story.append(p(
        "Hemos optado por una arquitectura <b>single-agent</b> con el contrato de la "
        "<i>opcion A</i>: un unico fichero <code>consultar.py</code> en la raiz del repo "
        "expone la funcion <code>consultar(pregunta, conversation_id)</code> que devuelve "
        "el diccionario que pide el enunciado. Hemos descartado la arquitectura hexagonal "
        "porque, tras leer el manual y valorarlo con tiempo, decidimos centrar el esfuerzo "
        "en el benchmark riguroso de 4 modelos (banda 7) y en un frontend usable (extra +1.5), "
        "en lugar de ampliar a banda 10. Nuestro objetivo realista era una banda 7 solida."
    ))

    # 2. Pipeline
    story.append(p("2. Pipeline de una consulta", estilo_h1))
    story.append(p(
        "El flujo de procesamiento sigue el pipeline descrito en el enunciado:"
    ))
    pipeline = [
        ["#", "Paso", "Implementacion en consultar.py"],
        ["1", "Carga del corpus", "<code>_cargar_documentos()</code> lee los 16 .txt de <code>base_conocimiento/</code>."],
        ["2", "Chunking", "<code>_chunkear_documento()</code>: hibrido Q:/A: + recursivo."],
        ["3", "Embeddings", "<code>_embedding_ollama()</code> con <code>nomic-embed-text</code> (768 dim)."],
        ["4", "Indexacion", "ChromaDB persistente en <code>./chroma_db</code>, metrica coseno."],
        ["5", "Embedding consulta", "Mismo modelo de embeddings que la indexacion."],
        ["6", "Retrieval", "Top-k semantico (k=5) sobre la coleccion."],
        ["7", "Construccion prompt", "<code>_construir_prompt()</code> + system prompt anti-alucinacion."],
        ["8", "Generacion LLM", "<code>_generar_ollama()</code> o <code>_generar_poligpt()</code>."],
        ["9", "Formato salida", "respuesta + fuentes + chunks + metricas + trazas."],
    ]
    tabla_pipe = Table(
        [[p(c, estilo_cuerpo) if i > 0 else p(f"<b>{c}</b>", estilo_cuerpo)
          for c in fila] for i, fila in enumerate(pipeline)],
        colWidths=[0.8 * cm, 3.8 * cm, 12.0 * cm],
    )
    tabla_pipe.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tabla_pipe)
    story.append(Spacer(1, 8))

    # 3. Decisiones tecnicas
    story.append(p("3. Decisiones tecnicas y justificacion", estilo_h1))

    story.append(p("3.1 Chunking hibrido Q:/A: + recursivo", estilo_h2))
    story.append(p(
        "Una primera version usaba <code>RecursiveCharacterTextSplitter</code> uniformemente "
        "con <code>chunk_size=500</code>, <code>overlap=100</code> (lo que recomienda el manual). "
        "El problema: el corpus de DNI tiene muchos pares <b>Q:/A:</b> en el FAQ y en "
        "<code>15_desayunos_100_preguntas.txt</code>, y el splitter cortaba a veces entre la "
        "pregunta y la respuesta, lo que rompia chunks que conceptualmente son una unidad. "
        "Probamos a subir <code>chunk_size</code>, pero entonces los documentos narrativos "
        "se quedaban en chunks demasiado grandes. La solucion: detectar con un regex "
        "(<code>PATRON_QA</code>) que documento es mayoritariamente Q:/A: (heuristica: "
        "&gt;50% del texto en pares) y, si lo es, generar un chunk por cada par. "
        "Para los narrativos seguimos con el splitter recursivo, ahora con "
        "<code>chunk_size=700</code> y <code>overlap=120</code>."
    ))

    story.append(p("3.2 Embeddings y vector store", estilo_h2))
    story.append(p(
        "Usamos <code>nomic-embed-text</code> via Ollama por su soporte multilingue "
        "(el corpus esta en castellano), 768 dimensiones y porque no requiere "
        "dependencia externa: si Ollama esta arrancado, los embeddings funcionan. "
        "Como vector store elegimos ChromaDB con <code>PersistentClient</code> en "
        "<code>./chroma_db</code>: persiste entre ejecuciones, la API es trivial y la "
        "metrica coseno funciona bien para embeddings normalizados. Indexar los ~272 chunks "
        "del corpus tarda unos 30 segundos en CPU; queda en cache para las siguientes consultas."
    ))

    story.append(p("3.3 Prompt anti-alucinacion y manejo de contradicciones", estilo_h2))
    story.append(p(
        "El system prompt explicita tres reglas: <b>(1)</b> responder solo desde el "
        "contexto, devolviendo 'No tengo esa informacion en mis fuentes' si no esta; "
        "<b>(2)</b> mencionar ambas versiones cuando hay contradicciones (el corpus "
        "contiene contradicciones intencionadas: por ejemplo, horario de los "
        "desayunos [schedule removed] vs [schedule removed]-[schedule removed]; ubicacion de COLES como [private location] "
        "vs biblioteca tutorizada); <b>(3)</b> no anyadir conocimiento general. Tras la "
        "generacion vaciamos la lista de fuentes citadas si la respuesta es de rechazo, "
        "para no citar archivos que no contenian realmente la respuesta."
    ))

    story.append(p("3.4 LLM por defecto y configurabilidad", estilo_h2))
    story.append(p(
        "Por defecto el agente usa <b>qwen2.5:3b</b> via Ollama local. Esa eleccion "
        "se defiende con datos en la seccion 4. Mediante variables de entorno "
        "(<code>LLM_BACKEND</code>, <code>LLM_MODEL</code>, <code>POLIGPT_MODEL</code>) "
        "se puede cambiar a otro modelo o a PoliGPT sin tocar codigo, lo que tambien "
        "facilita el script de benchmark."
    ))

    # 4. Benchmark
    story.append(p("4. Benchmark con 4 modelos (banda 7)", estilo_h1))
    story.append(p(
        "Set fijo de <b>12 preguntas</b> en <code>benchmark/preguntas.json</code>, "
        "agrupadas en cuatro categorias: factuales directas (P01-P05), sintesis "
        "multi-documento (P06-P08), contradicciones del corpus (P09-P10) y fuera de "
        "ambito (P11-P12). El pipeline RAG (chunking, k, prompt) se mantiene constante: "
        "solo cambia el modelo. Resultados resumidos:"
    ))
    bench = [
        ["Modelo", "Servidor", "Tok in", "Tok out", "Latencia (s)", "tok/s", "Acierto"],
        ["llama3.2:3b", "Ollama", "233", "88", "2.08", "45.4", "50.0%"],
        ["qwen2.5:3b", "Ollama", "240", "108", "2.21", "53.2", "83.3%"],
        ["poligpt-default", "PoliGPT", "246", "137", "4.13", "35.6", "91.7%"],
        ["poligpt-alt (gemma3:27b)", "PoliGPT", "237", "165", "6.93", "25.2", "100.0%"],
    ]
    tabla_b = Table(bench, colWidths=[4.0*cm, 1.8*cm, 1.6*cm, 1.7*cm, 2.2*cm, 1.5*cm, 1.8*cm])
    tabla_b.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(tabla_b)
    story.append(Spacer(1, 6))
    story.append(p(
        "<b>Lectura.</b> Los locales son ~2-3x mas rapidos en latencia total. "
        "En tasa de acierto, los PoliGPT van por delante, pero la distancia entre "
        "qwen2.5:3b (83%) y poligpt-default (92%) es menor que la diferencia en "
        "latencia y dependencia de VPN. Donde si pesa el modelo grande es en las "
        "preguntas con contradiccion: los PoliGPT detectan y citan las dos versiones, "
        "mientras que los locales tienden a coger una sola. La unica alucinacion "
        "observada en fuera-de-ambito es de llama3.2:3b en P12 (Champions 2024)."
    ))
    story.append(p(
        "<b>Eleccion final.</b> <code>qwen2.5:3b</code> via Ollama, por tres razones: "
        "(1) el enunciado exige que el sistema funcione con Ollama local, (2) la "
        "diferencia de calidad con poligpt-default es ~9 puntos, asumible para el "
        "uso real del asistente, y (3) la independencia de la VPN UPV es un valor "
        "practico en si mismo. Como respaldo dejamos preparado el camino a PoliGPT "
        "mediante <code>LLM_BACKEND=poligpt</code>."
    ))

    # 5. Resultados sobre preguntas de prueba
    story.append(p("5. Resultados sobre preguntas de prueba", estilo_h1))
    story.append(p(
        "Mas alla del benchmark cuantitativo, hicimos pruebas cualitativas con "
        "preguntas tipicas. Algunos resultados ilustrativos con el modelo elegido "
        "(qwen2.5:3b):"
    ))
    story.append(p(
        "<i>P: \u00bfQue es DNI? \u2192 R: 'DNI (Damos Nuestra Ilusion) es una asociacion "
        "juvenil de voluntariado en Valencia...' (fuentes: 04_filosofia_dni.txt, "
        "01_faq_dni.txt). Acierto claro.</i>",
        estilo_cita,
    ))
    story.append(p(
        "<i>P: \u00bfA que hora son los desayunos? \u2192 El modelo, en una de cada dos "
        "ejecuciones, coge solo la version de las [schedule removed] (parcial). En las otras, si "
        "se le hace una pregunta mas especifica (\u00bfHay informacion contradictoria...?) "
        "menciona ambas versiones. Esta es la limitacion mas visible del modelo "
        "local frente a los PoliGPT.</i>",
        estilo_cita,
    ))
    story.append(p(
        "<i>P: \u00bfCuanto cuesta el alquiler en Valencia? \u2192 R: 'No tengo esa "
        "informacion en mis fuentes.' Rechaza correctamente.</i>",
        estilo_cita,
    ))

    # 6. Dificultades
    story.append(p("6. Dificultades encontradas y como las resolvimos", estilo_h1))
    story.append(p(
        "<b>Chunks Q:/A: cortados.</b> Sintoma: el retrieval devolvia chunks con la "
        "pregunta pero sin la respuesta (o al reves). Resolucion: el chunker hibrido "
        "descrito en 3.1."
    ))
    story.append(p(
        "<b>Indexacion lenta al re-arrancar.</b> Sintoma: cada vez que abriamos "
        "Streamlit, el agente reindexaba (~30s). Resolucion: usar "
        "<code>PersistentClient</code> de Chroma y comprobar <code>coleccion.count() &gt; 0</code> "
        "antes de re-indexar."
    ))
    story.append(p(
        "<b>Cambiar de modelo entre iteraciones del benchmark.</b> Sintoma: el "
        "modulo <code>consultar</code> capturaba el modelo al primer import. Resolucion: "
        "<code>importlib.reload(consultar_mod)</code> tras cambiar las variables de entorno."
    ))
    story.append(p(
        "<b>Citar fuentes que no contenian la respuesta.</b> Sintoma: cuando el modelo "
        "respondia 'no se', seguia listando las fuentes recuperadas como si "
        "contuviesen la respuesta. Resolucion: detectamos la frase de rechazo y "
        "vaciamos la lista de fuentes en ese caso."
    ))

    # 7. Limitaciones y propuestas
    story.append(p("7. Analisis critico, limitaciones y propuestas de mejora", estilo_h1))
    story.append(p(
        "<b>Sin memoria de conversacion.</b> Aceptamos <code>conversation_id</code> por "
        "contrato pero no lo usamos. Para una version posterior anyadiriamos un historial "
        "por conversacion para resolver referencias anaforicas ('y los sabados?')."
    ))
    story.append(p(
        "<b>Sin re-ranking.</b> El top-k semantico simple basta para el corpus actual "
        "(pequeno, ~150 chunks). Para corpus mayores anyadiriamos un cross-encoder "
        "(p.ej. <code>BGE-reranker</code>) tras el retrieval inicial para mejorar la "
        "precision en el top-3."
    ))
    story.append(p(
        "<b>Sin retrieval hibrido.</b> Probamos BM25 + semantico (con "
        "<code>rank-bm25</code>) pero en nuestras 12 preguntas la mejora no compensaba "
        "la complejidad anyadida. En un corpus mas grande con terminos especificos "
        "(nombres propios, codigos) si seria util."
    ))
    story.append(p(
        "<b>Sin RAGAs.</b> Dejamos la banda 8 fuera del alcance para concentrar "
        "esfuerzo en el benchmark + frontend. Si retomamos el proyecto, lo natural "
        "seria anyadir las 4 metricas (<i>faithfulness, answer_relevancy, "
        "context_precision, context_recall</i>) sobre las mismas 12 preguntas y "
        "definir dos metricas propias orientadas a DNI: una de 'deteccion de "
        "contradiccion' (¿cita las dos versiones cuando existen?) y otra de "
        "'rechazo correcto' (¿rechaza las preguntas fuera de ambito sin alucinar?)."
    ))

    # 8. Conclusion
    story.append(p("8. Conclusion", estilo_h1))
    story.append(p(
        "Hemos construido un agente RAG funcional que cumple el contrato del "
        "enunciado, indexa los 16 .txt del corpus DNI, recupera contexto relevante "
        "con un retriever semantico sobre ChromaDB, genera respuestas con Ollama "
        "local (qwen2.5:3b por defecto, PoliGPT como respaldo configurable), cita "
        "las fuentes y se niega a inventar cuando la informacion no esta. El "
        "benchmark de 4 modelos justifica con datos por que elegimos qwen2.5:3b "
        "frente a alternativas mas pequenyas o mas grandes. El frontend Streamlit "
        "lo hace usable sin tocar la linea de comandos. La principal limitacion "
        "que reconocemos es la deteccion irregular de contradicciones del corpus "
        "con modelos pequenyos; si la entrega valorase especialmente este caso, "
        "valdria la pena migrar a un modelo mas grande via PoliGPT al menos para "
        "esa categoria de preguntas."
    ))

    doc.build(story)
    print(f"PDF generado en: {SALIDA}")


if __name__ == "__main__":
    construir()
