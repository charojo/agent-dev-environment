# ## @DOC
# ### Ade Check Models
# Checks availability of required AI models.

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available Models:")
for model in client.models.list():
    print(f"- {model.name}")
