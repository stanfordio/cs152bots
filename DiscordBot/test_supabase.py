# This is to test if the supabase works 

from supabase_helper import insert_victim_log
from datetime import datetime

def test_insert():
    victim_name = "TestVictim"
    timestamp = datetime.now()
    print(f"Attempting to insert log for {victim_name} at {timestamp}")
    insert_victim_log(victim_name, timestamp)
    print("Insertion attempt finished")

if __name__ == "__main__":
    test_insert() 