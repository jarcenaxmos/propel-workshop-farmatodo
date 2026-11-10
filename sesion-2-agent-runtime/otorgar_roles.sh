#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Da (o quita) los roles del agente desplegado en Agent Runtime.
#   ./otorgar_roles.sh --id ID_NUMERICO            otorga los roles
#   ./otorgar_roles.sh --id ID_NUMERICO --quitar   los quita (cleanup.sh lo usa)
# Variables: PROJECT_ID y REGION (las toma de ../.env si existe).
#
# El agente usa Agent Identity: su identidad es el principal
#   principal://agents.global.org-ORG.system.id.goog/resources/aiplatform/
#     projects/NUM/locations/REGION/reasoningEngines/ID
# (si el proyecto NO esta en una organizacion: agents.global.proj-NUM.system.id.goog).
# Es unico por instancia: si borras el agente y creas otro, hay que repetir esto.
# Al borrar la instancia sus roles NO se borran solos: por eso existe --quitar.
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
[[ -f "${AQUI}/../.env" ]] && { set -a; source "${AQUI}/../.env"; set +a; }
PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"; REGION="${REGION:-us-central1}"
ID=""; ACCION="add"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --id) ID="$2"; shift 2 ;;
    --quitar) ACCION="remove"; shift ;;
    *) echo "Uso: $0 --id ID_NUMERICO [--quitar]"; exit 2 ;;
  esac
done
[[ -n "${ID}" && -n "${PROJECT_ID}" ]] || { echo "Faltan --id o PROJECT_ID"; exit 2; }

NUM="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
ORG="$(gcloud projects get-ancestors "${PROJECT_ID}" --format='value(id,type)' 2>/dev/null \
       | awk '$2=="organization"{print $1}')"
if [[ -n "${ORG}" ]]; then DOMINIO="agents.global.org-${ORG}.system.id.goog"
else DOMINIO="agents.global.proj-${NUM}.system.id.goog"; fi
PRINCIPAL="principal://${DOMINIO}/resources/aiplatform/projects/${NUM}/locations/${REGION}/reasoningEngines/${ID}"
echo "Principal del agente: ${PRINCIPAL}"

# Minimo privilegio: el agente solo LEE senales; el resto es para correr y
# escribir su propia telemetria.
ROLES=(
  roles/aiplatform.user                    # llamar a Gemini
  roles/serviceusage.serviceUsageConsumer  # usar las APIs del proyecto
  roles/mcp.toolUser                       # permiso mcp.tools.call de los MCP de Google
  roles/logging.viewer                     # tools de lectura del MCP de Logging
  roles/monitoring.viewer                  # tools de lectura del MCP de Monitoring
  roles/logging.logWriter                  # sus propios logs
  roles/monitoring.metricWriter            # sus propias metricas
  roles/telemetry.tracesWriter             # sus trazas (OpenTelemetry)
)
for rol in "${ROLES[@]}"; do
  # Se reintenta: IAM rechaza cambios de politica concurrentes y tarda en
  # reconocer un principal recien creado.
  for intento in 1 2 3 4 5 6; do
    gcloud projects "${ACCION}-iam-policy-binding" "${PROJECT_ID}" --member="${PRINCIPAL}" \
      --role="${rol}" --condition=None --format=none >/dev/null 2>&1 && { echo "  ${ACCION}: ${rol}"; break; }
    if (( intento == 6 )); then
      echo "[!] No se pudo ${ACCION} ${rol}. Necesitas roles/resourcemanager.projectIamAdmin."
      [[ "${ACCION}" == "remove" ]] || exit 1
    fi
    sleep 5
  done
done
