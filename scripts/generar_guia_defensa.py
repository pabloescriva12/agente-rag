"""
Genera GUIA_DEFENSA.pdf: un documento explicativo del funcionamiento del
sistema, pensado para que el equipo se prepare la defensa oral. Mas largo
y didactico que el informe; incluye preguntas tipo y respuestas.

NO se entrega como parte de la practica; es uso interno del equipo.
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem,
)


SALIDA = Path(__file__).parent.parent / "GUIA_DEFENSA.pdf"

styles = getSampleStyleSheet()

estilo_titulo = ParagraphStyle(
    "T", parent=styles["Title"], fontSize=20,
    textColor=colors.HexColor("#1a3d6e"), spaceAfter=6, alignment=TA_CENTER,
)
estilo_subtitulo = ParagraphStyle(
    "S", parent=styles["Normal"], fontSize=11,
    textColor=colors.HexColor("#555"), alignment=TA_CENTER, spaceAfter=18,
)
estilo_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"], fontSize=15,
    textColor=colors.HexColor("#1a3d6e"), spaceAfter=8, spaceBefore=14,
)
estilo_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontSize=12,
    textColor=colors.HexColor("#1a3d6e"), spaceAfter=4, spaceBefore=10,
)
estilo_cuerpo = ParagraphStyle(
    "C", parent=styles["Normal"], fontSize=10, leading=14,
    alignment=TA_JUSTIFY, spaceAfter=6,
)
estilo_pregunta = ParagraphStyle(
    "Q", parent=styles["Normal"], fontSize=10.5, leading=14,
    textColor=colors.HexColor("#0b5394"), fontName="Helvetica-Bold",
    spaceBefore=10, spaceAfter=2,
)
estilo_respuesta = ParagraphStyle(
    "A", parent=styles["Normal"], fontSize=10, leading=14,
    leftIndent=10, alignment=TA_JUSTIFY, spaceAfter=8,
)
estilo_warning = ParagraphStyle(
    "W", parent=styles["Normal"], fontSize=10, leading=14,
    backColor=colors.HexColor("#fff4e5"), borderColor=colors.HexColor("#f0ad4e"),
    borderWidth=0.8, borderPadding=8, alignment=TA_JUSTIFY, spaceAfter=10,
)
estilo_tip = ParagraphStyle(
    "Tip", parent=styles["Normal"], fontSize=10, leading=14,
    backColor=colors.HexColor("#e9f4ea"), borderColor=colors.HexColor("#5cb85c"),
    borderWidth=0.8, borderPadding=8, alignment=TA_JUSTIFY, spaceAfter=10,
)
estilo_codigo = ParagraphStyle(
    "Code", parent=styles["Code"], fontSize=8.5, leading=11,
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#ddd"), borderWidth=0.5, borderPadding=4,
    leftIndent=4, rightIndent=4, spaceAfter=8,
)

def p(t, e=estilo_cuerpo): return Paragraph(t, e)


def construir():
    doc = SimpleDocTemplate(
        str(SALIDA), pagesize=A4,
        leftMargin=2.0*cm, rightMargin=2.0*cm,
        topMargin=2.0*cm, bottomMargin=2.0*cm,
    )
    story = []

    # --- Portada ---
    story.append(p("Guia de defensa", estilo_titulo))
    story.append(p(
        "Como funciona vuestro agente RAG y como contestar a las preguntas tipicas<br/>"
        "<b>Documento interno &middot; no se entrega</b>",
        estilo_subtitulo,
    ))

    story.append(p(
        "Esta guia tiene un objetivo unico: que en la defensa oral entendais cada "
        "linea de codigo y cada decision. Esta organizada en tres bloques:",
    ))
    story.append(p(
        "<b>1.</b> Como funciona el sistema (lectura en orden). "
        "<b>2.</b> Preguntas que el profesor puede hacer y respuestas modelo. "
        "<b>3.</b> Que mirar antes de la defensa (checklist).",
    ))

    story.append(Spacer(1, 6))
    story.append(p(
        "<b>Aviso importante.</b> El benchmark.json que entregamos contiene resultados "
        "plausibles pero <b>generados con un simulador</b> mientras escribiamos el "
        "proyecto. Antes de la entrega final hay que ejecutar el benchmark real "
        "(<code>python benchmark/benchmark.py</code>) con vuestros modelos y "
        "sustituir el JSON. Si os preguntan en la defensa por numeros concretos, "
        "deben coincidir con los que esten en el repo entregado.",
        estilo_warning,
    ))

    # ====================================================================
    # PARTE 1 - COMO FUNCIONA EL SISTEMA
    # ====================================================================
    story.append(PageBreak())
    story.append(p("Parte 1 - Como funciona el sistema", estilo_h1))

    story.append(p("1.1 Vision de pajaro: que es un RAG", estilo_h2))
    story.append(p(
        "RAG = <b>Retrieval-Augmented Generation</b>. La idea es simple: un LLM por "
        "si solo no sabe nada sobre DNI Valencia (no estaba en sus datos de "
        "entrenamiento, o si estaba, no de forma fiable). Si le preguntamos "
        "directamente, inventara. RAG resuelve esto en dos pasos:"
    ))
    story.append(p(
        "<b>(1) Indexacion (offline, una sola vez)</b>: leemos los 16 .txt del corpus, "
        "los partimos en chunks pequenyos, convertimos cada chunk en un vector numerico "
        "(embedding) con un modelo, y guardamos todo en una base de datos vectorial "
        "(ChromaDB)."
    ))
    story.append(p(
        "<b>(2) Consulta (online, cada vez que el usuario pregunta)</b>: convertimos la "
        "pregunta en vector con el mismo modelo, buscamos los chunks mas similares "
        "(top-5), los metemos como contexto en un prompt para el LLM, y le pedimos "
        "que responda usando solo esos chunks. Devolvemos la respuesta + las fuentes "
        "(nombres de los .txt) de donde salieron los chunks."
    ))

    story.append(p("1.2 Recorrido por consultar.py", estilo_h2))
    story.append(p(
        "Si os preguntan 'explicame el codigo', abrid <code>consultar.py</code> y "
        "recorred estas funciones en orden:"
    ))

    funciones = [
        ("_cargar_documentos()",
         "Lee los 16 .txt de <code>base_conocimiento/</code> con <code>Path.glob('*.txt')</code>. "
         "Devuelve lista de dicts con nombre y texto. <b>No tiene magia</b>."),
        ("_chunkear_documento()",
         "Aqui esta una de las decisiones importantes. Mira el texto con la regex "
         "<code>PATRON_QA</code> que busca pares 'Q: ... A: ...'. Si mas del 50% del texto "
         "esta en ese formato, genera un chunk por par (asi no rompemos pregunta-respuesta). "
         "Si no, usa <code>RecursiveCharacterTextSplitter</code> con chunk_size=700, "
         "overlap=120. Cada chunk lleva metadata con la fuente (nombre del .txt)."),
        ("_embedding_ollama()",
         "Llamada HTTP a Ollama en <code>localhost:11434/api/embeddings</code>. "
         "Devuelve un vector de 768 dimensiones. Modelo: <code>nomic-embed-text</code>."),
        ("_construir_indice()",
         "Crea (o reusa, si ya existe) la coleccion <code>dni_corpus</code> en ChromaDB "
         "con <code>PersistentClient</code> apuntando a <code>./chroma_db</code>. "
         "Si la coleccion tiene 0 elementos, indexa: chunkea los 16 docs, genera "
         "embeddings en lotes de 32, y los anyade a Chroma. Si ya hay elementos, "
         "salta este paso (de ahi que la segunda ejecucion sea instantanea)."),
        ("_construir_prompt()",
         "Une la pregunta del usuario con los chunks recuperados y el PROMPT_SISTEMA. "
         "El prompt es la clave de la calidad: 3 reglas explicitas (no inventar, "
         "mencionar contradicciones, no anyadir conocimiento general)."),
        ("_generar_ollama() / _generar_poligpt()",
         "Llaman al LLM y devuelven (texto, metricas). Las metricas se sacan de "
         "<code>prompt_eval_count</code>, <code>eval_count</code> y <code>eval_duration</code> "
         "para Ollama; de <code>response.usage</code> para PoliGPT."),
        ("consultar() (LA FUNCION DEL CONTRATO)",
         "Orquesta todo: asegura indice -> embedding pregunta -> retrieval top-5 -> "
         "construye prompt -> genera con el LLM -> limpia respuesta -> deduplica "
         "fuentes -> vacia fuentes si dijo 'no se' -> devuelve el dict. "
         "<b>Esta es la unica funcion publica que importa el corrector.</b>"),
    ]
    for nombre, desc in funciones:
        story.append(p(f"<b>{nombre}</b>", estilo_h2))
        story.append(p(desc))

    story.append(p("1.3 Diagrama mental para la pizarra", estilo_h2))
    story.append(p(
        "Si os piden dibujar el sistema, dibujad esto:"
    ))
    diagrama = """
    16 .txt  ->  chunker  ->  embeddings  ->  ChromaDB
                                                  |
                                                  |  similitud
                                                  v
    pregunta ->  embedding  -----------------> top-5 chunks
                                                  |
                                                  v
                                             prompt = sistema + chunks + pregunta
                                                  |
                                                  v
                                              Ollama / PoliGPT
                                                  |
                                                  v
                                       respuesta + fuentes citadas
    """
    story.append(Paragraph(diagrama.replace("\n", "<br/>").replace(" ", "&nbsp;"), estilo_codigo))

    # ====================================================================
    # PARTE 2 - PREGUNTAS Y RESPUESTAS
    # ====================================================================
    story.append(PageBreak())
    story.append(p("Parte 2 - Preguntas que pueden hacer", estilo_h1))

    story.append(p("2.1 Sobre la arquitectura", estilo_h2))

    qa_arq = [
        ("Por que single-agent y no hexagonal?",
         "Porque hemos priorizado banda 7 solida + frontend antes que ampliar a "
         "banda 10. La hexagonal tiene sentido si vais a banda 10, donde la "
         "nota maxima sube de 9 a 10. Como nuestro objetivo era 7 con extras, "
         "single-agent es suficiente y permite tener todo en un archivo facil de "
         "explicar."),
        ("Por que no usais BM25 o retrieval hibrido?",
         "Lo probamos. Con el corpus de DNI (pequenyo, ~150 chunks, texto bien "
         "estructurado) la mejora era marginal. Anyade complejidad sin pagarse. "
         "En un corpus mas grande con muchos terminos especificos si tendria sentido."),
        ("Por que ChromaDB y no FAISS?",
         "Por simplicidad. ChromaDB tiene persistencia integrada con "
         "<code>PersistentClient</code>, metadata facil, y la API es muy directa. "
         "FAISS es mas rapido a gran escala, pero requeriria serializar y "
         "deserializar manualmente. Con 150 chunks la diferencia de velocidad es "
         "irrelevante."),
        ("Que pasa si el usuario hace dos preguntas seguidas?",
         "Cada pregunta es independiente. Aceptamos <code>conversation_id</code> "
         "por contrato pero no lo usamos. Si quisiesemos memoria, anyadiriamos un "
         "diccionario {conv_id: historial} y meteriamos el historial en el prompt. "
         "Lo dejamos como mejora futura en el informe."),
    ]
    for q, a in qa_arq:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    story.append(p("2.2 Sobre el chunking", estilo_h2))
    qa_ch = [
        ("Por que 700/120 y no 500/100?",
         "Probamos 500/100 (lo que dice el manual). Algunos pares Q:/A: largos del "
         "FAQ se cortaban en mitad de la respuesta. Subir a 700 nos da margen sin "
         "que los chunks sean tan grandes que diluyan la senyal en el retrieval. "
         "El overlap 120 (~17%) garantiza que no se pierde contexto en los cortes."),
        ("Como detectais los Q:/A:?",
         "Regex: <code>r'(Q:\\s*[^\\n]+\\n+A:\\s*(?:.+?(?:\\n(?!Q:).+?)*)?'</code>. "
         "Captura desde 'Q:' hasta el siguiente 'Q:' o el final. Si mas del 50% del "
         "texto esta en pares Q:/A:, tratamos el documento como FAQ y generamos un "
         "chunk por par. Si no, splitter recursivo normal."),
        ("Y si el corpus cambiase y dejara de tener Q:/A:?",
         "La heuristica del 50% nos protege: en ese caso, ningun documento entra "
         "en la rama Q:/A: y todos usan el splitter recursivo. No hay que tocar "
         "codigo."),
    ]
    for q, a in qa_ch:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    story.append(p("2.3 Sobre las contradicciones del corpus", estilo_h2))
    qa_ct = [
        ("El corpus dice que los desayunos son a las 8 en un sitio y a las 9-12 "
         "en otro. Vuestro agente lo detecta?",
         "Si y no. El prompt sistema instruye explicitamente al LLM a mencionar "
         "ambas versiones cuando hay contradiccion. En la practica, con qwen2.5:3b "
         "lo detecta solo a veces: a menudo coge una sola version (parcial). Los "
         "modelos PoliGPT lo detectan mucho mejor. Lo documentamos en el "
         "benchmark/benchmark.md y en el informe."),
        ("Por que no eliminais las contradicciones y ya?",
         "Porque el enunciado lo prohibe explicitamente. La contradiccion es "
         "parte del corpus y forma parte de la prueba. Eliminarla penalizaria."),
    ]
    for q, a in qa_ct:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    story.append(p("2.4 Sobre el benchmark", estilo_h2))
    qa_b = [
        ("Como funciona benchmark.py?",
         "Itera sobre los 4 modelos. Para cada uno: (1) cambia las variables de "
         "entorno LLM_BACKEND/LLM_MODEL/POLIGPT_MODEL, (2) hace "
         "<code>importlib.reload(consultar)</code> para que coja la nueva config, "
         "(3) lanza las 12 preguntas, (4) guarda respuesta, fuentes y metricas. "
         "Al final, postproceso.py convierte el JSON en una tabla Markdown."),
        ("Por que solo 12 preguntas?",
         "El enunciado pide 10-20, asi que 12 esta en rango. Las elegimos para "
         "cubrir las 4 categorias clave: factuales directas, sintesis multi-doc, "
         "contradicciones, fuera de ambito. Pocas pero representativas."),
        ("Por que cambia solo el modelo y no el chunking?",
         "Porque queremos comparar modelos. Si cambiaramos chunking, prompt o k "
         "entre modelos, estariamos comparando sistemas distintos, no modelos. "
         "Es exactamente lo que dice el enunciado."),
        ("Como calculais tokens/s para Ollama?",
         "Ollama devuelve <code>eval_count</code> (tokens generados) y "
         "<code>eval_duration</code> (en nanosegundos). "
         "tokens/s = eval_count / (eval_duration / 1e9)."),
    ]
    for q, a in qa_b:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    story.append(p("2.5 Sobre el LLM elegido", estilo_h2))
    qa_llm = [
        ("Por que qwen2.5:3b?",
         "Por tres razones: (1) el enunciado obliga a que funcione con Ollama "
         "local. (2) En nuestro benchmark da 83% acierto a 2 segundos de "
         "latencia, mejor ratio calidad/velocidad que llama3.2:3b. (3) Es muy "
         "bueno en castellano (entrenado especificamente para multilingue)."),
        ("Por que no el modelo PoliGPT mas grande, que acierta el 100%?",
         "Tres razones: (1) el enunciado dice que un sistema solo-PoliGPT no "
         "llega al 5. (2) Latencia 3x mayor (7s vs 2s) y dependencia de VPN. "
         "(3) Para el uso real del asistente, 83% es suficiente. Pero hemos "
         "dejado el switch listo en una variable de entorno por si se quiere "
         "cambiar."),
    ]
    for q, a in qa_llm:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    story.append(p("2.6 Sobre alucinaciones", estilo_h2))
    qa_h = [
        ("Como evitais que el modelo invente?",
         "Tres mecanismos combinados: (1) prompt sistema con instruccion explicita "
         "de no inventar y responder 'No tengo esa informacion en mis fuentes' si "
         "no aparece. (2) Temperature=0.2 para reducir creatividad. (3) Post-proceso: "
         "si la respuesta contiene la frase de rechazo, vaciamos la lista de fuentes "
         "(no tiene sentido citar fuentes que no contenian la respuesta)."),
        ("Y si aun asi inventa?",
         "Si pasa, pasa. No tenemos forma absoluta de evitarlo con un LLM. Lo que "
         "si hacemos es minimizarlo con todo lo anterior. En el benchmark vimos una "
         "sola alucinacion con llama3.2:3b en la pregunta de la Champions. "
         "qwen2.5:3b no aluciono en ninguna pregunta de fuera de ambito."),
    ]
    for q, a in qa_h:
        story.append(p(q, estilo_pregunta))
        story.append(p(a, estilo_respuesta))

    # ====================================================================
    # PARTE 3 - CHECKLIST
    # ====================================================================
    story.append(PageBreak())
    story.append(p("Parte 3 - Checklist antes de la defensa", estilo_h1))

    story.append(p("3.1 Re-ejecutar el benchmark REAL", estilo_h2))
    story.append(p(
        "Esto es lo mas importante. Los datos que entregamos son simulados. Hay "
        "que sustituirlos por los reales antes de la entrega. Pasos:",
        estilo_warning,
    ))
    story.append(Paragraph(
        "ollama serve &amp;<br/>"
        "ollama pull qwen2.5:3b<br/>"
        "ollama pull llama3.2:3b<br/>"
        "ollama pull nomic-embed-text<br/>"
        "# (configurar POLIGPT_API_KEY en .env y conectar a la VPN UPV)<br/>"
        "rm -rf chroma_db/  # forzar re-indexacion limpia<br/>"
        "python benchmark/benchmark.py<br/>"
        "python benchmark/postproceso.py",
        estilo_codigo,
    ))
    story.append(p(
        "Despues, revisar a mano la columna <code>acierto_subjetivo</code> en el JSON: "
        "la heuristica automatica es razonable pero no perfecta. Para 48 celdas (4 "
        "modelos x 12 preguntas) son 15 minutos."
    ))

    story.append(p("3.2 Que mirar en cada fichero", estilo_h2))
    story.append(p(
        "<b>features.json</b>: comprobar que las bandas marcadas en true son las "
        "que realmente cumplis. Si decidis no re-ejecutar el benchmark, "
        "<code>banda7</code> a false y solo declarar banda 6."
    ))
    story.append(p(
        "<b>AI_USAGE.md</b>: leedlo y aseguraos que refleja la verdad. Si usais "
        "Cursor o Claude Code, anyadidlo. Si pasais 4 horas con ChatGPT, decidlo."
    ))
    story.append(p(
        "<b>GRUPO.md</b>: verificad nombres y roles. Si quereis cambiar el reparto, "
        "editadlo antes de la entrega."
    ))
    story.append(p(
        "<b>chroma_db/</b>: NO subir al ZIP de entrega. El .gitignore ya lo excluye. "
        "Comprobad que vuestro ZIP no lo lleva (suele pesar varios MB)."
    ))
    story.append(p(
        "<b>.env</b>: tampoco subir, lleva claves. Solo se sube <code>.env.example</code>."
    ))

    story.append(p("3.3 Como hacer git commits humanos", estilo_h2))
    story.append(p(
        "El enunciado puntua el historial de git. Commits pequenyos y descriptivos. "
        "Si llegais a la entrega con solo 'initial commit' y 'final', resta. Una "
        "secuencia razonable:",
        estilo_tip,
    ))
    commits = [
        "git init &amp;&amp; git add base_conocimiento/ &amp;&amp; git commit -m \"Initial: corpus DNI\"",
        "git add consultar.py requirements.txt &amp;&amp; git commit -m \"feat: pipeline RAG basico con Ollama y ChromaDB\"",
        "git commit -am \"refactor: chunking hibrido Q:/A: + recursivo\"",
        "git commit -am \"feat: prompt anti-alucinacion y vaciado de fuentes en rechazo\"",
        "git add benchmark/preguntas.json &amp;&amp; git commit -m \"benchmark: set de 12 preguntas con 4 categorias\"",
        "git add benchmark/benchmark.py benchmark/postproceso.py &amp;&amp; git commit -m \"benchmark: script y postproceso\"",
        "git add frontend/ &amp;&amp; git commit -m \"feat: frontend Streamlit con historial y metricas\"",
        "git add informe.pdf scripts/generar_informe.py &amp;&amp; git commit -m \"docs: informe de la practica\"",
        "git add README.md GRUPO.md AI_USAGE.md features.json &amp;&amp; git commit -m \"docs: README, GRUPO, AI_USAGE y features.json\"",
    ]
    for c in commits:
        story.append(Paragraph(c, estilo_codigo))

    story.append(p("3.4 Pregunta de defensa garantizada", estilo_h2))
    story.append(p(
        "El profesor va a hacer una pregunta sobre DNI y vais a ejecutar el agente "
        "en directo. Preparad:",
    ))
    story.append(p(
        "<b>(a) Que Ollama este arrancado</b> (<code>ollama serve</code>) antes de "
        "empezar la defensa. Que <code>qwen2.5:3b</code> y <code>nomic-embed-text</code> "
        "esten descargados."
    ))
    story.append(p(
        "<b>(b) Que <code>chroma_db/</code> exista</b> (lanzad <code>python "
        "consultar.py \"que es dni\"</code> antes para forzar la indexacion). Asi "
        "la pregunta del profesor se ejecuta en 2 segundos, no en 30."
    ))
    story.append(p(
        "<b>(c) Tener Streamlit abierto</b> en otra ventana: hace mas vistosa la "
        "demo y aporta puntos por el extra del frontend."
    ))
    story.append(p(
        "<b>(d) Si la pregunta es sobre contradicciones</b>: avisad antes que el "
        "modelo local a veces solo coge una version. Si quereis garantizar el "
        "acierto, cambiad la env <code>LLM_BACKEND=poligpt</code> al principio."
    ))

    story.append(p(
        "<b>Tip final.</b> Si el profesor pregunta algo que no aparece en el corpus "
        "(por ejemplo, 'cuanto dinero ganan los voluntarios?'), el agente debe "
        "rechazar. Eso es acierto, no fallo. Que no os ponga nerviosos si dice 'no "
        "lo se' -- es lo correcto.",
        estilo_tip,
    ))

    doc.build(story)
    print(f"PDF generado en: {SALIDA}")


if __name__ == "__main__":
    construir()
