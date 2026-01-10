import os
import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
import google.genai as genai


class AIInterface:
    def __init__(self, retry_attempts: int = 2, retry_delay: float = 1.0, models_file: str = "models.json"):
        """
        Initialize AI Interface with Gemini API
        
        Args:
            retry_attempts: number of retry attempts
            retry_delay: delay between retries in seconds
            models_file: path to JSON file with available models
        """
        load_dotenv()
        
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Initialize Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set GEMINI_API_KEY environment variable.")
        
        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        
        # Load available models from JSON file
        self.models = self._load_models(models_file)
        if not self.models:
            # Fallback to default model if no models file found
            self.models = ['gemini-2.0-flash-exp']
        
        self.current_model_index = 0
        self.model_name = self.models[self.current_model_index]

    def _load_models(self, models_file: str) -> List[str]:
        """Load available models from JSON file"""
        try:
            # Try to find models.json in the project root
            project_root = Path(__file__).parent.parent.parent
            models_path = project_root / models_file
            
            if not models_path.exists():
                # Try current directory
                models_path = Path(models_file)
            
            if models_path.exists():
                with open(models_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    models = data.get('models', [])
                    if models:
                        print(f"Loaded {len(models)} models from {models_path}")
                        return models
            
            print(f"Models file {models_file} not found, using default model")
            return []
        except Exception as e:
            print(f"Error loading models file: {e}")
            return []
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit/quota exceeded error"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check for common rate limit indicators
        rate_limit_indicators = [
            'rate limit',
            'quota exceeded',
            'resource exhausted',
            '429',
            'too many requests',
            'quota',
            'limit exceeded',
            'permission denied',
            'quota_exceeded',
            'resource_exhausted'
        ]
        
        return any(indicator in error_str or indicator in error_type for indicator in rate_limit_indicators)
    
    def _switch_to_next_model(self):
        """Switch to the next available model"""
        if len(self.models) <= 1:
            return False
        
        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        self.model_name = self.models[self.current_model_index]
        print(f"Switched to model: {self.model_name}")
        return True
    
    def _try_gemini(self, prompt: str, switch_on_rate_limit: bool = True) -> Optional[str]:
        """Try to generate text using Gemini API"""
        try:
            # Используем GenerativeModel для генерации контента
            model = genai.GenerativeModel(self.model_name, client=self.gemini_client)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"Gemini API error with model {self.model_name}: {error_msg}")
            
            # If it's a rate limit error and we have other models, switch
            if switch_on_rate_limit and self._is_rate_limit_error(e):
                if self._switch_to_next_model():
                    # Retry with new model
                    print(f"Retrying with model: {self.model_name}")
                    try:
                        model = genai.GenerativeModel(self.model_name, client=self.gemini_client)
                        response = model.generate_content(prompt)
                        return response.text
                    except Exception as retry_error:
                        print(f"Retry with {self.model_name} also failed: {retry_error}")
            
            return None

    def generate_text(self, prompt: str) -> str:
        """
        Generate text using Gemini API with retries
        
        Args:
            prompt: The text prompt to send to the AI
            
        Returns:
            Generated text from Gemini API
            
        Raises:
            RuntimeError: If Gemini API fails after all retry attempts
        """
        if not self.gemini_api_key:
            raise RuntimeError("Gemini API is not available. Please set GEMINI_API_KEY environment variable.")
        
        # Try with retries
        for attempt in range(self.retry_attempts):
            print(f"Trying Gemini (attempt {attempt + 1}/{self.retry_attempts})")
            
            result = self._try_gemini(prompt)
            if result is not None:
                print(f"Successfully generated text using Gemini")
                return result
            
            if attempt < self.retry_attempts - 1:  # Don't sleep after last attempt
                time.sleep(self.retry_delay)
        
        # If we get here, all attempts failed
        raise RuntimeError(f"Gemini API failed after {self.retry_attempts} attempts.")

    def get_status(self) -> Dict[str, Any]:
        """Get the status of available providers"""
        return {
            "gemini_available": self.gemini_api_key is not None,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "current_model": self.model_name,
            "available_models": self.models,
            "current_model_index": self.current_model_index
        }
