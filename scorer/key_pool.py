import os
import time
import threading
from dataclasses import dataclass
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

@dataclass
class Key:
    """
    Represents an API key with its current state and usage metrics.
    """
    provider: str
    api_key: str
    requests_this_minute: int = 0
    requests_today: int = 0
    last_reset_minute: float = 0.0
    last_reset_day: float = 0.0
    is_locked: bool = False
    locked_until: float = 0.0
    total_requests: int = 0
    total_errors: int = 0

class KeyPool:
    """
    Manages a pool of API keys across different providers with rate limiting and rotation.
    """
    
    RATE_LIMITS = {
        "gemini": {"min": 15, "day": 1500},
        "groq": {"min": 30, "day": 14400},
        "openrouter": {"min": 20, "day": 200}
    }

    def __init__(self):
        self.keys: List[Key] = []
        self.lock = threading.Lock()
        self._load_keys()
        
        if not self.keys:
            expected_vars = [
                "GEMINI_API_KEY_1..3",
                "GROQ_API_KEY_1..3",
                "OPENROUTER_API_KEY_1..2"
            ]
            raise RuntimeError(
                f"No API keys found in .env file. Please provide at least one of: {', '.join(expected_vars)}"
            )
            
        self._print_init_status()

    def _load_keys(self):
        """Loads keys from environment variables."""
        providers = {
            "gemini": ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"],
            "groq": ["GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3"],
            "openrouter": ["OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY_2"]
        }
        
        # Also check for single GEMINI_API_KEY as it's common
        if "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"]:
             if not any(k.api_key == os.environ["GEMINI_API_KEY"] for k in self.keys):
                self.keys.append(Key(provider="gemini", api_key=os.environ["GEMINI_API_KEY"]))

        for provider, env_vars in providers.items():
            for var in env_vars:
                key_val = os.getenv(var)
                if key_val and not any(k.api_key == key_val for k in self.keys):
                    self.keys.append(Key(provider=provider, api_key=key_val))

    def _print_init_status(self):
        counts = {"gemini": 0, "groq": 0, "openrouter": 0}
        for k in self.keys:
            counts[k.provider] += 1
        print(f"Key pool loaded: {counts['gemini']} Gemini, {counts['groq']} Groq, {counts['openrouter']} OpenRouter keys")

    def _reset_if_needed(self, key: Key):
        """Resets rate limit counters based on elapsed time."""
        now = time.time()
        
        # Reset minute counter
        if now - key.last_reset_minute > 60:
            key.requests_this_minute = 0
            key.last_reset_minute = now
            
        # Reset day counter
        if now - key.last_reset_day > 86400:
            key.requests_today = 0
            key.last_reset_day = now
            
        # Release lock if expired
        if key.is_locked and now > key.locked_until:
            key.is_locked = False

    def get_available_key(self) -> Optional[Key]:
        """Returns the least busy available key from the pool."""
        with self.lock:
            available_keys = []
            for key in self.keys:
                self._reset_if_needed(key)
                
                limits = self.RATE_LIMITS.get(key.provider)
                if not limits:
                    continue
                
                if (not key.is_locked and 
                    key.requests_this_minute < limits["min"] and 
                    key.requests_today < limits["day"]):
                    available_keys.append(key)
            
            if not available_keys:
                return None
            
            # Sort by requests_this_minute ascending to rotate keys
            available_keys.sort(key=lambda x: x.requests_this_minute)
            return available_keys[0]

    def mark_used(self, key: Key):
        """Updates usage statistics for a key."""
        with self.lock:
            key.requests_this_minute += 1
            key.requests_today += 1
            key.total_requests += 1

    def mark_error(self, key: Key, is_rate_limit: bool = False):
        """Logs an error and optionally locks the key on rate limit."""
        with self.lock:
            key.total_errors += 1
            if is_rate_limit:
                key.is_locked = True
                key.locked_until = time.time() + 65
                print(f"⚠️ [KeyPool] {key.provider.upper()} key rate limited. Locked for 65s.")

    def wait_for_key(self, timeout: int = 120) -> Optional[Key]:
        """Polls for an available key until found or timeout."""
        start_time = time.time()
        waiting_printed = False
        
        while time.time() - start_time < timeout:
            key = self.get_available_key()
            if key:
                return key
            
            elapsed = time.time() - start_time
            if elapsed > 4 and not waiting_printed:
                print("⏳ Waiting for available API key (all keys rate limited)...")
                waiting_printed = True
                
            time.sleep(2)
            
        return None

    def status(self) -> Dict[str, Dict]:
        """Returns a summary of the pool's current status."""
        summary = {}
        with self.lock:
            for k in self.keys:
                if k.provider not in summary:
                    summary[k.provider] = {"available": 0, "locked": 0, "requests_today": 0}
                
                self._reset_if_needed(k)
                limits = self.RATE_LIMITS[k.provider]
                
                is_available = (not k.is_locked and 
                               k.requests_this_minute < limits["min"] and 
                               k.requests_today < limits["day"])
                
                if is_available:
                    summary[k.provider]["available"] += 1
                else:
                    summary[k.provider]["locked"] += 1
                    
                summary[k.provider]["requests_today"] += k.requests_today
                
        return summary

# Singleton instance
key_pool = None
try:
    key_pool = KeyPool()
except RuntimeError as e:
    # This might happen during initial setup if .env is not ready
    # We allow the module to be imported but the user will see the error when using it
    pass
