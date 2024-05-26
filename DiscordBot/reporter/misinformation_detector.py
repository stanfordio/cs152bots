from llm_engine import LLMEngine
from typing import Dict


class ValidatorResponseObject:
    def __init__(self, is_valid: bool, reason: str, metadata: Dict = dict()):
        self.is_valid = is_valid
        self.reason = reason
        self.metadata = metadata


class LLMValidator(LLMEngine):
    def __init__(self, system_prompt: str):
        super().__init__(system_prompt=system_prompt)
        self.prompt: str = str()

    def validate(self, response: str, **kwargs) -> bool:
        return True

    def __call__(self, message: str, **kwargs) -> ValidatorResponseObject:
        prompt_formatted = self.prompt.format(message=message)
        response = self.generate_response(prompt=prompt_formatted)
        is_valid = self.validate(response=response, **kwargs)
        return ValidatorResponseObject(is_valid=is_valid, reason=response)


class MisinformationDetector(LLMValidator):
    def __init__(self):
        super().__init__(
            system_prompt="You are a helpful assistant that detects misinformation"
        )

        self.prompt = """### Contents
{message}

### Instructions: Your job is to determine whether the provided contents consist of misleading or false information from a government group
* If the contents are misleading or false, reply with "YES"
* If the contents are not misleading or false, reply with "NO"
* You can only reply with "YES" or "NO" as the first word
* After the first word (which must be "YES" or "NO"), provide a thorough explanation of why you made the decision

### Examples

Contents:
The government has announced a new policy aimed at reducing carbon emissions by 50% over the next decade. The policy includes measures such as increasing the use of renewable energy sources, implementing stricter regulations on industrial emissions, and providing incentives for businesses to adopt greener practices. Officials believe that these steps will significantly contribute to the fight against climate change and promote sustainable development.

Reponse:
NO, this is not misleading or false information from a government group because it is a statement of a government policy in the form of a news report with no inherent bias

____
Contents:
The government has announced that the new vaccine will make you immune to all diseases and will extend your lifespan by 50 years. This vaccine is mandatory for all citizens, and failure to comply will result in severe penalties. The government assures that there are no side effects and that it has been thoroughly tested.

Response:
YES, this is misleading or false information from a government group because it makes exaggerated claims about the vaccine's effectiveness and safety without scientific evidence.

____

Contents:
The government has announced a new initiative to improve public transportation infrastructure. The initiative includes plans to upgrade existing transit systems, introduce new routes, and invest in sustainable transportation options. Officials claim that these improvements will reduce traffic congestion and promote environmental sustainability.

Response:
NO, this is not misleading or false information from a government group because it outlines a government initiative with plausible benefits and no exaggerated claims.

____

### Now it is your turn. Follow the Instructions and determine whether the contents are misleading or false information from a government group or not. 

Contents:
{message}

Your Response:"""

    def validate(self, response: str, **kwargs) -> bool:
        return response[:3] == "YES"
