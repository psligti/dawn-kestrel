"""OpenCode Python - Streaming Response Handler"""
from __future__ import annotations
from typing import AsyncGenerator, Optional, Callable
import logging

from . import BaseProvider, UsageInfo


logger = logging.getLogger(__name__)


class StreamChunkHandler:
    """Handles streaming response chunks with buffering and conversion"""

    def __init__(
        self,
        provider: "BaseProvider",
        format_converter: Optional[Callable[[str], str]] = None,
        binary_decoder: Optional[Callable[[bytes], Optional[bytes]]] = None
    ):
        self.provider = provider
        self.format_converter = format_converter
        self.binary_decoder = binary_decoder
        self.buffer = ""
        self.separator = provider.get_stream_separator()
        self._accumulated_usage: Optional["UsageInfo"] = None

    async def process_stream(
        self,
        response_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        """
        Process streaming response, yielding converted chunks
        """
        decoder = "utf-8"

        async for raw_value in response_stream:
            # Apply binary decoder if available (e.g., AWS Bedrock)
            value = self.binary_decoder(raw_value) if self.binary_decoder else raw_value
            if not value:
                continue

            # Decode and add to buffer
            text = value.decode(decoder, errors='ignore')
            self.buffer += text
            
            # Split by separator and process complete chunks
            parts = self.buffer.split(self.separator)
            self.buffer = parts.pop() or ""  # Keep incomplete part
            
            # Process each complete chunk
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # Parse usage from chunk
                usage = self.provider.parse_usage(part)
                if usage:
                    self._accumulated_usage = self._merge_usage(
                        self._accumulated_usage, usage
                    )
                
                # Apply format conversion if needed
                if self.format_converter:
                    part = self.format_converter(part)
                    yield part + self.separator
                else:
                    yield part
    
    def get_final_usage(self) -> Optional["UsageInfo"]:
        """Return accumulated usage after stream completes"""
        return self._accumulated_usage
    
    def _merge_usage(
        self,
        existing: Optional["UsageInfo"],
        new: "UsageInfo"
    ) -> "UsageInfo":
        """Merge usage info from multiple chunks"""
        if not existing:
            return new
        
        return UsageInfo(
            input_tokens=new.input_tokens,  # Use latest
            output_tokens=new.output_tokens,  # Use latest
            reasoning_tokens=new.reasoning_tokens,
            cache_read_tokens=new.cache_read_tokens,
            cache_write_5m_tokens=new.cache_write_5m_tokens,
            cache_write_1h_tokens=new.cache_write_1h_tokens,
        )
