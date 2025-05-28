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


def call_gemini(sys_instruction, content):
    response = client.models.generate_content(
        model= "gemini-2.0-flash",
        config=types.GenerateContentConfig(
        system_instruction= sys_instruction,
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
    report_type_reponse = call_report_type(message_content, classifier_label, confidence_score,metadata)
    
    # Update misinfo_type in report details
    if report_type_reponse in ["1", "2"] :
        report_details['report_type'] = "Misinformation" if report_type_reponse == "1" else "other"

        # Initiate userflow for misiniformation
        if report_type_reponse == "1" :

            # Call to classify type of misinformation
            misinfo_type_response = call_misinfo_type(message_content)

             #================== Decision logic for Misinformation Type Response ==================
            
            # Political Misinfo
            if misinfo_type_response ==  "1" :
                report_details ['misinfo_type'] = "Political Misinformation"

                # Call to classify political misinfo subtype
                pol_misinfo_subtype_response  =  call_pol_misinfo_subtype(message_content)

                #=============== Decision logic for Political misinfo subtye response ===============
                if pol_misinfo_subtype_response == "1":
                    report_details['misinfo_subtype'] = 'Election/Campaign Misinformation'
                
                elif pol_misinfo_subtype_response == "2":
                    report_details['misinfo_subtype'] = 'Government/Civic Services'
                
                elif pol_misinfo_subtype_response == "3":
                    report_details['misinfo_subtype'] = 'Manipulated Photos/Video'

                elif pol_misinfo_subtype_response == "4":
                    report_details['misinfo_subtype'] = 'Other'
            
            # Health Misinfo
            elif misinfo_type_response == "2" :
                report_details ['misinfo_type'] = "Health Misinformation"

                 # Call to classify health misinfo subtype
                health_misinfo_subtype_response = call_health_misinfo_subtype(message_content)

                #=============== Decision logic for Health misinfo subtye response ===============
                if health_misinfo_subtype_response == "1":
                    report_details['misinfo_subtype'] = 'Vaccines'
                
                elif health_misinfo_subtype_response == "2":
                    report_details['misinfo_subtype'] = 'Cures and Treatments'
                    
                elif health_misinfo_subtype_response == "3":
                    report_details['misinfo_subtype'] = 'Mental Health'

                elif health_misinfo_subtype_response == "4":
                    report_details['misinfo_subtype'] = 'Oher'

            
            elif misinfo_type_response == "3" :
                report_details ['misinfo_type'] = "Other Misinformation"
                report_details['misinfo_subtype'] = 'Other'


        # Initiate userfflow for Harmful content
        imminent_response = call_imminent(message_content)

        #================== Decision logic for Imminent Harm Response ==================

        if imminent_response == "2":
            report_details['imminent'] = 'physical'

        elif imminent_response == "3":
            report_details['imminent'] = 'mental'
        
        elif imminent_response == "4":
            report_details['imminent'] = 'financial or property'
            

    # Think about logic for instances where LLM returns non option value

  




def call_report_type(message_content, classifier_label, confidence_score,metadata):
    # Step 1: Initial classification - Misinformation or Other
    print("====Step 1: Initial classification - Misinformation or Other===")
    print(f"Message: {message_content}")

    system_instruction = f"""
     You are a trust & safety expert content moderator for a social media platform who has been assigned to generate a user
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
    # Step 2: Type of Misinformation
    print("====Step 2: Misinformation type ===")
    
    system_instruction = f"""
    You are a misinformation trust & safety expert content moderator for a social media platform who has been assigned to analyze content reported
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



def call_pol_misinfo_subtype(message_content):
    # Step 3a. Type of Political Misinformation
    print("====Step 3a. Type of Political Misinformation ===")

    system_instruction = f"""
    You are a political trust & safety expert content moderator for a social media platform who has been assigned to analyze content reported
    as political misinformation.
                         """
    
    content = f"""
    Mesaage Content: {message_content}
    Classify the type of political  misinformation which the message falls under :
        1. Election/Campaign Misinformation
        2. Government/Civic Services
        3. Manipulated Photos/Video
        4. Other political misinformation
    
    Respond with ONLY the number (1-4).
              """

    return call_gemini(system_instruction, content)



def call_health_misinfo_subtype(message_content):
    # Step 3b. Type of Health Misinformation
    print("====Step 3b. Type of Health Misinformation ===")

    system_instruction = f"""
    You are a health trust & safety expert content moderator for a social media platform who has been assigned to analyze content reported
    as health misinformation.
                         """
    
    content = f"""
    Mesaage Content: {message_content}
    Classify the type of health  misinformation which the message falls under :
        1. Vaccines
        2. Cures and Treatments
        3. Mental Health
        4. Other health misinformation
            
    Respond with ONLY the number (1-4).
               """
    
    return call_gemini(system_instruction,content)


def call_imminent(message_content):
    # Step 4: Imminent Harm 
    print("====Step 4: Imminent Harm===")

    system_instruction = f"""
    You are a trust & safety expert content moderator for a social media platform who has been assigned to analyze content reported
    and assess potential harm of the reported content.
                         """
    
    content = f"""
    Mesaage Content: {message_content}
    Could this content likely cause imminent harm to people or public safety?
        1. No
        2. Yes, physical harm
        3. Yes, mental harm
        4. Yes, financial or property harm
        
    Respond with ONLY the number (1-4).
              """
    
    return call_gemini(system_instruction, content)

