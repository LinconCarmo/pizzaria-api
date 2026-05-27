import uvicorn

from src.core.config import settings


def main() -> None:
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
