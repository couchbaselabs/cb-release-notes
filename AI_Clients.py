from openai import OpenAI
from google import genai
from abc import ABC, abstractmethod


class AIClient(ABC):

    def __init__(self, ai_client, ai_model=None, ai_prompt=None):
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_prompt = ai_prompt
        super().__init__()

    @abstractmethod
    def get_ai_response(self, text):
        pass

class GeminiClient(AIClient):

    def get_ai_response(self, text):

        prompt = f"{self.ai_prompt}: {text}"

        response = self.ai_client.models.generate_content(
            model=self.ai_model,
            contents=prompt)

        return response.text

class OpenAIClient(AIClient):

    def get_ai_response(self, text):
        response =  self.ai_client.responses.create(
            model=self.ai_model,
            instructions=self.ai_prompt,
            input=f"{text}")

        return response.output_text

def ai_client_factory(ai_key: str, ai_service: dict) -> AIClient:
    ai_client = None

    if ai_service['name'] == 'chatgpt':
        ai_concrete_client = OpenAI(api_key=ai_key)
        ai_client = OpenAIClient(ai_concrete_client,
                             ai_model=ai_service['model'],
                             ai_prompt=ai_service['prompt'])

    if ai_service['name'] == 'gemini':
        ai_concrete_client = genai.Client(api_key=ai_key)
        ai_client = GeminiClient(ai_concrete_client,
                             ai_model=ai_service['model'],
                             ai_prompt=ai_service['prompt'])
    return ai_client
