"""Agente que redacta tickets de incidente con una skill de Agent Registry.

La skill NO esta en este codigo: se descarga del registro en cada sesion, en su
revision vigente. Si el equipo de plataforma publica una version nueva, este
agente la usa sin cambiar una linea ni redesplegarse.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.integrations.skill_registry import GCPSkillRegistry
from google.adk.models import Gemini
from google.adk.tools.skill_toolset import SkillToolset

PROJECT_ID = os.environ.get("SIGNALS_PROJECT_ID", os.environ["GOOGLE_CLOUD_PROJECT"])
MODEL = Gemini(model=os.environ.get("MODEL", "gemini-3.8-flash"),
               client_kwargs={"location": "global"})

# Las skills de Agent Registry viven en la ubicacion "global" (en us-east1 el
# servicio responde 503). Se indica explicita: sin ella ADK usaria
# GOOGLE_CLOUD_LOCATION, que aqui tambien es global, pero asi no depende de eso.
registro = GCPSkillRegistry(project_id=PROJECT_ID, location="global")

root_agent = LlmAgent(
    name="agente_tickets",
    model=MODEL,
    instruction="""
Eres el asistente de la guardia de Farmalab. Redactas el ticket de un incidente
a partir de los datos que te da la persona. No inventes datos.

ANTES de escribir cualquier ticket, carga la skill "private-redactar-ticket-incidente"
del registro (herramienta load_skill) y sigue sus reglas al pie de la letra.
Responde solo con el ticket (titulo, resumen, evidencia y accion sugerida).
""",
    tools=[SkillToolset(registry=registro)],
)
