from .api.routers.tts_api import tts_router
from .api.routers.reminders_api import reminders_router


def register(app):
    register_routers(app)
    register_prompt_profiles(app)
    register_commands(app)
    register_tools(app)


def register_routers(app):
    app.include_router(tts_router)
    app.include_router(reminders_router)


def register_prompt_profiles(app):
    pass


def register_commands(app):
    pass


def register_tools(app):
    pass