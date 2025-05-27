from google import genai

# Load API key from a text file
try:
    with open("api_key.txt", "r") as f:
        api_key = f.read().strip()
    client = genai.Client(api_key=api_key)
except FileNotFoundError:
    print("Error: API key file not found. Create 'api_key.txt' with your API key.")
    exit(1)
except Exception as e:
    print(f"Error loading API key: {e}")
    exit(1)


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

    # Perform initial Classification 
    classification_reponse = initial_classification()
    
    # Update misinfo_type in report details
    if classification_reponse in ["1", "2"] :
        report_details['misinfo_type'] = "Misinformation" if classification_reponse == "1" else "other"

        # Initiate userflow for misiniformation
        if classification_reponse == "1" :
            misinfo_type_response = call_misinfo_type(message_content)
    
    # Think about logic for instances where LLM returns non option value




def initial_classification(message_content, classifier_label, confidence_score,metadata):
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

    Validate the classifier's decision by selecting a category:
    1. Misinformation
    2. Other inappropriate content

    Respond with ONLY the number (1 or 2).
    """

    
    return  call_gemini (system_instruction, content)

def call_misinfo_type (message_content):
    # Step 2: Initial classification - Misinformation or Other
    print("====Step 2: Misinformation type ===")
    
    system_instruction = f"""
    You are an expert content moderator for a social media platform who has been assigned to analyze content reported
    as misinformation.
                        """
    
    content = f"""
     Mesaage Content: {message_content}
     Please select the type of misinformation:
        1. Political Misinformation
        2. Health Misinformation
        3. Other Misinformation
        
    Respond with ONLY the number (1-3).
                """
    
    return call_gemini(system_instruction, content)







