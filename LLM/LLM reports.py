from google import genai
from ../report import Report

client = genai.Client(api_key="YOUR_API_KEY")

# response = client.models.generate_content(
#     model="gemini-2.0-flash",
#     config=types.GenerateContentConfig(
#         system_instruction="You are a content moderation assistant for a Discord bot. Analyze the reported message and classify it into one of the specified categories. Respond with ONLY the category number."),
#     contents="Hello there"
# )

# print(response.text)

def call_gemini(system_instruction, content):
    response = client.models.generate_content(
        model= "gemini-2.0-flash",
        config=types.GenerateContentConfig(
        system_instruction= system_instruction,
        contents= content)
    )

    return response.text
    


#  Function to invoke report generation
def LLM_report(message_content, classifier_label, confidence_score,metadata, reporter_info = 'Classifier'):

    #  Dictionary for keeping track of report details
    report_details = {
        'message_guild_id' : f"{metadata.get('message_guild_id')}",
        'reported_author' : f"{metadata.get('message_author')}",
        'reported_content' : message_content,
        'report_type' : None,
        'misinfo_type' : None,
        'misinfo_subtype': None,
        'filter' : False,
        'imminent' : None
    }

    # Step 1: Initial classification - Misinformation or Other
    print("====Step 1: Initial classification - Misinformation or Other===")
    print(f"Message: {message_content}")

    system_instruction = f"""
     You are an expert content moderator for a social media platform who has been assigned to generate a user
     report for a post that has been flagged by the platform's classifier.
                         """

    content = f""" 

    Message Content : {message_content},

    Initial Classification from the Automated Post Classifier:
    - Label : {classifier_label},
    - Confidence : {confidence_score},

    Metadata :
    - Hashtags : {metadata.get('hashtags', 'Unkown')},
    - Previous Violation Count : {metadata.get('violation count', '0')}

    Reporter Info :
    - Reporter's Name : {reporter_info}

    Validate the classifier's decision by selecting a category:
    1. Misinformation
    2. Other inappropriate content

    Respond with ONLY the number (1 or 2).
    """

    
    report_type = call_gemini (system_instruction, content)








