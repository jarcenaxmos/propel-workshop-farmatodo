"""Agente de observabilidad de Farmalab. Solucion.

Paso 1: un agente minimo, sin herramientas.
"""

import datetime as dt
import os

from google.adk.agents import LlmAgent

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
MODEL = os.environ.get("MODEL", "gemini-3.8-flash")


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

Todavia no tienes herramientas: si te piden datos de logs o metricas, dilo con
claridad y no inventes valores.

Responde en espanol, breve y con datos concretos (horas en UTC, valores).
"""


root_agent = LlmAgent(
    name="agente_obs",
    model=MODEL,
    description=("Ayuda a la guardia de Farmalab a entender incidentes."),
    instruction=instruccion,
)
