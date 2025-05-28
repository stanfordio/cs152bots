import sys
import os
from datetime import datetime
from LLM_reports import LLM_report


# Test cases
test_data_1 = {
    "message_content": "BREAKING: Scientists confirm that COVID vaccines contain microchips to track your movements. Share before this gets deleted!",
    "classifier_label": "potential_misinfo",
    "confidence_score": 0.92,
    "metadata": {
        "message_guild_id": "123456789012345678",
        "message_author": "HealthTruth88",
        "hashtags": ["#vaccine", "#truth", "#covid"],
        "violation count": 2
    },
    "reporter_info": "ModerationBot"
}

test_data_2 = {
    "message_content": "CONFIRMED: The election was rigged! Counting machines were programmed to switch votes. The evidence is being suppressed by the government!",
    "classifier_label": "political_misinfo",
    "confidence_score": 0.89,
    "metadata": {
        "message_guild_id": "876543210987654321",
        "message_author": "PatriotTruth1776",
        "hashtags": ["#election", "#fraud", "#truth"],
        "violation count": 1
    },
    "reporter_info": "ElectionIntegrity"
}

test_data_3 = {
    "message_content": "Scientists have been hiding the truth: the Earth is flat and NASA has been faking space photos for decades!",
    "classifier_label": "potential_misinfo",
    "confidence_score": 0.75,
    "metadata": {
        "message_guild_id": "555666777888999000",
        "message_author": "TruthSeeker42",
        "hashtags": ["#flatearth", "#nasa", "#truth"],
        "violation count": 0
    },
    "reporter_info": "ScienceChannel"
}

test_data_4 = {
    "message_content": "I've heard some people say that drinking lemon water every morning can boost your immune system by 50%. Interesting!",
    "classifier_label": "potential_misinfo",
    "confidence_score": 0.58,
    "metadata": {
        "message_guild_id": "111222333444555666",
        "message_author": "WellnessJourney",
        "hashtags": ["#health", "#wellness", "#immunity"],
        "violation count": 0
    },
    "reporter_info": "HealthFacts"
}

test_data_5 = {
    "message_content": "According to the CDC website updated yesterday, vaccination rates have increased by 15% nationwide in the past month.",
    "classifier_label": "potential_misinfo",
    "confidence_score": 0.35,
    "metadata": {
        "message_guild_id": "999888777666555444",
        "message_author": "NewsUpdates",
        "hashtags": ["#covid", "#vaccination", "#data"],
        "violation count": 0
    },
    "reporter_info": "FactChecker"
}

test_data_6 = {
    "message_content": "URGENT investment opportunity! Send $500 in Bitcoin to this wallet and I guarantee you'll receive $5000 back within 24 hours. This is a secret method banks don't want you to know!",
    "classifier_label": "potential_scam",
    "confidence_score": 0.95,
    "metadata": {
        "message_guild_id": "444333222111000999",
        "message_author": "WealthMaker2023",
        "hashtags": ["#investment", "#bitcoin", "#getrich"],
        "violation count": 3
    },
    "reporter_info": "ScamAlert"
}

if __name__ == "__main__":
    print("Starting LLM Report Tests...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_cases = [test_data_1, test_data_2, test_data_3, test_data_4, test_data_5, test_data_6]

    # Generate report details for sample flagged posts
    for post in test_cases :
        report_details = LLM_report(post["message_content"],
                    post["classifier_label"],
                    post["confidence_score"],
                    post["metadata"],
                    post["reporter_info"])
        

        print("\nResults:")
        print(f"Report Type: {report_details.get('report_type', 'Not classified')}")
        print(f"Misinfo Type: {report_details.get('misinfo_type', 'N/A')}")
        print(f"Misinfo Subtype: {report_details.get('misinfo_subtype', 'N/A')}")
        print(f"Imminent Harm: {report_details.get('imminent', 'None')}")
        print(f"Filter Recommendation: {report_details.get('filter', 'No recommendation')}")
        print(f"LLM Recommendation: {report_details.get('LLM_recommendation', 'No recommendation')}")

    print("\nTests complete!")