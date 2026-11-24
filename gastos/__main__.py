import sys

from .cli import main

# Evita erro de acentuação em terminais do Windows.
for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

sys.exit(main())
