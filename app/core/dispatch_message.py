import discord
from app import config
from app.interfaces import websocket_server

DISCORD_TOKEN = config.DISCORD_TOKEN
PRIMARY_USER_DISCORD_ID = config.PRIMARY_USER_DISCORD_ID
MUSE_NAME = config.MUSE_NAME
OPENAI_MODEL = config.OPENAI_MODEL
DISCORD_GUILD_NAME = config.DISCORD_GUILD_NAME
DISCORD_CHANNEL_NAME = config.DISCORD_CHANNEL_NAME


async def send_to_discord(message_content):
    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"{MUSE_NAME} connected as {client.user}")

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
    await websocket_server.broadcast_message(content)

