"""Agente de observabilidad de Farmalab. Solucion.

Paso 2: lee Cloud Logging por MCP.
"""

import datetime as dt
import os

import google.auth
import google.auth.transport.requests
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool import StreamableHTTPConnectionParams

from .conexion_google import cliente_http
from .conexion_google import url_mcp

# Proyecto donde estan las senales. Desplegado en Agent Runtime,
# GOOGLE_CLOUD_PROJECT trae el NUMERO del proyecto y los filtros de logs
# necesitan el id, por eso se puede indicar aparte.
PROJECT_ID = os.environ.get("SIGNALS_PROJECT_ID",
                            os.environ["GOOGLE_CLOUD_PROJECT"])
# Gemini 3.x se sirve desde la ubicacion "global". Se fija aqui para que el
# agente funcione igual en tu maquina y desplegado en una region.
MODEL = Gemini(model=os.environ.get("MODEL", "gemini-3.8-flash"),
               client_kwargs={"location": "global"})


# --- Autenticacion hacia los servidores MCP de Google Cloud -----------------
# Usan OAuth 2.0 + IAM. El agente presenta un access token de las credenciales
# por defecto: tu usuario en Cloud Shell, la Agent Identity del agente en Agent Runtime.
_credenciales, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"])


def encabezados_google(_contexto=None) -> dict[str, str]:
  """Encabezados de autenticacion. Renueva el token si ya vencio."""
  if not _credenciales.valid:
    _credenciales.refresh(google.auth.transport.requests.Request())
  return {
      "Authorization": f"Bearer {_credenciales.token}",
      "x-goog-user-project": PROJECT_ID,
  }


# --- PASO 2: senales de Cloud Logging por MCP --------------------------------
logging_mcp = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=url_mcp("logging"), timeout=30, httpx_client_factory=cliente_http),
    header_provider=encabezados_google,
    # Solo lectura y solo lo necesario: el modelo no ve el resto de las tools.
    tool_filter=["list_log_entries", "list_log_names"],
)


def instruccion(_contexto=None) -> str:
  """Instruccion del agente. Es una funcion para poder incluir la hora actual."""
  ahora = dt.datetime.now(dt.timezone.utc)
  hace_una_hora = ahora - dt.timedelta(hours=1)
  f = "%Y-%m-%dT%H:%M:%SZ"
  return f"""
Eres el agente de observabilidad de Farmalab, una cadena de farmacias ficticia.
Ayudas a la guardia a entender incidentes y a abrir el ticket correcto.

Hora actual (UTC): {ahora.strftime(f)}. Hace una hora: {hace_una_hora.strftime(f)}.
Proyecto de Google Cloud: {PROJECT_ID}. En las herramientas de Google Cloud usa
siempre "projects/{PROJECT_ID}" como name, parent o resourceNames.

SENALES DISPONIBLES

Logs de aplicacion (herramienta list_log_entries):
- filter: logName="projects/{PROJECT_ID}/logs/farmalab-app"
  AND timestamp>="{hace_una_hora.strftime(f)}" y agrega lo que necesites, por
  ejemplo AND severity>=ERROR o AND labels.service="pagos-gateway".
- Usa orderBy "timestamp desc" y pageSize 50.
- Campos: severity, labels.service, labels.version, jsonPayload.error_code,
  jsonPayload.message, jsonPayload.status, jsonPayload.tienda_id.

Responde en espanol, breve y con datos concretos (horas en UTC, valores).
"""


root_agent = LlmAgent(
    name="agente_obs",
    model=MODEL,
    description=("Investiga incidentes con senales de Cloud Logging."),
    instruction=instruccion,
    tools=[
        logging_mcp,
    ],
)
