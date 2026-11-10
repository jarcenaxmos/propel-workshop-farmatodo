#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Borra de TU proyecto todo lo que crearon los labs:
#   - senales de ejemplo: log farmalab-app, metricas custom farmalab/*, politica de alertas
#   - agente(s) "agente-obs-farmalab" en Agent Runtime (sesion II)
#   - template de Model Armor farmalab-guardrail (sesion VI)
#   - cuenta de servicio agente-obs y sus roles (sesion II)
# No deshabilita APIs ni borra el proyecto.
#   ./cleanup.sh            pide que escribas el id del proyecto para confirmar
#   ./cleanup.sh --local    ademas borra .venv, .env, tickets/ y archivos generados
set -uo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
[[ -f "${AQUI}/.env" ]] && { set -a; source "${AQUI}/.env"; set +a; }
PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${REGION:-us-central1}"
[[ -n "${PROJECT_ID}" && "${PROJECT_ID}" != "(unset)" ]] || { echo "No hay proyecto. Ejecuta: export PROJECT_ID=tu-proyecto"; exit 1; }

echo "Se borraran los recursos del workshop en el proyecto ${PROJECT_ID} (region ${REGION})."
read -r -p "Para confirmar escribe el id del proyecto: " r
[[ "${r}" == "${PROJECT_ID}" ]] || { echo "No coincide. Cancelado."; exit 0; }
TOKEN="$(gcloud auth print-access-token)"

echo "== Senales de ejemplo"
if [[ -x "${AQUI}/.venv/bin/python" ]]; then
  PROJECT_ID="${PROJECT_ID}" "${AQUI}/.venv/bin/python" "${AQUI}/scripts/sembrar_senales.py" --borrar
else
  echo "[!] No hay .venv: no se borraron las senales. Ejecuta ./setup.sh y luego ./cleanup.sh, o borralas a mano (ver README)."
fi

echo "== Agent Runtime"
API="https://${REGION}-aiplatform.googleapis.com/v1"
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "${API}/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines?pageSize=100" \
  | python3 -c '
import json, sys
for e in json.load(sys.stdin).get("reasoningEngines", []):
    if e.get("displayName") == "agente-obs-farmalab":
        print(e["name"])' \
  | while read -r nombre; do
      echo "borrando ${nombre}"
      curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" "${API}/${nombre}?force=true" >/dev/null
    done
rm -f "${AQUI}/sesion-2-agent-runtime/.agent_engine_id"

echo "== Model Armor"
CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.${REGION}.rep.googleapis.com/" \
  gcloud model-armor templates delete farmalab-guardrail --location="${REGION}" \
  --project="${PROJECT_ID}" --quiet 2>/dev/null && echo "template borrado" || echo "no habia template"

echo "== Cuenta de servicio del agente"
SA="agente-obs@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "${SA}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  for rol in roles/aiplatform.user roles/mcp.toolUser roles/logging.viewer \
             roles/monitoring.viewer roles/logging.logWriter \
             roles/monitoring.metricWriter roles/cloudtrace.agent; do
    gcloud projects remove-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA}" \
      --role="${rol}" --condition=None --format=none >/dev/null 2>&1 || true
  done
  gcloud iam service-accounts delete "${SA}" --project="${PROJECT_ID}" --quiet && echo "cuenta de servicio borrada"
else
  echo "no habia cuenta de servicio"
fi

if [[ "${1:-}" == "--local" ]]; then
  echo "== Archivos locales"
  rm -rf "${AQUI}/.venv" "${AQUI}/.env" "${AQUI}/sesion-2-agent-runtime/build"
  find "${AQUI}" \( -name tickets -o -name .adk -o -name __pycache__ \) -type d -prune -exec rm -rf {} +
  find "${AQUI}" \( -name "*.respaldo" -o -name "*.evalset_result.json" \) -delete
fi
echo "Listo. Si creaste el proyecto solo para el workshop, tambien puedes borrarlo completo."
