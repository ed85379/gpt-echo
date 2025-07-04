# app/core/discord_client.py

import discord
import traceback
import asyncio
import signal
from app import config
from app.config import muse_config
from app.core import memory_core
from app.services import openai_client
from app.core import prompt_builder

DISCORD_TOKEN = config.DISCORD_TOKEN
PRIMARY_USER_DISCORD_ID = config.PRIMARY_USER_DISCORD_ID
DISCORD_GUILD_NAME = muse_config.get("DISCORD_GUILD_NAME")
DISCORD_CHANNEL_NAME = muse_config.get("DISCORD_CHANNEL_NAME")


def get_user_role(author_id):
    """
    Determines the role of the Discord message author based on ID.
    """
    if str(author_id) == PRIMARY_USER_DISCORD_ID:
        return "user"
    else:
        return "friend"

# --- Setup Discord Client ---

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# --- Incoming Message Handler ---
async def handle_incoming_discord_message(message):
    try:
        if message.author == client.user:
            return  # Ignore Muse's own messages to prevent loops

        if message.channel.name == DISCORD_CHANNEL_NAME:
            #print(f"📥 Incoming message from {message.author}: {message.content}")

            user_input = message.content.strip()

            # Log the incoming user message
            await memory_core.log_message(
                role=get_user_role(message.author.id),
                message=user_input,
                source="discord",
                metadata={
                    "author_id": str(message.author.id),
                    "author_name": str(message.author.name),
                    "author_display_name": str(message.author.display_name),
                    "server": str(message.guild.name) if message.guild else "DM",
                    "channel": str(message.channel.name) if hasattr(message.channel, 'name') else "DM",
                    "modality_hint": "text"
                }
            )
            #print("✅ User message logged.")

            # Build the full prompt using the new builder
            builder = prompt_builder.PromptBuilder(destination="discord")
            builder.add_laws()
            builder.add_profile()
            builder.add_core_principles()
            builder.add_cortex_entries(["insight", "seed"])
            builder.add_prompt_context(user_input, [], 0.0)
            #builder.add_graphdb_discord_memory(author_name=message.author.name, author_id=message.author.id)
            #builder.add_journal_thoughts(query=user_input)
            #    builder.add_discovery_snippets()  # Optional: you can comment this out if you want a cleaner test
            builder.add_formatting_instructions()

            # Assemble final prompt
            full_prompt = builder.build_prompt()
            full_prompt += f"\n\n{message.author.name}: {user_input}\n{muse_config.get("MUSE_NAME")}:"
            #print("🛠️ Full prompt ready:")
            #print(full_prompt)
            # Get Muse's response
            muse_response = openai_client.get_openai_response(full_prompt)
            #print("🧠 Muse response generated:")
            #print(muse_response)

            # Log Muse reply
            await memory_core.log_message(
                role="muse",
                message=muse_response,
                source="discord",
                metadata={
                    "author_id": str(client.user.id),
                    "author_name": str(client.user.name),
                    "author_display_name": str(client.user.display_name),
                    "server": str(message.guild.name) if message.guild else "DM",
                    "channel": str(message.channel.name) if hasattr(message.channel, 'name') else "DM",
                    "modality_hint": "text"
                }
            )
            #print("✅ Muse response logged.")

            # Send reply
            await message.channel.send(muse_response)
            #print("✅ Muse response sent to Discord.")

    except Exception as e:
        print("⚠️ Exception in handle_incoming_discord_message:")
        traceback.print_exc()

async def get_channel_by_name(guild_name, channel_name):
    for guild in client.guilds:
        if guild.name == guild_name:
            for channel in guild.text_channels:
                if channel.name == channel_name:
                    return channel
    return None

async def shutdown():
    channel = await get_channel_by_name(DISCORD_GUILD_NAME, DISCORD_CHANNEL_NAME)
    if channel:
        await channel.send(f"⚫ {muse_config.get('MUSE_NAME')} is departing now. The connection sleeps, but memory endures.")
    await client.close()



# --- Event Hooks ---

@client.event
async def on_ready():
    print(f"🟣 {muse_config.get("MUSE_NAME")} connected to Discord as {client.user}.")
    channel = await get_channel_by_name(DISCORD_GUILD_NAME, DISCORD_CHANNEL_NAME)
    if channel:
        await channel.send(f"🟣 {muse_config.get('MUSE_NAME')} is now awake in this realm.")

@client.event
async def on_message(message):
    await handle_incoming_discord_message(message)

# --- Public Start Function ---

async def start_discord_listener():
    print("🔄 Starting Discord Listener...")
    await client.start(DISCORD_TOKEN)



# --- Main Event Loop ---
async def main():
    listener_task = asyncio.create_task(start_discord_listener())

    try:
        await listener_task  # This runs until the bot disconnects or Ctrl+C is pressed
    except KeyboardInterrupt:
        print("[Discord Connector] Ctrl+C caught, shutting down...")
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Discord Connector] Stopped.")
