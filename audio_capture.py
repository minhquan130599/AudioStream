"""
Audio Capture module using WASAPI Loopback
Captures system audio without requiring additional software
"""

import numpy as np
from typing import Callable, Optional, List, Tuple
import threading

# Try PyAudioWPatch first (supports WASAPI Loopback)
try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    try:
        import pyaudio
        PYAUDIO_AVAILABLE = True
    except ImportError:
        PYAUDIO_AVAILABLE = False

# Fallback to sounddevice
import sounddevice as sd


class AudioCapture:
    """Captures system audio using WASAPI Loopback"""
    
    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 2,
        chunk_size: int = 960,
        device: Optional[int] = None,
        callback: Optional[Callable[[np.ndarray], None]] = None,
        use_loopback: bool = False
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device = device
        self.callback = callback
        self.use_loopback = use_loopback
        
        self._stream = None
        self._pyaudio = None
        self._running = False
        self._lock = threading.Lock()
        self._thread = None
        self.actual_channels = channels
    
    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for WASAPI loopback"""
        if self.callback and self._running:
            # Convert bytes to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self.callback(audio_data)
        return (None, pyaudio.paContinue)
    
    def _sounddevice_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Sounddevice callback for normal input"""
        if status:
            print(f"Capture status: {status}")
        
        if self.callback and self._running:
            audio_data = (indata * 32767).astype(np.int16)
            self.callback(audio_data)
    
    def start(self):
        """Start capturing audio"""
        with self._lock:
            if self._running:
                return
            
            try:
                if self.use_loopback and PYAUDIO_AVAILABLE:
                    self._start_loopback_capture()
                else:
                    self._start_normal_capture()
                    
                self._running = True
            except Exception as e:
                print(f"Failed to start capture: {e}")
                raise
    
    def _start_loopback_capture(self):
        """Start WASAPI loopback capture using PyAudioWPatch"""
        self._pyaudio = pyaudio.PyAudio()
        
        # Find the loopback device for the specified output device
        loopback_device = None
        
        if self.device is not None:
            # Try to get the specific loopback device
            try:
                dev_info = self._pyaudio.get_device_info_by_index(self.device)
                if dev_info.get('isLoopbackDevice', False):
                    loopback_device = dev_info
            except:
                pass
        
        # If no specific device, get default loopback
        if loopback_device is None:
            try:
                loopback_device = self._pyaudio.get_default_wasapi_loopback()
            except (AttributeError, OSError) as e:
                raise ValueError(f"Cannot get default WASAPI loopback device: {e}")
        
        if loopback_device is None:
            raise ValueError("No WASAPI loopback device found")
        
        # Get device parameters
        self.actual_channels = min(int(loopback_device['maxInputChannels']), self.channels)
        if self.actual_channels <= 0:
            self.actual_channels = 2  # Default to stereo
        
        device_sample_rate = int(loopback_device['defaultSampleRate'])
        
        print(f"WASAPI Loopback: {loopback_device['name']}")
        print(f"  Channels: {self.actual_channels}, Sample Rate: {device_sample_rate}")
        
        # Open loopback stream
        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=self.actual_channels,
            rate=device_sample_rate,
            input=True,
            input_device_index=int(loopback_device['index']),
            frames_per_buffer=self.chunk_size,
            stream_callback=self._pyaudio_callback
        )
        
        self._stream.start_stream()
        print(f"Audio capture started (WASAPI loopback, channels: {self.actual_channels})")
    
    def _start_normal_capture(self):
        """Start normal input capture using sounddevice"""
        device = self.device
        channels_to_use = self.channels
        
        if device is None:
            device = self._find_loopback_device()
        
        if device is not None:
            device_info = sd.query_devices(device)
            max_channels = int(device_info['max_input_channels'])
            if max_channels <= 0:
                raise ValueError(f"Device '{device_info['name']}' does not support audio input")
            if max_channels < self.channels:
                print(f"Device only supports {max_channels} channel(s)")
                channels_to_use = max_channels
            self.actual_channels = channels_to_use
        
        self._stream = sd.InputStream(
            device=device,
            samplerate=self.sample_rate,
            channels=channels_to_use,
            blocksize=self.chunk_size,
            dtype=np.float32,
            callback=self._sounddevice_callback,
        )
        
        self._stream.start()
        print(f"Audio capture started (input mode, device: {device}, channels: {channels_to_use})")
    
    def stop(self):
        """Stop capturing audio"""
        with self._lock:
            self._running = False
            
            if self._stream:
                if self.use_loopback and self._pyaudio:
                    self._stream.stop_stream()
                    self._stream.close()
                else:
                    self._stream.stop()
                    self._stream.close()
                self._stream = None
            
            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None
            
            print("Audio capture stopped")
    
    def is_running(self) -> bool:
        """Check if capture is running"""
        return self._running
    
    def _find_loopback_device(self) -> Optional[int]:
        """Find WASAPI loopback device using sounddevice"""
        devices = sd.query_devices()
        
        for i, dev in enumerate(devices):
            name = dev['name'].lower()
            if 'loopback' in name or 'stereo mix' in name or 'what u hear' in name:
                if dev['max_input_channels'] > 0:
                    return i
        
        return None
    
    @staticmethod
    def get_input_devices() -> List[Tuple[int, str, bool]]:
        """Get list of available input devices
        Returns: List of (device_id, name, is_loopback)
        """
        devices = []
        
        # Add WASAPI loopback devices from PyAudioWPatch
        if PYAUDIO_AVAILABLE:
            try:
                p = pyaudio.PyAudio()
                try:
                    # Get default loopback device
                    loopback = p.get_default_wasapi_loopback()
                    if loopback:
                        devices.append((
                            int(loopback['index']),
                            f"🔊 [System Audio] {loopback['name']}",
                            True
                        ))
                except (AttributeError, OSError):
                    pass
                
                # Also check for other loopback devices
                for i in range(p.get_device_count()):
                    try:
                        dev = p.get_device_info_by_index(i)
                        if dev.get('isLoopbackDevice', False):
                            name = dev['name']
                            if not any(name in d[1] for d in devices):
                                devices.append((i, f"🔊 [Loopback] {name}", True))
                    except:
                        pass
                
                p.terminate()
            except Exception as e:
                print(f"Error enumerating PyAudio devices: {e}")
        
        # Add regular input devices from sounddevice
        all_devices = sd.query_devices()
        for i, dev in enumerate(all_devices):
            if dev['max_input_channels'] > 0:
                devices.append((i, f"🎤 {dev['name']}", False))
        
        return devices
    
    @staticmethod
    def get_loopback_devices() -> List[Tuple[int, str]]:
        """Get list of WASAPI loopback devices"""
        devices = []
        
        if PYAUDIO_AVAILABLE:
            try:
                p = pyaudio.PyAudio()
                try:
                    loopback = p.get_default_wasapi_loopback()
                    if loopback:
                        devices.append((int(loopback['index']), loopback['name']))
                except (AttributeError, OSError):
                    pass
                p.terminate()
            except:
                pass
        
        return devices


def list_audio_devices():
    """Print all available audio devices"""
    print("\n=== Available Capture Devices ===")
    devices = AudioCapture.get_input_devices()
    for dev_id, name, is_loopback in devices:
        lb = "[LOOPBACK]" if is_loopback else ""
        print(f"[{dev_id}] {name} {lb}")
    print()


if __name__ == "__main__":
    list_audio_devices()
