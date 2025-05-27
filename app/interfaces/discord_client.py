# app/core/discord_client.py

import discord
import traceback
from app import config
from app.core import memory_core
from app.services import openai_client
from app.core import prompt_builder

DISCORD_TOKEN = config.DISCORD_TOKEN
PRIMARY_USER_DISCORD_ID = config.PRIMARY_USER_DISCORD_ID
MUSE_NAME = config.MUSE_NAME
DISCORD_GUILD_NAME = config.DISCORD_GUILD_NAME
DISCORD_CHANNEL_NAME = config.DISCORD_CHANNEL_NAME


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
            memory_core.log_message(
                role=get_user_role(message.author.id),
                content=user_input,
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
            builder.add_profile()
            builder.add_core_principles()
            builder.add_cortex_entries(["insight", "seed"])
            builder.add_prompt_context(user_input)
            builder.add_graphdb_discord_memory(author_name=message.author.name, author_id=message.author.id)
            #builder.add_journal_thoughts(query=user_input)
            #    builder.add_discovery_snippets()  # Optional: you can comment this out if you want a cleaner test
            builder.add_formatting_instructions()

            # Assemble final prompt
            full_prompt = builder.build_prompt()
            full_prompt += f"\n\n{message.author.name}: {user_input}\n{config.get_setting('MUSE_NAME', 'Assistant')}:"
            #print("🛠️ Full prompt ready:")
            #print(full_prompt)
            # Get Muse's response
            muse_response = openai_client.get_openai_response(full_prompt)
            #print("🧠 Muse response generated:")
            #print(muse_response)

            # Log Muse reply
            memory_core.log_message(
                role="muse",
                content=muse_response,
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


# --- Event Hooks ---

@client.event
async def on_ready():
    print(f"🟣 {MUSE_NAME} connected to Discord as {client.user}.")

@client.event
async def on_message(message):
    await handle_incoming_discord_message(message)

# --- Public Start Function ---

async def start_discord_listener():
    print("🔄 Starting Discord Listener...")
    await client.start(DISCORD_TOKEN)

