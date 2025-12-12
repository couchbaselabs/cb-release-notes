from AI_Clients import OpenAIClient, GeminiClient, AIClient

ai_factory = {
    'openai': OpenAIClient,
    'gemini': GeminiClient
}

def ai_client_factory(ai_key: str, ai_service: str, ai_model: str, ai_prompt: str) -> AIClient | None:


    ai_client = ai_factory[ai_service](ai_key, ai_model, ai_prompt)
    return ai_client
