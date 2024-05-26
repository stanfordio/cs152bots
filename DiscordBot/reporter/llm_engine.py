import litellm
import os


class LanguageModel:
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        system_prompt: str = "You are a helpful assistant",
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.system_prompt_formatted = [
            {"content": self.system_prompt, "role": "system"}
        ]
        self.message_history = self.system_prompt_formatted
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

    def generate_response(
        self, prompt: str, maintain_message_history: bool = True, **kwargs
    ):
        # Add the user's prompt to the message history
        if maintain_message_history:
            self.message_history = [
                *self.message_history,
                {"content": f"{prompt}", "role": "user"},
            ]
        # Generate a response
        response = litellm.completion(
            model=self.model_name,
            messages=self.message_history,
        )
        # Add the response to the message history
        if maintain_message_history:
            self.message_history = [
                *self.message_history,
                {"content": response.choices[0].message.content, "role": "system"},
            ]

        return response.choices[0].message.content


class LLMEngine:
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        system_prompt: str = "You are a helpful assistant",
    ):

        self.model_name = model_name
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.model = LanguageModel(model_name, temperature, system_prompt)

    def generate_response(
        self, prompt: str, maintain_message_history: bool = True, **kwargs
    ):
        return self.model.generate_response(prompt, maintain_message_history, **kwargs)
