from google import genai
from dotenv import load_dotenv
from .base import LLMBaseModel
load_dotenv()


class Gemini(LLMBaseModel):

    def __init__(self):
        self.client = genai.Client()

    def invoke(
        self,
        model,
        contents
    ):
        response = self.client.models.generate_content(
            model=model,
            contents=contents
        )
        return response.text
