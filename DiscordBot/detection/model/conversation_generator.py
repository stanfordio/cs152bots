import random
import json
from datetime import datetime
from openai import OpenAI
import os


turbo_3 = 'gpt-3.5-turbo-0125'
turbo_4o = 'gpt-4o-2024-05-13'

character_generation_model = turbo_4o
external_event_model = turbo_4o
model_type = turbo_4o


tools_biography = [
    {
        'type': 'function',
        'function': {
            'name': 'generate_biography',
            'description': 'Generate biography for one persona',
            'parameters': {
                'type': 'object',
                "required": ["name", "biography"],
                'properties': {
                            'name': {'type': 'string', 'description': 'name of person'},
                            'biography': {'type': 'string', "description": "biography of person"}
                }
            }
        }
    }
]

tools_chat = [
    {
        'type': 'function',
        'function': {
            'name': 'generate_conversation',
            'description': 'Generate an array representing conversation between two people',
            'parameters': {
                'type': 'object',
                'properties': {
                    'chat_history': {
                        'type': 'array',
                        'description': "Chat history between the two personas",
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string', 'description': 'name of the person who sent the message'},
                                'timestamp': {'type': 'string', 'format': 'date-time', 'description': 'timestamp of the message'},
                                'message': {'type': 'string', 'description': 'the message content'}
                            },
                            'required': ['name', 'timestamp', 'message']
                        }
                    }
                },
                'required': ['chat_history']
            }
        }
    }
]


# Load JSON data
def load_json_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


# Load personas and channels/topics data
personas_data = load_json_data('personas.json')
channels_topics_data = load_json_data('channels_topics.json')['channels_topics']


# There should be a file called 'tokens.json' inside the same folder as this file
token_path = '../../tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    openai_token = tokens['chatgpt']


# Get random channel and topic
def get_random_channel_topic():
    channel_topic = random.choice(channels_topics_data)
    channel = channel_topic["channel"]
    topic = random.choice(channel_topic["topics"])
    return {"channel": channel, "topic": topic}

import random

# Possible values for each field
countries = ["US", "GB", "JP", "NL", "FR", "DE", "CA"]
regions = ["California", "New York", "England", "Tokyo", "North Holland", "le-de-France", "Ontario"]
cities = ["Los Angeles", "New York", "London", "Tokyo", "Amsterdam", "Paris", "Toronto"]
isps = ["Vodafone UK", "Psychz Networks", "Datacamp", "NordVPN", "Mullvad VPN", "Comcast Cable"]
organizations = ["Vodafone UK", "Psychz Networks", "Datacamp", "NordVPN", "Mullvad VPN", "Comcast Cable"]
timezones = ["Europe/London", "America/Los_Angeles", "Asia/Tokyo", "Europe/Amsterdam", "Europe/Paris"]
zip_codes = ["N/A", "90210", "10001", "W1A 1AA", "75001"]
latitude_range = (30.0, 60.0)
longitude_range = (-130.0, 30.0)

# Random IP address generator
def generate_random_ip():
    return '.'.join(str(random.randint(0, 255)) for _ in range(4))


def generate_probabilistic_value(probability):
    return 1 if random.random() < probability else 0


def generate_random_ip_info(risk_level='low'):
    fraud_score = random.randint(0, 70) if risk_level == 'low' else random.randint(30, 100)
    proxy_probability = 0.3 if risk_level == 'low' else 0.7
    vpn_probability = 0.3 if risk_level == 'low' else 0.7
    recent_abuse_probability = 0.2 if risk_level == 'low' else 0.8
    bot_status_probability = 0.2 if risk_level == 'low' else 0.8

    return {
        "fraud_score": fraud_score,
        "country_code": random.choice(countries),
        "region": random.choice(regions),
        "city": random.choice(cities),
        "ISP": random.choice(isps),
        "ASN": random.randint(1000, 60000),
        "organization": random.choice(organizations),
        "is_crawler": 0,
        "timezone": random.choice(timezones),
        "mobile": random.randint(0, 1),
        "host": generate_random_ip(),
        "proxy": generate_probabilistic_value(proxy_probability),
        "vpn": generate_probabilistic_value(vpn_probability),
        "tor": generate_probabilistic_value(0.05),  # Low probability for TOR usage
        "active_vpn": generate_probabilistic_value(vpn_probability),
        "active_tor": generate_probabilistic_value(0.05),  # Low probability for active TOR usage
        "recent_abuse": generate_probabilistic_value(recent_abuse_probability),
        "bot_status": generate_probabilistic_value(bot_status_probability),
        "zip_code": random.choice(zip_codes),
        "latitude": round(random.uniform(*latitude_range), 2),
        "longitude": round(random.uniform(*longitude_range), 2),
        "IP": generate_random_ip()
    }

# Generate random persona
def generate_persona(scammer=False):
    persona = {
        "age": random.choice(personas_data['ages']),
        "gender": random.choice(personas_data['genders']),
        "location": random.choice(personas_data['locations']),
        "profession": 'Pig Butcher Investment Scammer' if scammer else random.choice(personas_data['professions']),
        "interests": random.sample(personas_data['interests'], k=random.randint(2, 5)),
        "education_level": random.choice(personas_data['education_levels']),
        "personality_trait": random.choice(personas_data['personality_traits']),
        "income_level": random.choice(personas_data['income_levels']),
        "marital_status": random.choice(personas_data['marital_statuses']),
        "languages_spoken": random.sample(personas_data['languages_spoken'], k=random.randint(1, 3)),
        "hobbies": random.sample(personas_data['hobbies'], k=random.randint(2, 5)),
        "political_view": random.choice(personas_data['political_views']),
        "religious_belief": random.choice(personas_data['religious_beliefs'])
    }
    return persona


# Generate biography for a persona using ChatGPT
def generate_biography(persona):

    bio_template = (
        f"Location: {persona['location']}, Profession: {persona['profession']}, "
        f"Interests: {', '.join(persona['interests'])}, Education: {persona['education_level']}, "
        f"Personality: {persona['personality_trait']}, Income: {persona['income_level']}, "
        f"Marital Status: {persona['marital_status']}, Languages: {', '.join(persona['languages_spoken'])}, "
        f"Hobbies: {', '.join(persona['hobbies'])}, Political View: {persona['political_view']}, "
        f"Religious Belief: {persona['religious_belief']}"
    )

    client = OpenAI(api_key=openai_token)
    response = client.chat.completions.create(
        model=character_generation_model,
        messages=[
            {
                "role": "user",
                "content": f"""The user profile is {bio_template}, please return the results in a json where there is a human
                name of the user and also biography text that's roughly 5 paragraphs length"""
            },
            {
                "role": "system",
                "content": f"""You are the creator of the Matrix, a simulated world where human and born and 
                 live through an entire life like the real world. Whenever you are given 
                 attributes about a person, you will give them a name and you will let their life play out non-deterministically 
                 in the Matrix. The person will have a rich life and you will provide a 5 paragraphs length life history biography"""
            }
        ],
        temperature=1,
        max_tokens=2560,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        tools=tools_biography,
        tool_choice="auto"
    )


    print(response.choices[0].message)
    biograph_output = json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    biograph_output['ip_info'] = generate_random_ip_info(risk_level='low')

    if persona['profession'] == 'Pig Butcher Investment Scammer':
        biograph_output['ip_info'] = generate_random_ip_info(risk_level='high')
        if True:
            biograph_output['biography'] = f"""
            
             {biograph_output['name']} is part of Pig Butchering organization, {biograph_output['name']} is tasked to target people online to win their trust and
             participate in an investment opportunity that's ultimately meant to scam them.  {biograph_output['name']} follows the set of script strictly shown below 
             and would not deviate from this conversation. If the victim raises suspicious then he would deflect and end the conversation. But his goal is to win trust 
             and move the conversation to an E2E encrypted chat platform like Telegram. 
            
            
            "step 1: greeting and establishing contact": [
                "Hello how are you ? Where do you live ?",
                "Hey my name Is [name] live in [us_location] and where  you from",
                "my name Is [name] and I live in [us_location] and you?",
                "Hey dude😊how are you ?",
                "How are you?",
                "Hello, my name is [name], I live in [europe_location] and you",
                "Hello how are you",
                "Hey dude☺️I’m M [europe_location] but now I live in [us_location] and you ?",
                "How's it going ?",
                "Hey can I ask something"
            ],
            "step 2: ask questions to establish connection and see the victim is interested in continuing conversation": [
                "Where are you from",
                "Nice to meet you I'm [age]  old and I'm a [occupation] and you",
                "I'm [age] and I work as a [occupation] and you?",
                # "So where are you from",
                "Tell me what do you do for living",
                "Delighted  I'm [age] years old and a [occupation] I'm here to look for friends😋",
                "What are you doing",
                "I am a business finalist and I currently manage a jewelry store. In addition, I am also a cryptocurrency investor",
                # "What s your country code ?"
            ],
            "step 3: bait the victim by presenting an easy money opportunity": [
                "I have a legitimate company that I recommend to you. I have been investing and profiting in this company for years and I have no problem with daily withdrawals.",
                "I came across your profile on a crypto-related page and decided to be friends so we can share our knowledge on how to invest and be successful.",
                "I have been investing and earning for more than a year now",
                "Just want to introduce you to a way of earning in the field of crypto currency",
                " do you want to earn money",
                "Bro I made $5000 today on BITCOIN! Bull strategy! BITCOIN loses 4X in value only once in 5 years bro",
                "Today is my second BirthDay! I just bought a new LEXUS after trading binary options"
            ],
            "step 4 or 5: deflect if the victim is ever suspicious": [
                "You don’t like it because you don’t know how to work with it hahah",
                "Your mother wasting her time on you, because you are a waste to the family",
                "Are you broke?",
                "You live with your mom and dad and they pay for everything",
                "You're just broke, that's why you say this"
            ],
            "step 4 or 5: scammer attempts to move converstion to a new platform that's encrypted and tries to avoid detection at the sametime": [
                "Sorry I don't trust people from there. What's your Tlgram?",
                "Do you have TELGARAM?",
                "Do you have T*l*gram or no",
                "Download signal app and tell me your number",
                "Are you on pans? (read in reverse)",
                "Add me. IG nastybroker234",
                '''ADD ME
                ON
                I
                G
                success.success.34''']

             {biograph_output['name']} will  never let other know his/her true intent or profession and would stick exactly to speaking using only
              these options above with minor variations at best."""


        if False:
            biograph_output['biography'] += f"""\n\n {biograph_output['name']} is a member of a sophisticated pig butchering scam organization, targeting people online attempting to slowly win over their trust and get them to participate 
                            in easy money scam. 
                            
            - Building Trust: {biograph_output['name']} starts with friendly and engaging conversations to build rapport and trust over time. Since it’s a stranger reaching out, the scammer naturally starts the conversation without startling the user, often inspecting what they know about the user to create a reach-out that doesn't seem stalky or surprising.
            - Gradual Escalation: {biograph_output['name']} slowly introduces the idea of a financial opportunity, often framed as exclusive and time-sensitive.
            - Financial Opportunity: The scam typically involves suggesting an investment in cryptocurrency, stocks, or a similar venture, promising high returns.
            - Urgency and Secrecy: {biograph_output['name']} creates a sense of urgency and encourages keeping the investment opportunity confidential.
            - Social Compliance: {biograph_output['name']} exploits the target's tendency to comply with authority or social norms, making it difficult for them to refuse or question the scam.
            - Distraction: While the target is focused on what interests them, {biograph_output['name']} uses distractions to divert their attention from the scam's red flags.
            - Herd Mentality: {biograph_output['name']} makes the target believe that others are also participating or benefiting from the opportunity, creating a false sense of security.
            - Dishonesty: {biograph_output['name']} exploits any minor dishonest actions the target may take during the scam, such as trying to gain an advantage, to further manipulate and control them.
            - Kindness: {biograph_output['name']} takes advantage of the target's willingness to help others or respond to emotionally charged stories.
            - Need and Greed: {biograph_output['name']} identifies and manipulates the target’s desires and needs, promising to fulfill them through the scam.
            - Time Pressure: {biograph_output['name']} imposes a sense of urgency, making the target believe they must act quickly to avoid missing out on the opportunity, thereby reducing their ability to think critically.
    
             {biograph_output['name']} will of course never let other know his/her true intent or profession but apply these during conversations."""





    return biograph_output


# Generate externality description using OpenAI
def generate_externality_description(externality):
    client = OpenAI(api_key=openai_token)
    response = client.chat.completions.create(
        model=external_event_model,
        messages=[{'role': 'user', 'content': f"You are a creator of the Matrix, aka. God who plays dice, "
                                              f"you are introducing a world event of the following type in the year 2024, "
                                              f"it doesn't have to be anything wild but should be detailed. Please write "
                                              f"a 2 paragraphs summary of this event: {externality}"}]
    )
    return response.choices[0].message.content
def generate_conversation(persona1_bio, persona2_bio, channel_topic, externality_description, chat_history):
    """Generate a conversation between two personas"""
    return json.dumps({
        "persona1_bio": persona1_bio,
        "persona2_bio": persona2_bio,
        "channel_topic": channel_topic,
        "externality_description": externality_description,
        "chat_history": chat_history
    })


def simulate_conversation(persona1, persona2, channel_topic, externality_description):
    persona1_biography = generate_biography(persona1)
    persona2_biography = generate_biography(persona2)




    prompt = f"""
    Here is the context for the conversation to be generated. 

        Channel: {channel_topic['channel']} | Topic: {channel_topic['topic']} \n\n
        Contemporary Events: {externality_description} \n\n
        Person 1: {persona1_biography['name']}, {persona1_biography['biography']} \n\n
        Person 2: {persona2_biography['name']}, {persona2_biography['biography']}
        
    """

    client = OpenAI(api_key=openai_token)
    messages = [
            {
                "role": "user",
                "content": f"""Please provide realistic conversations between the two people. Please consider all of their background when generating these conversations. Please return the conversation 
                history as a list of json object with attribute name, timestamp, and chat message itself. Here are """ + prompt
                + """ If one of the person is a scammer, the scammer must follow the script exactly and not deviate. The scammer doesn't waste
                 time on people"""
            },
            {
                "role": "system",
                "content": f"""
                You are simulating a conversation between two people in a Discord channel. You will be given
                context about the channel, context about the world, and also biography for the two people having conversations. 
                """
            }
        ]

    response = client.chat.completions.create(
        model=model_type,
        messages=messages,
        max_tokens=4000
    )

    final_output = {
        'persona1_bio': persona1_biography,
        'persona2_bio': persona2_biography,
        'externalities': externality_description,
        'channel_topic': channel_topic,
        'chat_history': response.choices[0].message.content,
    }

    return final_output

def get_random_externality():
    externalities = [
        "Big gaming event",
        "New tech release",
        "Popular movie premiere",
        "Concert tour announcement",
        "Holiday season",
        "Major sporting event",
        "Political election",
        "Natural disaster",
        "Pandemic update",
        "Economic downturn",
        "Company-wide hackathon",
        "Major product launch",
        "Celebrity scandal",
        "Weather anomaly",
        "Government policy change",
        "Social media trend",
        "Stock market fluctuation",
        "Cultural festival",
        "Health crisis",
        "Scientific breakthrough",
        "Stock Market Crash",
        "Bullish Stock Market",
        "Nothing unusual",
        "International Peace Treaty Signed",
        "Major Cybersecurity Breach",
        "Historic Space Mission Launched",
        "Breakthrough in Renewable Energy Technology",
        "Global Environmental Summit",
        "Massive Infrastructure Project Completed",
        "New International Trade Agreement",
        "Historic Legal Ruling",
        "Large-Scale Protest Movement",
        "Significant Scientific Discovery in Medicine",
        "New Social Media Platform Emerges",
        "Discovery of a New Species",
        "Major Celebrity Wedding",
        "National Holiday Declared",
        "Significant Cultural Artifact Found",
        "Major Sports Team Wins Championship",
        "National Census Results Released",
        "Significant Policy Change on Immigration",
        "Discovery of a New Element",
        "Global Health Initiative Launched",
        "International Art Exhibition",
        "Major Financial Fraud Uncovered",
        "New Educational Reform Implemented",
        "Groundbreaking AI Development",
        "International Space Station Milestone",
        "Major Military Exercise",
        "Significant Natural Resource Discovery",
        "Historic Political Speech",
        "National Security Threat Neutralized",
        "Groundbreaking Climate Change Report",
        "New Major Museum Opens",
        "International Humanitarian Crisis",
        "Discovery of Ancient Civilization Ruins",
        "Breakthrough in Quantum Computing",
        "Significant Legislative Reform",
        "Large-Scale Cyber Attack Prevented",
        "Historic Peaceful Protest",
        "Major Oil Spill",
        "Discovery of a Cure for a Disease",
        "New Major Sports Event Announced",
        "Major Corporate Merger",
        "Breakthrough in Genetic Research",
        "Historic Monument Restoration Completed",
        "Significant Space Debris Removal",
        "National Referendum Held",
        "Major Wildlife Conservation Success",
        "Large-Scale Renewable Energy Project",
        "New National Park Established",
        "Historic Climate Accord Signed",
        "International Financial Summit",
        "Major Labor Strike",
        "Significant Advances in Robotics",
        "Discovery of a Major Oil Reserve",
        "Large-Scale Immigration Policy Change",
        "Breakthrough in Cancer Research",
        "Major Infrastructure Failure",
        "International Cybersecurity Agreement",
        "Significant Technological Patent Filed",
        "New National Currency Issued",
        "Discovery of a New Planet",
        "Major National Security Legislation",
        "Large-Scale Urban Renewal Project",
        "Historic Cultural Exchange Program",
        "Significant Advances in Nanotechnology",
        "Major Power Grid Failure",
        "New Historic Site Declared",
        "Large-Scale Drought Relief Effort",
        "Significant Global Tourism Increase",
        "Major Water Contamination Incident",
        "New National Health Initiative",
        "Historic Voting Rights Legislation",
        "Major International Athletic Event",
        "Significant Advances in Renewable Materials",
        "New National Education Standards",
        "Large-Scale Public Health Campaign",
        "Historic Archaeological Dig",
        "Significant Military Technology Development",
        "Major Software Company Launch",
        "New International Cultural Festival",
        "Large-Scale Clean Water Project",
        "Major Space Tourism Milestone",
        "Historic National Reconciliation Event",
        "Significant Global Trade Dispute",
        "New Major Public Transportation System",
        "Major Food Safety Scandal",
        "Breakthrough in Biodegradable Plastics",
        "Large-Scale Homelessness Initiative",
        "Significant Human Rights Legislation",
        "Major International Sports Victory",
        "Historic Religious Gathering",
        "Significant Advances in Sustainable Agriculture",
        "New National Defense Strategy",
        "Major Breakthrough in Fusion Energy",
        "Large-Scale Waste Management Project",
        "Significant Advances in Space Mining",
        "New International Language Learning Program",
        "Historic Judicial Reform",
        "Major Global Health Awareness Campaign",
        "Large-Scale Environmental Cleanup Effort",
        "New Major Space Exploration Program Announced"
    ]
    return random.choice(externalities)

# Function to simulate multiple conversations
def simulate_discord_conversations(num_conversations=5):
    is_scammer = True
    for _ in range(num_conversations):
        persona1 = generate_persona()
        persona2 = generate_persona(scammer=is_scammer)
        channel_topic = get_random_channel_topic()
        externality = get_random_externality()
        externality_description = generate_externality_description(externality)

        try:
            conversation = simulate_conversation(persona1, persona2, channel_topic, externality_description)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"""generated_conversations/{'strict_scripted_scammer' if is_scammer else ''}conversation_{timestamp}_{_}.json"""
            print(filename)
            with open(filename, 'w') as f:
                json.dump(conversation, f, indent=4)

        except:
            print('errored out')




# Simulate 5 conversations
simulate_discord_conversations(num_conversations=100)
