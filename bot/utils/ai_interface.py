import os
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai


class AIInterface:
    def __init__(self, retry_attempts: int = 2, retry_delay: float = 1.0):
        """
        Initialize AI Interface with Gemini API
        
        Args:
            retry_attempts: number of retry attempts
            retry_delay: delay between retries in seconds
        """
        load_dotenv()
        
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Initialize Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_client = genai
        else:
            self.gemini_client = None
            
        # Validate that Gemini is available
        if not self.gemini_client:
            raise ValueError("GEMINI_API_KEY not found. Please set GEMINI_API_KEY environment variable.")

    def _try_gemini(self, prompt: str) -> Optional[str]:
        """Try to generate text using Gemini API"""
        if not self.gemini_client:
            return None
            
        try:
            model = self.gemini_client.GenerativeModel('gemini-2.5-flash-lite')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
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
        if not self.gemini_client:
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
            "gemini_available": self.gemini_client is not None,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay
        }
