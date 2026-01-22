"""
Audio Playback module
Low-latency audio playback for received audio data
"""

import numpy as np
import sounddevice as sd
from typing import Optional, List, Tuple
import threading
import queue


class AudioPlayback:
    """Plays back received audio with low latency"""
    
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 2,
        chunk_size: int = 960,
        device: Optional[int] = None,
        buffer_size: int = 10  # Number of chunks to buffer
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self.buffer_size = buffer_size
        self.volume = 1.0
        
        self._stream: Optional[sd.OutputStream] = None
        self._running = False
        self._lock = threading.Lock()
        self._audio_queue: queue.Queue = queue.Queue(maxsize=buffer_size * 2)
    
    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """Internal callback for audio stream"""
        if status:
            print(f"Playback status: {status}")
        
        try:
            # Get audio from queue
            audio_data = self._audio_queue.get_nowait()
            
            # Convert from int16 to float32 and apply volume
            float_data = audio_data.astype(np.float32) / 32767.0 * self.volume
            
            # Reshape if needed
            if len(float_data.shape) == 1:
                float_data = float_data.reshape(-1, self.channels)
            
            # Copy to output buffer
            if len(float_data) >= frames:
                outdata[:] = float_data[:frames]
            else:
                outdata[:len(float_data)] = float_data
                outdata[len(float_data):] = 0
                
        except queue.Empty:
            # No audio available, output silence
            outdata.fill(0)
    
    def start(self):
        """Start audio playback"""
        with self._lock:
            if self._running:
                return
            
            try:
                self._stream = sd.OutputStream(
                    device=self.device,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.chunk_size,
                    dtype=np.float32,
                    callback=self._audio_callback,
                    latency='low'
                )
                self._stream.start()
                self._running = True
                print(f"Audio playback started (device: {self.device})")
            except Exception as e:
                print(f"Failed to start playback: {e}")
                raise
    
    def stop(self):
        """Stop audio playback"""
        with self._lock:
            self._running = False
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                # Clear the queue
                while not self._audio_queue.empty():
                    try:
                        self._audio_queue.get_nowait()
                    except queue.Empty:
                        break
                print("Audio playback stopped")
    
    def play(self, audio_data: np.ndarray):
        """Queue audio data for playback"""
        if not self._running:
            return
        
        try:
            self._audio_queue.put_nowait(audio_data)
        except queue.Full:
            # Drop oldest frame to prevent latency buildup
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(audio_data)
            except queue.Empty:
                pass
    
    def is_running(self) -> bool:
        """Check if playback is running"""
        return self._running
    
    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
    
    def get_buffer_level(self) -> int:
        """Get current buffer level"""
        return self._audio_queue.qsize()
    
    @staticmethod
    def get_output_devices() -> List[Tuple[int, str]]:
        """Get list of available output devices"""
        devices = []
        all_devices = sd.query_devices()
        
        for i, dev in enumerate(all_devices):
            if dev['max_output_channels'] > 0:
                devices.append((i, dev['name']))
        
        return devices
