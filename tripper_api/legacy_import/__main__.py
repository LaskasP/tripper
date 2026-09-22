import asyncio

from tripper_api.legacy_import.legacy_import_service import _main

raise SystemExit(asyncio.run(_main()))
