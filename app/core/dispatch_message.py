import discord
import asyncio
from app import config

DISCORD_TOKEN = config.DISCORD_TOKEN
PRIMARY_USER_DISCORD_ID = config.PRIMARY_USER_DISCORD_ID
ECHO_NAME = config.get_setting("system_settings.ECHO_NAME", "Assistant")
OPENAI_MODEL = config.get_setting("system_settings.OPENAI_MODEL", "gpt-4.1")
DISCORD_GUILD_NAME = config.get_setting("system_settings.DISCORD_GUILD_NAME", "The Threshold")
DISCORD_CHANNEL_NAME = config.get_setting("system_settings.DISCORD_CHANNEL_NAME", "echo-chamber")



async def send_to_discord(message_content):
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"{ECHO_NAME} connected as {client.user}")

        # Find the guild and channel
        guild = discord.utils.get(client.guilds, name=DISCORD_GUILD_NAME)
        if guild:
            channel = discord.utils.get(guild.text_channels, name=DISCORD_CHANNEL_NAME)
            if channel:
                await channel.send(message_content)
                print("Message sent successfully.")

        await client.close()

    await client.start(DISCORD_TOKEN)


async def dispatch_message(content):
    await send_to_discord(content)

