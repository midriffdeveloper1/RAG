from abc import ABC, abstractmethod
from typing import Any


class RealtimeVoiceProvider(ABC):
    

    @abstractmethod
    def create_ephemeral_token(self, ttl_seconds: int = 60) -> dict[str, Any]:
       
        raise NotImplementedError

    @abstractmethod
    def stt_stream_config(self) -> dict[str, Any]:
       
        raise NotImplementedError

    @abstractmethod
    def tts_stream_config(self, voice_name: str) -> dict[str, Any]:
        raise NotImplementedError