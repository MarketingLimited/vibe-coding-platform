import asyncio
import logging

from .config import Settings
from .service import CleanupService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


async def run_cleanup_loop() -> None:
    settings = Settings()
    service = CleanupService(settings)
    interval = max(60, settings.cleanup_interval)
    while True:
        service.run_once()
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(run_cleanup_loop())
