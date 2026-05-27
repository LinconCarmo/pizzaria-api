"""Pytest bootstrap: defaults seguros para imports de ``src.core.config``.

Roda antes da coleta. ``src.core.config`` instancia ``Settings()`` no
import-time e requer 4 vars (``DATABASE_URL``, ``REDIS_URL``, ``RABBITMQ_URL``,
``JWT_SECRET``); sem elas, qualquer teste que importe ``src.*`` falha na
fase de coleta com ``ValidationError``.

Usa ``os.environ.setdefault`` para nunca pisar em vars reais: ``.env`` local
de dev, ``env:`` do CI, ou overrides explícitos (ex.: o conftest de
integração que sobrescreve ``DATABASE_URL`` com a URL do Testcontainer)
continuam tendo precedência.
"""

import os

os.environ.setdefault("DATABASE_URL", "mysql://test:test@localhost:3306/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
