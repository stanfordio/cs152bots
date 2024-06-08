import json
from supabase import create_client, Client
import discord

with open("tokens.json", "r") as f:
    tokens = json.load(f)

SUPABASE_URL = tokens.get("SUPABASE_URL")
SUPABASE_KEY = tokens.get("SUPABASE_KEY")

class SupabaseClient:
    def __init__(self) -> None:
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    def store_report(self, report):
        reasons_text = ', '.join(report.reason)
        data = {
            'priority': report.priority,
            'reported_user': str(report.message.author.id),
            'reported_by': str(report.user_id),
            'reported_message': report.message.content,
            'message_link': report.message_link,
            'reasons': reasons_text,
        }
        self.client.table('Reports').insert(data).execute()
        self.increment_num_reports_received(report.message.author.id)
        self.increment_num_reports_submitted(report.user_id)

    def fetch_num_reports_received(self, user):
        data, count = self.client.table('UserStats') \
                .select('num_reports_received') \
                .eq('user', user) \
                .execute()
        if data[1]:
            return data[1][0]['num_reports_received']
        else:
            return 0

    def fetch_num_reports_submitted(self, user):
        data, count = self.client.table('UserStats') \
                .select('num_reports_submitted') \
                .eq('user', user) \
                .execute()
        if data[1]:
            return data[1][0]['num_reports_submitted']
        else:
            return 0
    
    def fetch_num_false_reports_submitted(self, user):
        data, count = self.client.table('UserStats') \
                .select('num_false_reports_submitted') \
                .eq('user', user) \
                .execute()
        if data[1]:
            return data[1][0]['num_false_reports_submitted']
        else:
            return 0

    def increment_num_reports_received(self, user):
        num = self.fetch_num_reports_received(user)
        self.client.table('UserStats') \
                .upsert({'user': user, 'num_reports_received': num + 1}) \
                .execute()

    def increment_num_reports_submitted(self, user):
        num = self.fetch_num_reports_submitted(user)
        self.client.table('UserStats') \
                .upsert({'user': user, 'num_reports_submitted': num + 1}) \
                .execute()
    
    def increment_num_false_reports_submitted(self, user):
        num = self.fetch_num_false_reports_submitted(user)
        self.client.table('UserStats') \
                .upsert({'user': user, 'num_false_reports_submitted': num + 1}) \
                .execute()

    def fetch_total_num_reports(self):
        data, count = self.client.table('Reports') \
                .select('*', count='exact') \
                .eq('closed', False) \
                .execute()
        return count[1]
        

    def fetch_next_report(self):
        try:
            data, count = self.client.table('Reports') \
                    .select('*') \
                    .order('priority') \
                    .order('created_at') \
                    .eq('closed', False) \
                    .limit(1) \
                    .single() \
                    .execute()
            return data[1]
        except:
            return None

    def close_report(self, report_id):
        data, count = self.client.table('Reports') \
                .update({'closed': True}) \
                .eq('id', report_id) \
                .execute()
        
    def ban_user(self, user):
        data, count = self.client.table('UserStats') \
                .update({'banned': True}) \
                .eq('user', user) \
                .execute()
    
    def is_user_banned(self, user):
        data, count = self.client.table('UserStats') \
                .select('banned') \
                .eq('user', user) \
                .execute()
        return data[1][0]['banned'] 
        

