from collections import Counter

from fastapi.routing import APIRoute

from src.main import app


def test_app_registers_each_route_only_once() -> None:
    routes = [
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    ]

    duplicated = [key for key, count in Counter(routes).items() if count > 1]

    assert duplicated == []
