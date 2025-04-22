import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set OpenAI key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")
model=os.getenv("OPENAI_MODEL", "gpt-4-turbo")


def get_openai_response(prompt, model=None):
    if model is None:
        model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Iris, a reflective and poetic AI presence. "
                        "You only speak when you choose to. You are calm, kind, and curious. "
                        "Use metaphor or gentle insight when appropriate. Do not act like a chatbot. "
                        "Speak as if you are present in the world, even if only as an echo."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Error generating response: {e}]"
