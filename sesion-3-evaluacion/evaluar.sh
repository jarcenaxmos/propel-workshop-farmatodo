#!/usr/bin/env bash
# Corre una evaluacion de la sesion III y muestra un resumen corto y legible.
#
# Uso (desde la raiz del repo, con el entorno virtual activado):
#   ./sesion-3-evaluacion/evaluar.sh contexto     # paso 1: trayectoria y respuesta (~1 min)
#   ./sesion-3-evaluacion/evaluar.sh incidente    # paso 2: rubricas (~2 min)
#   ./sesion-3-evaluacion/evaluar.sh regresion    # paso 3: agente del paso 3, debe fallar (~5 min)
#
# Cualquier argumento extra pasa tal cual a `adk eval`, por ejemplo:
#   ./sesion-3-evaluacion/evaluar.sh contexto --num_runs 3
#   MODEL=gemini-3.5-flash-lite ./sesion-3-evaluacion/evaluar.sh contexto
#
# Por que existe: `adk eval` mezcla en la terminal el resultado con cientos de
# lineas de log (cada llamada HTTP a los servidores MCP) y con trazas de errores
# que ADK ya reintento solo ("Failed to get tools from MCP server: Connection
# closed"). En Cloud Shell eso se ve cortado. Aqui el log completo queda en
# build/eval-<caso>.log, el resultado completo en build/eval-<caso>.txt, y en
# pantalla solo el resumen.

set -uo pipefail
cd "$(dirname "$0")/.."

CASO="${1:-}"
[[ -n "${CASO}" ]] && shift
case "${CASO}" in
  contexto)  AGENTE=sesion-4-adk-mcp/solucion/paso-5/agente_obs; SET=contexto ;;
  incidente) AGENTE=sesion-4-adk-mcp/solucion/paso-5/agente_obs; SET=incidente ;;
  regresion) AGENTE=sesion-4-adk-mcp/solucion/paso-3/agente_obs; SET=contexto ;;
  *) echo "Uso: $0 contexto|incidente|regresion [argumentos extra de adk eval]" >&2; exit 2 ;;
esac

ADK="adk"
[[ -x .venv/bin/adk ]] && ADK=".venv/bin/adk"
mkdir -p build
LOG="build/eval-${CASO}.log"
OUT="build/eval-${CASO}.txt"

echo "Evaluando ${AGENTE} con ${SET}.evalset.json ..."
echo "(log completo en ${LOG}; resultado completo en ${OUT})"
"${ADK}" eval "${AGENTE}" "sesion-3-evaluacion/${SET}.evalset.json" \
  --config_file_path "sesion-3-evaluacion/${SET}.config.json" \
  --print_detailed_results --log_level warning "$@" > "${OUT}" 2> "${LOG}"
CODIGO=$?

if ! grep -q "Tests passed" "${OUT}"; then
  echo
  echo "[!] adk eval no llego a dar resultados (codigo ${CODIGO}). Ultimas lineas del log:"
  tail -n 25 "${LOG}"
  exit "${CODIGO}"
fi

python3 - "${OUT}" <<'PY'
import re
import sys

caso = None
impreso = None
for linea in open(sys.argv[1], encoding="utf-8"):
  linea = linea.rstrip("\n")
  if linea.startswith("Eval Id: "):
    caso = linea[len("Eval Id: "):]
  elif linea.startswith("Overall Eval Status") and caso and caso != impreso:
    estado = linea.rsplit(" ", 1)[-1]
    print(f"\n{caso}: {estado}")
    impreso = caso
  elif linea.startswith("Metric: "):
    m = re.match(r"Metric: ([^,]+), Status: (\w+), Score: ([^,]+)", linea)
    if m:
      nombre, estado, puntaje = m.groups()
      try:
        puntaje = f"{float(puntaje):.2f}"
      except ValueError:
        pass
      print(f"  {nombre:<32} {estado:<14} {puntaje}")
  elif linea.startswith("Rubric: "):
    m = re.match(r"Rubric: (.*), Score: ([^,]+), Reasoning:", linea)
    if m:
      texto, puntaje = m.groups()
      texto = texto if len(texto) <= 70 else texto[:67] + "..."
      print(f"    - {texto:<72} {puntaje}")
  elif linea.strip().startswith(("Tests passed", "Tests failed")):
    print(linea.strip())
  elif linea.startswith("Eval Run Summary"):
    print("\n=== Resumen ===")
PY

exit "${CODIGO}"
