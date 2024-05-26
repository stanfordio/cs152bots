from llm_engine import LLMEngine
from typing import Dict, Any
import json


class ValidatorResponseObject:
    def __init__(self, flagged: bool, payload: Any, metadata: Dict = dict()):
        self.flagged = flagged
        self.payload = payload
        self.metadata = metadata


class LLMValidator(LLMEngine):
    def __init__(self, system_prompt: str, **kwargs):
        super().__init__(system_prompt=system_prompt, **kwargs)
        self.prompt: str = str()

    def validate(self, payload: Any, **kwargs) -> bool:
        return True

    def __call__(self, message: str, **kwargs) -> ValidatorResponseObject:
        prompt_formatted = self.prompt.format(message=message)
        payload = self.generate_response(prompt=prompt_formatted)
        if self.json_mode:
            payload = json.loads(payload)
        flagged = self.validate(payload=payload, **kwargs)
        return ValidatorResponseObject(flagged=flagged, payload=payload)


class MisinformationDetector(LLMValidator):
    def __init__(self):
        super().__init__(
            system_prompt="You are a helpful assistant that detects misinformation",
            json_mode=True,
        )

        self.prompt = """### Output Format
{{
    "flagged": "YES/NO",
    "misinformation_type": "misinformation_type",
    "reason": "Explanation"
}}

Contents
{message}

### Instructions: Your job is to determine whether the provided contents consist of misleading or false information from a government group, and what type of content it contains
* If the contents are misleading or false, fill in the "flagged" field with "YES"
* If the contents are not misleading or false, fill in the "flagged" field with "NO"
* You can only reply "YES" or "NO" for the "flagged" field
* The misinformation type must be one of the following:
  - Dis/Misinformation
  - Inciting Harassment
  - Hate Speech
  - Swaying others opinion
  - Other, (and elaborate)
* If you classify it as misinformation for another reason, fill in the "misinformation_type" field with a 2-word descriptor

### Examples

Contents:
The government has announced a new policy aimed at reducing carbon emissions by 50 percent over the next decade. The policy includes measures such as increasing the use of renewable energy sources, implementing stricter regulations on industrial emissions, and providing incentives for businesses to adopt greener practices. Officials believe that these steps will significantly contribute to the fight against climate change and promote sustainable development.

Reponse:
{{
    "flagged": "NO",
    "misinformation_type": "None",
    "reason": "This is not misleading or false information from a government group because it is a statement of a government policy in the form of a news report with no inherent bias."
}}
____
Contents:
The government has announced that the new vaccine will make you immune to all diseases and will extend your lifespan by 50 years. This vaccine is mandatory for all citizens, and failure to comply will result in severe penalties. The government assures that there are no side effects and that it has been thoroughly tested.

Response:
{{
    "flagged": "YES",
    "misinformation_type": "Dis/Misinformation",
    "reason": "This is misleading or false information from a government group because it makes exaggerated claims about the vaccine's effectiveness and safety without scientific evidence."
}}
____

Contents:
The government has announced a new initiative to improve public transportation infrastructure. The initiative includes plans to upgrade existing transit systems, introduce new routes, and invest in sustainable transportation options. Officials claim that these improvements will reduce traffic congestion and promote environmental sustainability.

Response:
{{
    "flagged": "NO",
    "misinformation_type": "None",
    "reason": "This is not misleading or false information from a government group because it outlines a government initiative with plausible benefits and no exaggerated claims."
}}
____

### Now it is your turn. Follow the Instructions and determine whether the contents are misleading or false information from a government group or not. 

Output Format: 
{{
    "flagged": "YES/NO",
    "misinformation_type": "misinformation_type",
    "reason": "Explanation"
}}


Contents:
{message}

Your Response:```json"""

    def validate(self, payload: str, **kwargs) -> bool:
        return payload["flagged"] == "YES"


misinformation_detector = MisinformationDetector()

print(
    misinformation_detector(
        "The government has announced a new policy aimed at reducing carbon emissions by 50% over the next decade. The policy includes measures such as increasing the use of renewable energy sources, implementing stricter regulations on industrial emissions, and providing incentives for businesses to adopt greener practices. Officials believe that these steps will significantly contribute to the fight against climate change and promote sustainable development."
    ).flagged
)
