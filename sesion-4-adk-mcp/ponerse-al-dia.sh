#!/usr/bin/env bash
# Workshop Propel · Farmatodo. Todos los derechos reservados.
#
# Deja tu agente (agente_obs/) igual a la solucion de un paso, para seguir desde ahi.
#   ./ponerse-al-dia.sh 3     # tu agent.py queda como la solucion del paso 3
# Tu version anterior se guarda como agente_obs/agent.py.respaldo
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
N="${1:-}"
[[ "${N}" =~ ^[1-6]$ ]] || { echo "Uso: ./ponerse-al-dia.sh N   (N de 1 a 6)"; exit 1; }
cp "${AQUI}/agente_obs/agent.py" "${AQUI}/agente_obs/agent.py.respaldo"
cp "${AQUI}/solucion/paso-${N}/agente_obs/agent.py" "${AQUI}/agente_obs/agent.py"
echo "Listo: agente_obs/agent.py es ahora la solucion del paso ${N}."
echo "Tu version anterior quedo en agente_obs/agent.py.respaldo"
