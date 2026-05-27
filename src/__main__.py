import socket

import uvicorn

from src.core.config import settings
from src.core.logger import logger


class LoggingServer(uvicorn.Server):
    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        host = self.config.host
        port = self.config.port
        logger.bind(host=host, port=port).info(f"Server running at http://{host}:{port}")


def main() -> None:
    config = uvicorn.Config(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.app_env == "development",
    )
    LoggingServer(config=config).run()


if __name__ == "__main__":
    main()
