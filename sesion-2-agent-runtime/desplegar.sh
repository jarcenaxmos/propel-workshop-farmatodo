#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Despliega el agente de observabilidad en Agent Runtime con identidad propia.
#   ./desplegar.sh          despliega la solucion del paso 5
#   ./desplegar.sh --mio    despliega TU agente (sesion-4-adk-mcp/agente_obs)
# Si ya lo desplegaste antes, actualiza el mismo recurso en vez de crear otro.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"; RAIZ="$(dirname "${AQUI}")"
[[ -f "${RAIZ}/.env" ]] || { echo "Falta .env: ejecuta primero ./setup.sh en la raiz del repo."; exit 1; }
set -a; source "${RAIZ}/.env"; set +a
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"; REGION="${REGION:-us-central1}"
ORIGEN="${RAIZ}/sesion-4-adk-mcp/solucion/paso-5/agente_obs"
[[ "${1:-}" == "--mio" ]] && ORIGEN="${RAIZ}/sesion-4-adk-mcp/agente_obs"
SA="agente-obs@${PROJECT_ID}.iam.gserviceaccount.com"

echo "== 1/3 Identidad del agente: ${SA}"
# El agente NO corre con tu usuario: tiene su propia cuenta de servicio, con
# permisos de solo lectura sobre las senales.
gcloud iam service-accounts describe "${SA}" --project="${PROJECT_ID}" >/dev/null 2>&1 \
  || gcloud iam service-accounts create agente-obs --project="${PROJECT_ID}" \
       --display-name="Agente de observabilidad (workshop)"
for rol in roles/aiplatform.user roles/mcp.toolUser roles/logging.viewer \
           roles/monitoring.viewer roles/logging.logWriter \
           roles/monitoring.metricWriter roles/cloudtrace.agent; do
  # Se reintenta: IAM rechaza cambios de politica concurrentes.
  for intento in 1 2 3 4; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA}" \
      --role="${rol}" --condition=None --format=none >/dev/null 2>&1 && break
    (( intento == 4 )) && { echo "[!] No se pudo otorgar ${rol}. Necesitas roles/resourcemanager.projectIamAdmin."; exit 1; }
    sleep 3
  done
  echo "  ${rol}"
done

echo "== 2/3 Paquete autocontenido en build/agente_obs"
PAQ="${AQUI}/build/agente_obs"
rm -rf "${AQUI}/build"; mkdir -p "${PAQ}/datos"
cp "${ORIGEN}"/*.py "${PAQ}/"
cp -r "${RAIZ}/sesion-4-adk-mcp/servidor_contexto" "${PAQ}/"
cp "${RAIZ}/datos/catalogo_servicios.json" "${PAQ}/datos/"
[[ -f "${RAIZ}/datos/.incidente.json" ]] && cp "${RAIZ}/datos/.incidente.json" "${PAQ}/datos/"
cat > "${PAQ}/requirements.txt" <<REQ
google-adk[mcp,gcp,otel-gcp]==2.14.0
mcp==2.3.0
REQ
cat > "${PAQ}/.env" <<ENV
MODEL=${MODEL:-gemini-3.8-flash}
SIGNALS_PROJECT_ID=${PROJECT_ID}
TICKETS_DIR=/tmp/tickets
ENV

echo "== 3/3 Despliegue en Agent Runtime (${REGION}). Tarda de 3 a 10 minutos."
EXTRA=()
if [[ -f "${AQUI}/.agent_engine_id" ]]; then
  EXTRA+=(--agent_engine_id "$(cat "${AQUI}/.agent_engine_id")")
  echo "Se actualiza el agente existente: $(cat "${AQUI}/.agent_engine_id")"
fi
"${RAIZ}/.venv/bin/adk" deploy agent_engine \
  --project="${PROJECT_ID}" --region="${REGION}" \
  --display_name="agente-obs-farmalab" \
  --description="Agente de observabilidad del workshop Propel" \
  --service_account="${SA}" --otel_to_cloud \
  ${EXTRA[@]+"${EXTRA[@]}"} "${PAQ}" 2>&1 | tee "${AQUI}/build/deploy.log"

# El id del recurso queda guardado para consultar.py, para actualizar y para cleanup.sh.
ID="$(grep -oE 'projects/[^/ ]+/locations/[a-z0-9-]+/reasoningEngines/[0-9]+' "${AQUI}/build/deploy.log" | tail -1 || true)"
if [[ -n "${ID}" ]]; then
  basename "${ID}" > "${AQUI}/.agent_engine_id"
  echo; echo "Recurso: ${ID}"; echo "Prueba: python sesion-2-agent-runtime/consultar.py"
else
  echo "[!] No se encontro el id del recurso en la salida. Revisa build/deploy.log."; exit 1
fi
