# Grupo

Asignatura: **Inteligencia Artificial**
Practica: Agente RAG - Asistente Inteligente de Conocimiento
Titulacion: Grado en Tecnologias Interactivas

## Integrantes

| Nombre | Rol principal | Responsabilidades concretas |
|---|---|---|
| **Pablo Escriva** | Pipeline RAG + frontend | Carga del corpus, chunking (Q:/A: + recursivo), indexacion en ChromaDB, prompt anti-alucinacion, frontend Streamlit. |
| **Carlos Carrasco** | Benchmark + informe | Diseno del set de preguntas, script de benchmark con 4 modelos, postproceso a Markdown, redaccion del informe y analisis de resultados. |

## Reparto del trabajo

Hemos trabajado en pareja durante todas las sesiones, pero cada uno ha liderado
una parte. Las decisiones de arquitectura (single-agent vs hexagonal, eleccion
de modelo final, parametros de chunking) se han tomado conjuntamente despues de
probar varias alternativas.

El historial de git refleja esta division: Pablo concentra los commits sobre
`consultar.py`, `frontend/` y todo lo relativo al pipeline RAG; Carlos los de
`benchmark/`, el informe y las preguntas de evaluacion.
