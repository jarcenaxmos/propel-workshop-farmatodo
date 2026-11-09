#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Prepara TU proyecto de Google Cloud y tu entorno para los labs.
#   ./setup.sh             APIs + entorno Python + .env + senales de ejemplo + verificacion
#   ./setup.sh --yes       sin pedir confirmacion
#   ./setup.sh --sin-apis  no intenta habilitar APIs (si un admin ya lo hizo)
# Variables opcionales:
#   PROJECT_ID  por defecto, tu proyecto activo en gcloud
#   REGION      region de Agent Runtime y Model Armor (por defecto us-central1)
#   MODEL       modelo Gemini (por defecto gemini-3.8-flash)
# Se puede ejecutar las veces que quieras: no duplica nada.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
SI=0; APIS=1
for a in "$@"; do
  case "$a" in
    --yes|-y) SI=1 ;;
    --sin-apis) APIS=0 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Opcion desconocida: $a (usa --help)"; exit 1 ;;
  esac
done

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
MODEL="${MODEL:-gemini-3.8-flash}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "No hay un proyecto activo."
  echo "Ejecuta: export PROJECT_ID=tu-proyecto   y vuelve a lanzar ./setup.sh"
  exit 1
fi

echo "Proyecto: ${PROJECT_ID}   Region: ${REGION}   Modelo: ${MODEL}"
if (( ! SI )); then
  read -r -p "Se habilitaran APIs y se crearan senales de ejemplo en ese proyecto. Continuar? [s/N] " r
  [[ "${r}" =~ ^[sSyY]$ ]] || { echo "Cancelado."; exit 0; }
fi

echo "== 1/5 APIs"
if (( APIS )); then
  gcloud services enable aiplatform.googleapis.com logging.googleapis.com \
    monitoring.googleapis.com --project="${PROJECT_ID}" \
    || { echo "[!] No se pudieron habilitar las APIs del lab principal. Necesitas roles/serviceusage.serviceUsageAdmin o que un admin las habilite."; exit 1; }
  # Estas solo hacen falta para los ejemplos de las sesiones II, III, V y VI.
  gcloud services enable cloudresourcemanager.googleapis.com cloudtrace.googleapis.com \
    telemetry.googleapis.com storage.googleapis.com modelarmor.googleapis.com \
    agentregistry.googleapis.com --project="${PROJECT_ID}" \
    || echo "[!] No se habilitaron todas las APIs opcionales. El lab de la sesion IV funciona igual."
else
  echo "omitido (--sin-apis)"
fi

echo "== 2/5 Entorno Python"
PY="${PYTHON:-python3}"
"${PY}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || { echo "[!] Se necesita Python 3.11 o superior. Tienes: $(${PY} --version 2>&1). Indica otro con PYTHON=python3.12 ./setup.sh"; exit 1; }
[[ -x "${AQUI}/.venv/bin/python" ]] || "${PY}" -m venv "${AQUI}/.venv"
"${AQUI}/.venv/bin/python" -m pip install --quiet --upgrade pip
"${AQUI}/.venv/bin/python" -m pip install --quiet -r "${AQUI}/requirements.txt"
echo "ADK: $("${AQUI}/.venv/bin/adk" --version 2>/dev/null | tail -1)"

echo "== 3/5 Archivo .env"
cat > "${AQUI}/.env" <<ENV
# Generado por setup.sh. ADK lo lee solo al ejecutar adk run / adk web / adk eval.
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_LOCATION=global
MODEL=${MODEL}
REGION=${REGION}
ENV
echo "escrito: .env"

echo "== 4/5 Senales de ejemplo (logs, metricas y politica de alertas)"
PROJECT_ID="${PROJECT_ID}" "${AQUI}/.venv/bin/python" "${AQUI}/scripts/sembrar_senales.py"

echo "== 5/5 Verificacion"
"${AQUI}/.venv/bin/python" "${AQUI}/scripts/verificar.py"

echo
echo "Listo. Activa el entorno y sigue la guia de la sesion IV:"
echo "  source .venv/bin/activate"
echo "  cd sesion-4-adk-mcp    # guia.md"
