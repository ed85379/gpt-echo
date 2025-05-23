import openai
from app import config

openai.api_key = config.OPENAI_API_KEY
ECHO_NAME = config.ECHO_NAME
OPENAI_MODEL = config.OPENAI_MODEL

# Initialize the OpenAI client
client = openai.OpenAI()

def get_openai_response(prompt, model=OPENAI_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"You are {ECHO_NAME}, speaking with emotion and memory."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        reply = response.choices[0].message.content
        return reply
    except Exception as e:
        print("Error communicating with OpenAI:", e)
        return ""
