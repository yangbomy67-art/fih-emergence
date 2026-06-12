"""FIH Emergence CLI Entry Point."""

import asyncio

from fih_emergence.roles.human_gate import main

if __name__ == "__main__":
    asyncio.run(main())
