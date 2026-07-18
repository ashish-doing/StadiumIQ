"""
check_model.py — finds out which Gemini model actually works with YOUR API key,
right now, instead of guessing from documentation that might be stale.

Usage:
    python check_model.py

Reads GEMINI_API_KEY from your .env file automatically. Makes a handful of
tiny test calls (a few tokens each) — this will NOT meaningfully touch your
daily quota.
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY not found in your .env file. Fix that first.")
    exit(1)

genai.configure(api_key=api_key)

print("=" * 60)
print("STEP 1: Models your key can actually see (via list_models)")
print("=" * 60)
try:
    available = []
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            available.append(m.name)
            print(f"  {m.name}")
except Exception as e:
    print(f"  Could not list models: {e}")
    available = []

print()
print("=" * 60)
print("STEP 2: Live test call against each realistic candidate")
print("=" * 60)

candidates = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

working = []
for name in candidates:
    try:
        model = genai.GenerativeModel(name)
        response = model.generate_content("Reply with exactly one word: OK")
        text = response.text.strip()
        print(f"  ✅ {name} — WORKS (replied: {text!r})")
        working.append(name)
    except Exception as e:
        err = str(e)[:100]
        print(f"  ❌ {name} — FAILED ({err}...)")

print()
print("=" * 60)
print("RECOMMENDATION")
print("=" * 60)
if working:
    print(f"Use this model in gemini_client.py: \"{working[0]}\"")
    if len(working) > 1:
        print(f"(Other working options: {', '.join(working[1:])})")
else:
    print("None of the candidates worked. Check:")
    print("  1. Is GEMINI_API_KEY actually valid? (copy-paste error?)")
    print("  2. Was this key created under 'new project' at aistudio.google.com?")
    print("  3. Try creating a completely fresh key and re-running this script.")