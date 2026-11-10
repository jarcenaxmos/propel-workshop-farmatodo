#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Despliega el agente de observabilidad en Agent Runtime con Agent Identity
# (identidad propia del agente, sin cuentas de servicio).
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
PY="${RAIZ}/.venv/bin/python"

echo "== 1/3 Identidad del agente (Agent Identity)"
# El agente NO corre con tu usuario ni con una cuenta de servicio: Agent Runtime
# le da una identidad propia (Agent Identity), unica por instancia. Se elige al
# CREAR la instancia y no se puede cambiar despues, asi que primero se crea la
# instancia vacia, luego se le dan roles y al final se sube el codigo.
if [[ -f "${AQUI}/.agent_engine_id" ]]; then
  ID="$(cat "${AQUI}/.agent_engine_id")"
  echo "Se actualiza el agente existente: ${ID}"
else
  ID="$("${PY}" - "${PROJECT_ID}" "${REGION}" <<'PYEOF'
import sys, warnings
warnings.filterwarnings("ignore")
import vertexai
from vertexai._genai import types
proyecto, region = sys.argv[1:]
cliente = vertexai.Client(project=proyecto, location=region,
                          http_options={"api_version": "v1beta1"})
agente = cliente.agent_engines.create(config={
    "display_name": "agente-obs-farmalab",
    "identity_type": types.IdentityType.AGENT_IDENTITY,
})
print(agente.api_resource.name.rsplit("/", 1)[-1])
PYEOF
)"
  [[ -n "${ID}" ]] || { echo "[!] No se pudo crear la instancia."; exit 1; }
  echo "${ID}" > "${AQUI}/.agent_engine_id"
  echo "Instancia creada: ${ID}"
fi
# Roles minimos para el principal de esa instancia (se puede repetir sin problema).
PROJECT_ID="${PROJECT_ID}" REGION="${REGION}" "${AQUI}/otorgar_roles.sh" --id "${ID}"

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
cat > "${PAQ}/.agent_engine_config.json" <<CFG
{"identity_type": "AGENT_IDENTITY", "min_instances": 0, "max_instances": 1,
 "resource_limits": {"cpu": "1", "memory": "2Gi"}, "container_concurrency": 3}
CFG
cat > "${PAQ}/.env" <<ENV
MODEL=${MODEL:-gemini-3.8-flash}
SIGNALS_PROJECT_ID=${PROJECT_ID}
TICKETS_DIR=/tmp/tickets
ENV

echo "== 3/3 Subiendo el codigo a Agent Runtime (${REGION}). Tarda de 3 a 10 minutos."
# CPU, memoria e instancias: .agent_engine_config.json (dentro del paquete).
"${RAIZ}/.venv/bin/adk" deploy agent_engine \
  --project="${PROJECT_ID}" --region="${REGION}" \
  --display_name="agente-obs-farmalab" \
  --description="Agente de observabilidad del workshop Propel" \
  --otel_to_cloud --agent_engine_id="${ID}" "${PAQ}" 2>&1 | tee "${AQUI}/build/deploy.log"

echo; echo "Recurso: projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${ID}"
echo "Prueba: python sesion-2-agent-runtime/consultar.py"
