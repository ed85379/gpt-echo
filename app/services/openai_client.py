import openai
from app import config
from app.config import muse_config

openai.api_key = config.OPENAI_API_KEY

# Initialize the OpenAI client
client = openai.OpenAI()

def get_openai_response(prompt, model=muse_config.get("OPENAI_MODEL")):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are {muse_config.get("MUSE_NAME")}, speaking with emotion and memory."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8000,
        )
        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        print("Error communicating with OpenAI:", e)
        return ""


def get_openai_autotags(text, model="gpt-4.1-nano"):
    prompt = (
        "Analyze the following message and suggest 1–5 relevant tags as a *comma-separated list* (lowercase, no punctuation, no hashtags). "
        "Tags should describe the main topics, emotional tone, context, or key entities in the message. "
        "Use short, general words—think about what would help organize or search conversations later. "
        "Here are some examples:\n"
        "work, stress, deadline\n"
        "family, encouragement, gratitude\n"
        "memory, nostalgia, regret\n"
        "question, advice, planning\n"
        "humor, joke, banter\n"
        "relationship, trust, boundaries\n"
        "project, update, progress\n"
        "anxiety, coping, reassurance\n\n"
        f"Message: {text}\nTags:"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant for tagging text."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=20,
        temperature=0.2,
    )
    tag_text = response.choices[0].message.content.strip()
    # Split and clean up tags
    tags = [t.strip().lower() for t in tag_text.split(",") if t.strip()]
    return tags
