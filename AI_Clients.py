from abc import ABC, abstractmethod

from openai import OpenAI


class AbstractAIClient(ABC):
    ai_client = None
    ai_model = None
    ai_prompt = None

    def __init__(self, ai_client,  ai_model=None, ai_prompt=None):
        self.ai_client = ai_client
        self.ai_model = ai_model
        self.ai_prompt = ai_prompt
        super().__init__()

    @abstractmethod
    def get_ai_response(self, text):
        pass



class OpenAIClient(AbstractAIClient):

    def get_ai_response(self, text):
        return self.ai_client.responses.create(
            model=self.ai_model,
            instructions=self.ai_prompt,
            input=f"{text}")


def ai_client_factory(ai_key, ai_service):

    ai_client = None

    if ai_service['name'] == 'chatgpt':
      ai_concrete_client = OpenAI(api_key=ai_key)
      ai_client = OpenAIClient(ai_concrete_client,
                               ai_model=ai_service['model'],
                               ai_prompt=ai_service['prompt'])
    return ai_client
