"""
Docstring for src.tools.llm
"""
import os
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
# Import the required safety types
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from src.utils.config import cfg

def get_llm(profile: str = "default") -> BaseChatModel:
    """
    Factory to get an LLM instance based on configuration profiles.
    """
    provider = cfg.get("llm.provider") 
    
    if not provider:
        raise ValueError("LLM provider not configured")

    profile_path = f"llm.{profile}"
    
    # Fetch specific settings for this profile, falling back to default if missing
    model_name = cfg.get(f"{profile_path}.model", cfg.get("llm.default.model"))
    temperature = cfg.get(f"{profile_path}.temperature", cfg.get("llm.default.temperature"))
    max_tokens = cfg.get(f"{profile_path}.max_tokens", cfg.get("llm.default.max_tokens"))
    
    if provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=cfg.get(f"llm.{profile}.top_p", 0.95),
            top_k=cfg.get(f"llm.{profile}.top_k", 64),
            # Updated to use Enum objects to satisfy Pydantic validation
            safety_settings={
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
        )
        
    elif provider == "openai":
        # Ensure ChatOpenAI is imported if used
        from langchain_openai import ChatOpenAI 
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
    elif provider == "anthropic":
        # Ensure ChatAnthropic is imported if used
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")