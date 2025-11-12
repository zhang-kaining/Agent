from pydantic import BaseModel
from abc import ABC, abstractmethod


class LLMBaseModel(BaseModel, ABC):

    @abstractmethod
    def invoke(
        self,
        model: str,
        contents: list[str]
    ) -> str:
        """
        Invoke the LLM model with the given contents.
        """
        pass
        