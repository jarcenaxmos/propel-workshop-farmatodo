"""El agente del paso 5 con Model Armor delante y detras del modelo.

ModelArmorPlugin revisa cada prompt antes de que llegue a Gemini y cada
respuesta antes de que llegue al usuario. Si un filtro coincide, el turno se
reemplaza por un mensaje seguro y el modelo ni siquiera se invoca.
"""

import os
import pathlib
import sys

from google.adk.apps import App
from google.adk.integrations.model_armor import ModelArmorConfig
from google.adk.integrations.model_armor import ModelArmorPlugin

# Reutiliza el agente final de la sesion IV sin copiarlo.
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "sesion-4-adk-mcp" / "solucion" / "paso-5"))
from agente_obs.agent import root_agent  # noqa: E402

REGION = os.environ.get("REGION", "us-central1")
TEMPLATE = (f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/locations/{REGION}"
            "/templates/farmalab-guardrail")

app = App(
    name="agente_protegido",
    root_agent=root_agent,
    plugins=[
        ModelArmorPlugin(config=ModelArmorConfig(
            prompt_template_name=TEMPLATE,
            response_template_name=TEMPLATE,
            input_blocked_message=("Model Armor bloqueo este mensaje. Si crees"
                                   " que es un error, avisa a la guardia."),
            output_blocked_message=("Model Armor bloqueo la respuesta del"
                                    " modelo."),
        )),
    ],
)
