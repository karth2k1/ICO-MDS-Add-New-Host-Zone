"""
LLM Client for Cisco Chat AI (GPT-4.1).

Handles OAuth token retrieval and chat completions.
"""

import os
import json
import time
from typing import Any, Dict, List, Optional
import requests


class CiscoLLMClient:
    """
    Client for Cisco's Chat AI service using GPT-4.1.
    
    Handles OAuth2 token management and chat completions.
    """
    
    # Default URLs
    DEFAULT_OAUTH_URL = "https://id.cisco.com/oauth2/default/v1/token"
    DEFAULT_CHAT_URL = "https://chat-ai.cisco.com/openai/deployments/gpt-4.1/chat/completions"
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        appkey: str = None,
        username: str = None,
        oauth_url: str = None,
        chat_url: str = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            client_id: OAuth client ID (or set CISCO_CLIENT_ID env var)
            client_secret: OAuth client secret (or set CISCO_CLIENT_SECRET env var)
            appkey: Cisco Chat AI appkey (or set CISCO_APPKEY env var)
            username: Cisco username (or set CISCO_USERNAME env var)
            oauth_url: OAuth token URL (optional, uses default)
            chat_url: Chat completions URL (optional, uses default)
        """
        self.client_id = client_id or os.environ.get("CISCO_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("CISCO_CLIENT_SECRET")
        self.appkey = appkey or os.environ.get("CISCO_APPKEY")
        self.username = username or os.environ.get("CISCO_USERNAME", "ico-workflow-generator")
        self.oauth_url = oauth_url or os.environ.get("CISCO_OAUTH_URL", self.DEFAULT_OAUTH_URL)
        self.chat_url = chat_url or os.environ.get("CISCO_CHAT_AI_URL", self.DEFAULT_CHAT_URL)
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # Validate credentials are available
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Cisco OAuth credentials not found. "
                "Set CISCO_CLIENT_ID and CISCO_CLIENT_SECRET environment variables, "
                "or pass client_id and client_secret to the constructor."
            )
        
        if not self.appkey:
            raise ValueError(
                "Cisco Chat AI appkey not found. "
                "Set CISCO_APPKEY environment variable."
            )
    
    def _get_access_token(self) -> str:
        """
        Get a valid OAuth access token, refreshing if necessary.
        
        Returns:
            Valid access token string
        """
        # Check if we have a valid cached token (with 60s buffer)
        if self._access_token and time.time() < (self._token_expires_at - 60):
            return self._access_token
        
        # Request new token
        try:
            response = requests.post(
                self.oauth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            # Calculate expiration time (default to 1 hour if not provided)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = time.time() + expires_in
            
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to obtain OAuth token: {e}") from e
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to GPT-4.1.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification (e.g., {"type": "json_object"})
            
        Returns:
            API response as dictionary
        """
        token = self._get_access_token()
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Cisco Chat AI expects user as a JSON-encoded string.
            "user": json.dumps({"appkey": self.appkey}),
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = requests.post(
                self.chat_url,
                json=payload,
                headers={
                    "api-key": token,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=120  # LLM calls can take time
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Chat completion request failed: {e}") from e
    
    def get_completion_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> str:
        """
        Get just the text content from a chat completion.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            The assistant's response text
        """
        response = self.chat_completion(messages, temperature, max_tokens)
        return response["choices"][0]["message"]["content"]
    
    def get_json_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Get a JSON response from the LLM.
        
        Args:
            messages: List of message dicts (should instruct JSON output)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Parsed JSON response
        """
        response = self.chat_completion(
            messages,
            temperature,
            max_tokens,
            response_format={"type": "json_object"}
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)


# Singleton instance (lazy initialization)
_llm_client: Optional[CiscoLLMClient] = None


def get_llm_client() -> CiscoLLMClient:
    """Get or create the singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = CiscoLLMClient()
    return _llm_client
