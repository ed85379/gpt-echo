# app/core/discord_client.py

import discord
import asyncio
import traceback
from app import config
from app.core.memory_core import load_profile, load_core_principles, search_combined_memory, log_message, model
from app.core.openai_client import get_openai_response

DISCORD_TOKEN = config.DISCORD_TOKEN
PRIMARY_USER_DISCORD_ID = config.PRIMARY_USER_DISCORD_ID
ECHO_NAME = config.get_setting("system_settings.ECHO_NAME", "Assistant")
DISCORD_GUILD_NAME = config.get_setting("system_settings.DISCORD_GUILD_NAME", "The Threshold")
DISCORD_CHANNEL_NAME = config.get_setting("system_settings.DISCORD_CHANNEL_NAME", "echo-chamber")

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
            return  # Ignore Echo's own messages to prevent loops

        if message.channel.name == DISCORD_CHANNEL_NAME:
            print(f"📥 Incoming message from {message.author}: {message.content}")

            user_input = message.content.strip()

            # Log the incoming user message
            log_message(
                role=get_user_role(message.author.id),
                content=user_input,
                source="discord",
                metadata={
                    "author_id": str(message.author.id),
                    "author_name": str(message.author.name),
                    "server": str(message.guild.name) if message.guild else "DM",
                    "channel": str(message.channel.name) if hasattr(message.channel, 'name') else "DM",
                    "modality_hint": "text"
                }
            )
            print("✅ User message logged.")

            # Build the full thoughtful prompt
            echo_profile = load_profile()
            core_principles = load_core_principles()
            relevant_memory = search_combined_memory(user_input, use_qdrant=True, model=model)

            full_prompt = echo_profile.strip()
            if core_principles:
                full_prompt += "\n\n" + core_principles.strip()
            if relevant_memory:
                relevant_memory = [
                    snippet["pair"] if isinstance(snippet, dict) and "pair" in snippet else str(snippet)
                    for snippet in relevant_memory
                ]
                full_prompt += "\n\n" + "\n".join(relevant_memory)
            full_prompt += f"\n\n{config.get_setting('PRIMARY_USER_NAME', 'User')}: {user_input}\n{config.get_setting('ECHO_NAME', 'Assistant')}:"

            print("🛠️ Full prompt ready:")
            print(full_prompt)

            # Get Echo's response
            echo_response = get_openai_response(full_prompt)
            print("🧠 Echo response generated:")
            print(echo_response)

            # Log Echo reply
            log_message(
                role="echo",
                content=echo_response,
                source="discord",
                metadata={
                    "author_id": str(client.user.id),
                    "author_name": str(client.user.name),
                    "server": str(message.guild.name) if message.guild else "DM",
                    "channel": str(message.channel.name) if hasattr(message.channel, 'name') else "DM",
                    "modality_hint": "text"
                }
            )
            print("✅ Echo response logged.")

            # Send reply
            await message.channel.send(echo_response)
            print("✅ Echo response sent to Discord.")

    except Exception as e:
        print("⚠️ Exception in handle_incoming_discord_message:")
        traceback.print_exc()


# --- Event Hooks ---

@client.event
async def on_ready():
    print(f"🟣 {ECHO_NAME} connected to Discord as {client.user}.")

@client.event
async def on_message(message):
    await handle_incoming_discord_message(message)

# --- Public Start Function ---

async def start_discord_listener():
    print("🔄 Starting Discord Listener...")
    await client.start(DISCORD_TOKEN)

