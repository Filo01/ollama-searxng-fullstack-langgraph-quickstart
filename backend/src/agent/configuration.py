import os
from pydantic import BaseModel, Field
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """The configuration for the agent."""

    query_generator_model: str = Field(
        default="gemma3:4b",
        metadata={
            "description": "The name of the language model to use for the agent's query generation. (Ollama model)"
        },
    )

    reflection_model: str = Field(
        default="gemma3:14b",
        metadata={
            "description": "The name of the language model to use for the agent's reflection. (Ollama model)"
        },
    )

    answer_model: str = Field(
        default="gemma3:27b",
        metadata={
            "description": "The name of the language model to use for the agent's answer. (Ollama model)"
        },
    )

    searxng_url: str = Field(
        default="http://localhost:8080/search",
        metadata={
            "description": "The URL of the SearxNG instance to use for web search."
        },
    )

    number_of_initial_queries: int = Field(
        default=3,
        metadata={"description": "The number of initial search queries to generate."},
    )

    max_research_loops: int = Field(
        default=2,
        metadata={"description": "The maximum number of research loops to perform."},
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {
            name: os.environ.get(name.upper(), configurable.get(name))
            for name in cls.model_fields.keys()
        }

        # Filter out None values
        values = {k: v for k, v in raw_values.items() if v is not None}

        return cls(**values)
