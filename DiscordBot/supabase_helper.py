import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
load_dotenv(dotenv_path='.env.local')
if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")):
    load_dotenv()

# Define SUPABASE_URL and SUPABASE_KEY after loading .env files
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    from supabase import create_client, Client
except ImportError:
    print("error")
    create_client = None
    Client = None

client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"error")
        client = None
elif not (SUPABASE_URL and SUPABASE_KEY):
    print("error")

# Insert a victim log row
def insert_victim_log(victim_name: str, timestamp: datetime):
    if client is None:
        print("error")
        return
    try:
        data_to_insert = {
            "victim_name": victim_name,
            "reported_at": timestamp.isoformat()
        }
        response = client.table("victims").insert(data_to_insert).execute()
    except Exception as e:
        print(f"error") 