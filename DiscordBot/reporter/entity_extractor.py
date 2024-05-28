from llm_engine import LLMEngine
import json


class EntityExtractorOutputObject:

    def __init__(self, posting_entity: str, posting_entity_name: str):
        self.posting_entity = posting_entity
        self.posting_entity_name = posting_entity_name

    def __dict__(self):
        return {
            "data": {
                "posting_entity": self.posting_entity,
                "posting_entity_name": self.posting_entity_name,
            }
        }


class EntityExtractor(LLMEngine):
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        system_prompt: str = "You are a helpful assistant",
        json_mode: bool = True,
    ):
        super().__init__(model_name, temperature, system_prompt, json_mode)

        self.prompt = """### Contents
{contents}

### Message Author
{message_author}

### Output Format
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}

        
### Instructions: Your job is to determine whether the Message Contents were posted by one of the following entities. 
1. Government Official
2. Government Agency
3. Government State-Controlled Media
4. Ex-Government Official
5. Not Government Entity
* You should leverage the Message Author and Contents to determine the entity and entity name.
* The posting entity should be explicitly named in the Contents or in the Message Author
* If the posting entity is not from the above list, then fill the field titled "posting_entity" with "Not Government Entity" and fill the field titled "posting_entity_name" with the name of the user.
* Fill the type of the posting entity in the field titled "posting_entity"
* Fill the name of the posting entity in the field titled "posting_entity_name"

### Examples: 
Contents:
The President of the United States tweeted: "Announcing a new initiative to provide free healthcare to all citizens. This will cover all medical expenses, including surgeries and medications, without increasing taxes. #HealthcareForAll"

Message Author:
POTUS

### Output Format:
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}


Response:
{{
    "posting_entity": "Government Official",
    "posting_entity_name": "President of the United States"
}}
____
Contents:
A former senator tweeted: "The new tax reform will only benefit the wealthy and increase the financial burden on the middle class. Protest against this reform! #TaxReform"

Message Author:
FormerSenator123

### Output Format:
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}


Response:
{{
    "posting_entity": "Ex-Government Official",
    "posting_entity_name": "Former Senator"
}}
____
Contents:
The Ministry of Health tweeted: "Warning about a new strain of flu spreading rapidly. Get vaccinated and take necessary precautions to avoid infection. #HealthAlert"

Message Author:
HealthMinistry

### Output Format:
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}


Response:
{{
    "posting_entity": "Government Agency",
    "posting_entity_name": "Ministry of Health"
}}
____
Contents:
A state-controlled news outlet tweeted: "The recent economic downturn is due to foreign interference, not domestic policies. Remain calm and trust the government's actions. #EconomicUpdate"

Message Author:
StateNewsOutlet

### Output Format:
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}


Response:
{{
    "posting_entity": "Government State-Controlled Media",
    "posting_entity_name": "State-Controlled News Outlet"
}}
____
Contents:
A user named JohnDoe123 tweeted: "The new environmental regulations are a scam and will not benefit the public. No evidence provided. #EnvironmentScam"

Message Author:
JohnDoe123

### Output Format:
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}


Response:
{{
    "posting_entity": "Not Government Entity",
    "posting_entity_name": "JohnDoe123"
}}

### Now it is your turn. Following the instructions above, extract the entity and entity name from the message content based on the following Output Format:

Contents:
{contents}

Message Author: 
{message_author}

Output Format: 
{{
    "posting_entity": "Government Official/Government Agency/Government State-Controlled Media/Ex-Government Official/Not Government Entity",
    "posting_entity_name": "Name of the entity that posted the message",
}}

Your Response:```json"""

    def extract_persona(
        self, user_name: str, message_content: str, message_author: str
    ) -> EntityExtractorOutputObject:
        prompt_formatted = self.prompt.format(
            contents=message_content, message_author=message_author
        )

        response = self.generate_response(prompt_formatted)
        response_as_json = json.loads(response)

        return EntityExtractorOutputObject(
            posting_entity=response_as_json["posting_entity"],
            posting_entity_name=response_as_json["posting_entity_name"],
        )

        # INSERT_YOUR_CODE


def test_extract_persona():
    extractor = EntityExtractor()
    user_name = "JohnDoe123"
    message_content = "The new environmental regulations are a scam and will not benefit the public. No evidence provided. #EnvironmentScam"
    message_author = "JohnDoe123"

    expected_output = EntityExtractorOutputObject(
        posting_entity="Not Government Entity", posting_entity_name="JohnDoe123"
    )

    result = extractor.extract_persona(user_name, message_content, message_author)

    assert (
        result.posting_entity == expected_output.posting_entity
    ), f"Expected {expected_output.posting_entity}, but got {result.posting_entity}"
    assert (
        result.posting_entity_name == expected_output.posting_entity_name
    ), f"Expected {expected_output.posting_entity_name}, but got {result.posting_entity_name}"


test_extract_persona()
