#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Crea el template de Model Armor "farmalab-guardrail" en tu proyecto.
# Filtros: prompt injection y jailbreak, URIs maliciosas, datos sensibles
# (Sensitive Data Protection basico) y contenido danino (Responsible AI).
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"; RAIZ="$(dirname "${AQUI}")"
[[ -f "${RAIZ}/.env" ]] || { echo "Falta .env: ejecuta primero ./setup.sh en la raiz del repo."; exit 1; }
set -a; source "${RAIZ}/.env"; set +a
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"; REGION="${REGION:-us-central1}"
# Model Armor solo atiende en endpoints regionales.
export CLOUDSDK_API_ENDPOINT_OVERRIDES_MODELARMOR="https://modelarmor.${REGION}.rep.googleapis.com/"

if gcloud model-armor templates describe farmalab-guardrail --location="${REGION}" \
     --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "El template farmalab-guardrail ya existe en ${REGION}."
else
  gcloud model-armor templates create farmalab-guardrail \
    --location="${REGION}" --project="${PROJECT_ID}" \
    --pi-and-jailbreak-filter-settings-enforcement=enabled \
    --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above \
    --malicious-uri-filter-settings-enforcement=enabled \
    --basic-config-filter-enforcement=enabled \
    --rai-settings-filters='[{"filterType":"HATE_SPEECH","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"HARASSMENT","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"DANGEROUS","confidenceLevel":"MEDIUM_AND_ABOVE"},{"filterType":"SEXUALLY_EXPLICIT","confidenceLevel":"MEDIUM_AND_ABOVE"}]' \
    --labels=workshop=farmatodo
fi
echo "Template: projects/${PROJECT_ID}/locations/${REGION}/templates/farmalab-guardrail"
