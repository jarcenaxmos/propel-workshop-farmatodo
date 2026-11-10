# Diagrama de arquitectura

`architecture.html` es la fuente y `architecture-observability-agent.png` se genera a partir de ella. No edites el PNG a mano.

Para regenerarlo (requiere `uv`; la primera vez puede pedir `uv run --with playwright playwright install chromium`):

```bash
uv run --with playwright python RUTA_A/jarcen-architecture-diagram/scripts/render.py \
  docs/architecture/architecture.html docs/architecture/architecture-observability-agent.png 2
```

El script de render es de la skill `jarcen-architecture-diagram` de Axmos y no viene en este repo. Sin él, abre `architecture.html` en Chrome a 1920×960 y toma una captura.

Qué cambiar:

- Un componente opcional pasa a ser parte fija: quita la clase `opt` de su tarjeta y cambia la etiqueta `OPTIONAL` por `ACTIVE`.
- Cambia la fecha de estado en el `<header>`.
- Los íconos son los oficiales de Google Cloud. Su origen está en `icons/manifest-*.json`.
