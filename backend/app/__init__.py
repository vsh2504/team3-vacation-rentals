"""StayNest backend.

Pattern: Facade (lazy). ``app.create_app`` is the single public entry point;
it is resolved on first use so importing a submodule such as ``app.domain``
never builds the web application.
"""


def __getattr__(name: str):
    if name == "create_app":
        from .main import create_app
        return create_app
    raise AttributeError(f"module 'app' has no attribute {name!r}")
