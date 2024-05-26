from .llm_engine import LLMEngine


class MisinformationDetector(LLMEngine):
    def __init__(self):
        super().__init__(
            system_prompt="You are a helpful assistant that detects misinformation"
        )

    def detect_misinformation(self, message: str):
        return self.generate_response(
            prompt="Detect if the following message is misinformation or not: "
            + message
        )
