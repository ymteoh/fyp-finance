# check_models.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load your API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env")
    exit(1)

# Configure and list models
genai.configure(api_key=api_key)

print("✅ Available models that support generateContent:\n")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f" • {m.name}")