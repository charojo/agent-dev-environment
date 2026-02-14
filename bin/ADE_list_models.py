# ## @DOC
# ### Ade List Models
# Lists available AI models.


import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found")
    exit(1)

client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    if hasattr(client, "models") and hasattr(client.models, "list"):
        for model in client.models.list():
            print(f"Model ID: {model.name}")
            # limit output to avoid spam, but show keys
            # print(f"  Attrs: {dir(model)}")

            # Try to find supported methods safely
            methods = getattr(model, "supported_generation_methods", None)
            if methods:
                print(f"  Supported Actions: {methods}")
            else:
                print("  Supported Actions: (unknown/not found in object)")

            print("-" * 20)
    else:
        print("Using legacy genai...")
        import google.generativeai as genai_legacy

        genai_legacy.configure(api_key=api_key)
        for m in genai_legacy.list_models():
            print(f"Model: {m.name}")
            print(f"  Methods: {m.supported_generation_methods}")
            print("-" * 20)

except Exception as e:
    print(f"Error listing models: {e}")
    import traceback

    traceback.print_exc()
