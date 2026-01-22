"""
Opus Codec module for audio compression
Reduces bandwidth by ~90% while maintaining low latency
"""

import numpy as np
from typing import Optional

# Try to import opus library
try:
    import opuslib
    OPUS_AVAILABLE = True
except ImportError:
    try:
        # Try alternative: use ctypes to load opus directly
        import ctypes
        import ctypes.util
        OPUS_AVAILABLE = False
    except:
        OPUS_AVAILABLE = False


class OpusEncoder:
    """Opus audio encoder"""
    
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 2,
        bitrate: int = 64000,
        frame_size: int = 960  # 20ms at 48kHz
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate
        self.frame_size = frame_size
        
        self._encoder = None
        
        if OPUS_AVAILABLE:
            try:
                self._encoder = opuslib.Encoder(
                    sample_rate,
                    channels,
                    opuslib.APPLICATION_AUDIO
                )
                self._encoder.bitrate = bitrate
                print(f"Opus encoder initialized (bitrate: {bitrate})")
            except Exception as e:
                print(f"Failed to create Opus encoder: {e}")
                self._encoder = None
    
    def encode(self, audio_data: np.ndarray) -> bytes:
        """Encode audio data to Opus format"""
        if self._encoder is None:
            # Fallback: just convert to bytes without compression
            return audio_data.tobytes()
        
        try:
            # Ensure correct format (int16)
            if audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # Flatten if needed
            pcm_data = audio_data.flatten().tobytes()
            
            # Encode
            encoded = self._encoder.encode(pcm_data, self.frame_size)
            return encoded
        except Exception as e:
            print(f"Encode error: {e}")
            return audio_data.tobytes()
    
    @property
    def is_available(self) -> bool:
        return self._encoder is not None


class OpusDecoder:
    """Opus audio decoder"""
    
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 2,
        frame_size: int = 960
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = frame_size
        
        self._decoder = None
        
        if OPUS_AVAILABLE:
            try:
                self._decoder = opuslib.Decoder(sample_rate, channels)
                print("Opus decoder initialized")
            except Exception as e:
                print(f"Failed to create Opus decoder: {e}")
                self._decoder = None
    
    def decode(self, encoded_data: bytes) -> np.ndarray:
        """Decode Opus data to audio"""
        if self._decoder is None:
            # Fallback: assume raw int16 data
            return np.frombuffer(encoded_data, dtype=np.int16)
        
        try:
            # Decode
            pcm_data = self._decoder.decode(encoded_data, self.frame_size)
            
            # Convert to numpy array
            audio_data = np.frombuffer(pcm_data, dtype=np.int16)
            
            # Reshape to (samples, channels)
            audio_data = audio_data.reshape(-1, self.channels)
            
            return audio_data
        except Exception as e:
            print(f"Decode error: {e}")
            # Try raw format
            try:
                return np.frombuffer(encoded_data, dtype=np.int16)
            except:
                return np.zeros((self.frame_size, self.channels), dtype=np.int16)
    
    @property
    def is_available(self) -> bool:
        return self._decoder is not None


class SimpleCodec:
    """
    Simple codec without Opus dependency
    Uses basic compression for fallback
    """
    
    def __init__(self, sample_rate: int = 48000, channels: int = 2, frame_size: int = 960):
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = frame_size
    
    def encode(self, audio_data: np.ndarray) -> bytes:
        """Convert audio to bytes (no compression)"""
        if audio_data.dtype != np.int16:
            audio_data = audio_data.astype(np.int16)
        return audio_data.tobytes()
    
    def decode(self, data: bytes) -> np.ndarray:
        """Convert bytes back to audio"""
        audio = np.frombuffer(data, dtype=np.int16)
        return audio.reshape(-1, self.channels)


def get_codec(sample_rate: int = 48000, channels: int = 2, bitrate: int = 64000, frame_size: int = 960):
    """Get the best available codec"""
    if OPUS_AVAILABLE:
        encoder = OpusEncoder(sample_rate, channels, bitrate, frame_size)
        decoder = OpusDecoder(sample_rate, channels, frame_size)
        if encoder.is_available and decoder.is_available:
            return encoder, decoder
    
    # Fallback to simple codec
    print("Opus not available, using uncompressed audio")
    codec = SimpleCodec(sample_rate, channels, frame_size)
    return codec, codec
