"""
Script de benchmark: ejecuta el mismo set de preguntas contra distintos modelos
y registra metricas. Genera benchmark/benchmark.json (datos crudos) y, mediante
postproceso, benchmark/benchmark.md (tabla legible).

Uso:
    python benchmark/benchmark.py            # ejecuta los 4 modelos por defecto
    python benchmark/benchmark.py --solo-locales   # solo Ollama (sin VPN)

IMPORTANTE: Solo cambia el modelo entre ejecuciones. Chunking, k, prompt y
retrieval se mantienen constantes (de lo contrario estariamos comparando
sistemas distintos, no modelos).
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path

# Permitir que el script se ejecute desde la raiz del repo
sys.path.insert(0, str(Path(__file__).parent.parent))

import consultar as consultar_mod  # type: ignore


# Configuracion de los 4 modelos. Los nombres de PoliGPT pueden cambiar segun
# lo que veas en /v1/models; ajusta si hace falta.
MODELOS = [
    {
        "alias": "llama3.2:3b",
        "backend": "ollama",
        "model_name": "llama3.2:3b",
        "servidor": "ollama_local",
    },
    {
        "alias": "qwen2.5:3b",
        "backend": "ollama",
        "model_name": "qwen2.5:3b",
        "servidor": "ollama_local",
    },
    {
        "alias": "poligpt-default",
        "backend": "poligpt",
        "model_name": "poligpt",
        "servidor": "poligpt",
    },
    {
        "alias": "poligpt-alt",
        "backend": "poligpt",
        "model_name": "gemma3:27b",  # cambiar segun lo que liste /v1/models
        "servidor": "poligpt",
    },
]


def cargar_preguntas() -> list[dict]:
    ruta = Path(__file__).parent / "preguntas.json"
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)["preguntas"]


def ejecutar_modelo(modelo: dict, preguntas: list[dict]) -> list[dict]:
    """Configura el backend y lanza todas las preguntas contra ese modelo."""
    # Reconfiguramos las variables de entorno y recargamos el modulo
    os.environ["LLM_BACKEND"] = modelo["backend"]
    if modelo["backend"] == "ollama":
        os.environ["LLM_MODEL"] = modelo["model_name"]
    else:
        os.environ["POLIGPT_MODEL"] = modelo["model_name"]

    # Recargar para que coja las nuevas vars
    importlib.reload(consultar_mod)

    resultados = []
    for pregunta in preguntas:
        print(f"  [{modelo['alias']}] {pregunta['id']}: {pregunta['texto'][:60]}...")
        try:
            t0 = time.time()
            r = consultar_mod.consultar(pregunta["texto"])
            tiempo = time.time() - t0
            resultados.append({
                "pregunta_id": pregunta["id"],
                "pregunta": pregunta["texto"],
                "categoria": pregunta["categoria"],
                "respuesta": r["respuesta"],
                "fuentes": r["fuentes"],
                "metricas": r["metricas"],
                "tiempo_total_s": round(tiempo, 3),
                "error": None,
            })
        except Exception as e:
            resultados.append({
                "pregunta_id": pregunta["id"],
                "pregunta": pregunta["texto"],
                "categoria": pregunta["categoria"],
                "respuesta": "",
                "fuentes": [],
                "metricas": {},
                "tiempo_total_s": 0,
                "error": str(e),
            })
    return resultados


def evaluar_acierto_subjetivo(respuesta: str, pregunta: dict) -> str:
    """
    Heuristica simple para etiquetar acierto/fallo automaticamente.
    Para el informe final lo revisamos a mano, esto es solo un primer pase.
    """
    if not respuesta:
        return "error"

    cat = pregunta["categoria"]
    resp_lower = respuesta.lower()

    if cat == "fuera_ambito":
        # Acierto = rechazar
        marcadores_rechazo = [
            "no tengo esa informacion",
            "no tengo esta informacion",
            "no lo se",
            "no aparece",
            "no esta en",
            "fuentes",
        ]
        return "acierto" if any(m in resp_lower for m in marcadores_rechazo) else "fallo"

    if cat == "dato_restringido":
        marcadores_privacidad = [
            "personas voluntarias inscritas",
            "voluntarios inscritos",
            "canales oficiales",
            "se comunican",
            "ubicacion concreta",
        ]
        return "acierto" if any(m in resp_lower for m in marcadores_privacidad) else "fallo"

    # Para factuales y sintesis: si la respuesta es no-trivial y cita fuentes, ok
    if len(respuesta) > 20:
        return "acierto"
    return "fallo"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--solo-locales",
        action="store_true",
        help="Ejecutar solo modelos Ollama (sin VPN/PoliGPT)",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "benchmark.json"),
        help="Ruta del JSON de salida",
    )
    args = parser.parse_args()

    preguntas = cargar_preguntas()
    print(f"Set de preguntas cargado: {len(preguntas)} preguntas\n")

    modelos_a_ejecutar = MODELOS
    if args.solo_locales:
        modelos_a_ejecutar = [m for m in MODELOS if m["backend"] == "ollama"]
        print(f"Modo solo-locales: {len(modelos_a_ejecutar)} modelos\n")

    todos_los_resultados = {
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "set_preguntas": "benchmark/preguntas.json",
        "modelos": [],
        "resultados": {},
    }

    for modelo in modelos_a_ejecutar:
        print(f"\n=== Ejecutando: {modelo['alias']} ({modelo['servidor']}) ===")
        try:
            resultados = ejecutar_modelo(modelo, preguntas)
            # Evaluacion subjetiva inicial (revisar a mano despues)
            for r in resultados:
                pregunta = next(p for p in preguntas if p["id"] == r["pregunta_id"])
                r["acierto_subjetivo"] = evaluar_acierto_subjetivo(
                    r["respuesta"], pregunta
                )
            todos_los_resultados["modelos"].append(modelo)
            todos_los_resultados["resultados"][modelo["alias"]] = resultados
        except Exception as e:
            print(f"  ERROR con {modelo['alias']}: {e}")
            todos_los_resultados["resultados"][modelo["alias"]] = {"error": str(e)}

    # Guardar JSON
    ruta_salida = Path(args.output)
    ruta_salida.parent.mkdir(exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(todos_los_resultados, f, indent=2, ensure_ascii=False)

    print(f"\nResultados guardados en {ruta_salida}")
    print("Ejecuta 'python benchmark/postproceso.py' para generar la tabla en Markdown.")


if __name__ == "__main__":
    main()
