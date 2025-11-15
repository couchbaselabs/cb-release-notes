from openai import OpenAI
from google import genai

from abc import ABC, abstractmethod

class AIClient(ABC):

    def __init__(self, ai_model=None, ai_prompt=None):
        self.ai_model = ai_model
        self.ai_prompt = ai_prompt
        self.ai_client = None
        super().__init__()

    @abstractmethod
    def get_ai_response(self, text) -> str:
        pass

class GeminiClient(AIClient):

    def __init__(self, ai_key, ai_model=None, ai_prompt=None):
        super().__init__(ai_model, ai_prompt)
        self.ai_client = genai.Client(api_key=ai_key)

    def get_ai_response(self, text) -> str | None:

        prompt = f"{self.ai_prompt}: {text}"

        response = self.ai_client.models.generate_content(model=self.ai_model, contents=prompt)

        return response.text

class OpenAIClient(AIClient):

    def __init__(self, ai_key, ai_model=None, ai_prompt=None):
        super().__init__(ai_model, ai_prompt)
        self.ai_client = OpenAI(api_key=ai_key)

    def get_ai_response(self, text) -> str | None:
        response =  self.ai_client.responses.create(
            model=self.ai_model,
            instructions=self.ai_prompt,
            input=f"{text}")

        return response.output_text

def ai_client_factory(ai_key: str, ai_service: str, ai_model: str, ai_prompt: str) -> AIClient | None:

    ai_factory =  {
        'chatgpt': OpenAIClient,
        'gemini': GeminiClient
    }

    ai_client = ai_factory[ai_service](ai_key, ai_model, ai_prompt)
    return ai_client
