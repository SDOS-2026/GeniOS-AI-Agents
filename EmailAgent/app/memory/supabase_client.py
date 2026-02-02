from supabase import create_client
from dotenv import load_dotenv
import os
import warnings

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_ENABLED = os.getenv("SUPABASE_ENABLED", "false").lower() == "true"

# Initialize Supabase client if credentials are properly configured
supabase = None

if SUPABASE_ENABLED and SUPABASE_URL and SUPABASE_KEY:
    if "xxxx" not in SUPABASE_URL and "your_anon" not in SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✅ Supabase client initialized successfully")
        except Exception as e:
            print(f"⚠️ Warning: Failed to initialize Supabase: {e}")
            print("Memory features will be disabled")
            supabase = None
    else:
        print("⚠️ Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
        print("Memory features will be disabled. This is OK for basic operation.")
else:
    print("ℹ️ Supabase is disabled. Set SUPABASE_ENABLED=true in .env to enable memory features.")
