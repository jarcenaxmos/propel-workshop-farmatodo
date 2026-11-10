"""Agente de observabilidad de Farmalab.

Este es tu archivo de trabajo. Sigue la guia (guia.md) y completa cada paso
donde dice PASO N. Si te atrasas: ./ponerse-al-dia.sh N
"""

import datetime as dt
import os

from google.adk.agents import LlmAgent
from google.adk.models import Gemini

# Proyecto donde estan las senales. Desplegado en Agent Runtime,
# GOOGLE_CLOUD_PROJECT trae el NUMERO del proyecto y los filtros de logs
# necesitan el id, por eso se puede indicar aparte.
PROJECT_ID = os.environ.get("SIGNALS_PROJECT_ID",
                            os.environ["GOOGLE_CLOUD_PROJECT"])
# Gemini 3.x se sirve desde la ubicacion "global". Se fija aqui para que el
# agente funcione igual en tu maquina y desplegado en una region.
MODEL = Gemini(model=os.environ.get("MODEL", "gemini-3.8-flash"),
               client_kwargs={"location": "global"})


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


# --- PASO 1: define aqui tu agente -------------------------------------------
# root_agent = LlmAgent(...)

