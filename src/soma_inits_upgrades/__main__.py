"""Entry point for python -m soma_inits_upgrades."""

import sys

from soma_inits_upgrades.main import cli

try:
    cli()
except KeyboardInterrupt:
    sys.exit(1)
