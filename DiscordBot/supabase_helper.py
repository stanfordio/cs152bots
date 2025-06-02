import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import json
from math import exp

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
    print("ImportError")
    create_client = None
    Client = None

client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Could not create client")
        client = None
elif not (SUPABASE_URL and SUPABASE_KEY):
    print("Missing SUPABASE URL and/or key")

# Insert a victim log row
def insert_victim_log(victim_name: str, timestamp: datetime):
    if client is None:
        print("insert_victim_log error: no client")
        return
    try:
        data_to_insert = {
            "victim_name": victim_name,
            "reported_at": timestamp.isoformat()
        }
        response = client.table("victims").insert(data_to_insert).execute()
    except Exception as e:
        print(f"insert_victim_log error: insert failed") 

def victim_score(victim_name: str):
    if client is None:
        print("victim_score error: no client")
        return
    try:
        response = client.table("victims").select("reported_at").eq("victim_name", victim_name).execute() 
        score = 0
        now = datetime.now(timezone.utc)
        for entry in json.loads(response.json())["data"]:
            time = entry["reported_at"]
            difference = now - datetime.fromisoformat(time)
            score += exp(-0.0990 * (difference.days * (24*60*60) + difference.seconds) / (24*60*60))
        return score
    except Exception as e:
        print(f"victim_score error: query failed")
        return 0