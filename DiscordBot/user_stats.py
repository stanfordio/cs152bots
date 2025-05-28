import json
import os
from datetime import datetime

class UserStats:
    def __init__(self):
        self.stats_file = 'user_stats.json'
        # Clear the stats file on initialization
        self._clear_stats()
        self.stats = self._load_stats()

    def _clear_stats(self):
        # Create an empty stats file
        with open(self.stats_file, 'w') as f:
            json.dump({}, f)

    def _load_stats(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def add_report(self, user_id, report_type, report_content, outcome, explanation=None):
        if user_id not in self.stats:
            self.stats[user_id] = {
                'total_reports': 0,
                'reports': []
            }
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'report_type': report_type,
            'report_content': report_content,
            'outcome': outcome,
            'explanation': explanation
        }
        
        self.stats[user_id]['reports'].append(report)
        self.stats[user_id]['total_reports'] = len(self.stats[user_id]['reports'])
        self._save_stats()

    def get_user_stats(self, user_id):
        return self.stats.get(user_id, {
            'total_reports': 0,
            'reports': []
        })

    def get_all_stats(self):
        return self.stats 