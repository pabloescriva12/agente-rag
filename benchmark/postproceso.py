"""
Postproceso del benchmark: lee benchmark/benchmark.json y produce un
benchmark.md con tabla resumen + tabla detallada por pregunta.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean


def cargar_resultados(ruta: Path) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def agregar_por_modelo(resultados_modelo: list[dict]) -> dict:
    """Calcula promedios y aciertos para un modelo."""
    if not resultados_modelo or isinstance(resultados_modelo, dict):
        return {}

    sin_error = [r for r in resultados_modelo if r.get("error") is None]
    if not sin_error:
        return {"error_total": True}

    aciertos = sum(1 for r in sin_error if r.get("acierto_subjetivo") == "acierto")
    parciales = sum(1 for r in sin_error if r.get("acierto_subjetivo") == "parcial")
    fallos = sum(1 for r in sin_error if r.get("acierto_subjetivo") == "fallo")

    return {
        "n_preguntas": len(sin_error),
        "tokens_entrada_avg": round(mean(
            r["metricas"].get("tokens_entrada", 0) for r in sin_error
        ), 1),
        "tokens_salida_avg": round(mean(
            r["metricas"].get("tokens_salida", 0) for r in sin_error
        ), 1),
        "latencia_avg_s": round(mean(
            r["metricas"].get("latencia_total_s", 0) for r in sin_error
        ), 2),
        "tokens_por_segundo_avg": round(mean(
            r["metricas"].get("tokens_por_segundo", 0) for r in sin_error
        ), 1),
        "aciertos": aciertos,
        "parciales": parciales,
        "fallos": fallos,
        "tasa_acierto_pct": round(100 * aciertos / len(sin_error), 1),
    }


def construir_markdown(datos: dict) -> str:
    out: list[str] = []
    out.append("# Resultados del benchmark\n")
    out.append(f"**Fecha de ejecucion:** {datos.get('fecha', 'desconocida')}\n")
    out.append(f"**Set de preguntas:** {datos.get('set_preguntas')}\n")

    # Tabla resumen por modelo
    out.append("\n## Tabla resumen por modelo\n")
    out.append("| Modelo | Servidor | N preg. | Tok. in (avg) | Tok. out (avg) | Latencia (s, avg) | tok/s (avg) | Aciertos | Parciales | Fallos | Tasa acierto |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")

    for alias, res in datos["resultados"].items():
        if isinstance(res, dict) and "error" in res:
            out.append(f"| {alias} | - | - | - | - | - | - | - | - | - | ERROR: {res['error'][:30]} |")
            continue
        agr = agregar_por_modelo(res)
        if not agr or agr.get("error_total"):
            out.append(f"| {alias} | - | 0 | - | - | - | - | - | - | - | - |")
            continue
        # Buscar servidor en la lista de modelos
        servidor = next(
            (m["servidor"] for m in datos.get("modelos", []) if m["alias"] == alias),
            "?",
        )
        out.append(
            f"| {alias} | {servidor} | {agr['n_preguntas']} | "
            f"{agr['tokens_entrada_avg']} | {agr['tokens_salida_avg']} | "
            f"{agr['latencia_avg_s']} | {agr['tokens_por_segundo_avg']} | "
            f"{agr['aciertos']} | {agr['parciales']} | {agr['fallos']} | "
            f"{agr['tasa_acierto_pct']}% |"
        )

    # Detalle por pregunta
    out.append("\n## Detalle por pregunta\n")
    out.append("Acierto subjetivo: A = acierto, P = parcial, F = fallo, E = error.\n")

    # Cabecera con los modelos como columnas
    aliases = list(datos["resultados"].keys())
    cabecera = "| ID | Pregunta | Categoria | " + " | ".join(aliases) + " |"
    sep = "|---|---|---|" + "|".join(["---"] * len(aliases)) + "|"
    out.append(cabecera)
    out.append(sep)

    # Agrupar resultados por pregunta
    ids_preguntas: list[str] = []
    textos: dict[str, str] = {}
    categorias: dict[str, str] = {}
    for alias, res in datos["resultados"].items():
        if isinstance(res, list):
            for r in res:
                pid = r["pregunta_id"]
                if pid not in ids_preguntas:
                    ids_preguntas.append(pid)
                    textos[pid] = r["pregunta"][:50]
                    categorias[pid] = r["categoria"]

    mapa = {"acierto": "A", "parcial": "P", "fallo": "F", "error": "E"}
    for pid in ids_preguntas:
        fila = [pid, textos.get(pid, ""), categorias.get(pid, "")]
        for alias in aliases:
            res = datos["resultados"][alias]
            if not isinstance(res, list):
                fila.append("?")
                continue
            r = next((x for x in res if x["pregunta_id"] == pid), None)
            if not r:
                fila.append("?")
            else:
                fila.append(mapa.get(r.get("acierto_subjetivo", ""), "?"))
        out.append("| " + " | ".join(fila) + " |")

    # Interpretacion
    out.append("\n## Interpretacion\n")
    out.append(
        "Esta seccion se rellena tras inspeccionar los datos. Puntos a comentar:\n"
        "\n"
        "- **Velocidad**: comparativa de latencia y tokens/s. En general los modelos PoliGPT\n"
        "  son mas grandes (mayor latencia pero respuestas mas elaboradas) y los locales\n"
        "  responden mas rapido pero con mas variabilidad.\n"
        "- **Acierto en factuales**: si la diferencia es minima, justifica usar el local\n"
        "  por coste / disponibilidad sin VPN.\n"
        "- **Contradicciones (P09, P10)**: aqui es donde se separa el grano de la paja.\n"
        "  Los modelos pequenyos tienden a coger un solo lado de la contradiccion. Los\n"
        "  mas grandes a veces detectan ambas. Comentar concretamente que se ve.\n"
        "- **Fuera de ambito (P11, P12)**: el prompt anti-alucinacion deberia llevar a\n"
        "  todos los modelos a rechazar. Si alguno responde, indicar cual e investigar.\n"
        "- **Eleccion final**: en base a todo lo anterior, justificar que modelo se elige\n"
        "  para la entrega final.\n"
    )

    return "\n".join(out) + "\n"


def main():
    base = Path(__file__).parent
    entrada = base / "benchmark.json"
    salida = base / "benchmark.md"

    if not entrada.exists():
        print(f"ERROR: no se encuentra {entrada}")
        print("Ejecuta primero 'python benchmark/benchmark.py'")
        return

    datos = cargar_resultados(entrada)
    md = construir_markdown(datos)

    with open(salida, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Markdown generado en {salida}")


if __name__ == "__main__":
    main()
