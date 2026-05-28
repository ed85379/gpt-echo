from .api.routers.tts_api import tts_router
from .reminders.router import reminders_router
from .reminders.commands import register_reminder_commands
from app.commands.registry import command_registry


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
    register_reminder_commands(app.state.command_registry)


def register_tools(app):
    pass