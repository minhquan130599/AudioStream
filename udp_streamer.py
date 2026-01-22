"""
UDP Streamer module for sending and receiving audio over network
"""

import socket
import threading
import struct
from typing import Callable, Optional
import time


# Packet header format: sequence number (4 bytes) + timestamp (8 bytes)
HEADER_FORMAT = '!IQ'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_PACKET_SIZE = 65507  # Max UDP packet size


class UDPSender:
    """Sends audio data over UDP"""
    
    def __init__(self, target_ip: str, target_port: int):
        self.target_ip = target_ip
        self.target_port = target_port
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._sequence = 0
        self._lock = threading.Lock()
        
        self._packets_sent = 0
        self._bytes_sent = 0
    
    def start(self):
        """Start the sender"""
        with self._lock:
            if self._running:
                return
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self._running = True
            self._sequence = 0
            print(f"UDP sender started -> {self.target_ip}:{self.target_port}")
    
    def stop(self):
        """Stop the sender"""
        with self._lock:
            self._running = False
            if self._socket:
                self._socket.close()
                self._socket = None
            print(f"UDP sender stopped (sent {self._packets_sent} packets, {self._bytes_sent} bytes)")
    
    def send(self, data: bytes):
        """Send audio data"""
        if not self._running or self._socket is None:
            return
        
        try:
            # Create header with sequence number and timestamp
            header = struct.pack(HEADER_FORMAT, self._sequence, int(time.time() * 1000))
            packet = header + data
            
            self._socket.sendto(packet, (self.target_ip, self.target_port))
            self._sequence = (self._sequence + 1) % (2**32)
            self._packets_sent += 1
            self._bytes_sent += len(packet)
        except Exception as e:
            print(f"Send error: {e}")
    
    def update_target(self, ip: str, port: int):
        """Update target address"""
        self.target_ip = ip
        self.target_port = port
    
    @property
    def stats(self) -> dict:
        return {
            'packets_sent': self._packets_sent,
            'bytes_sent': self._bytes_sent
        }


class UDPReceiver:
    """Receives audio data over UDP"""
    
    def __init__(
        self,
        listen_port: int,
        callback: Optional[Callable[[bytes, int], None]] = None
    ):
        self.listen_port = listen_port
        self.callback = callback
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._packets_received = 0
        self._bytes_received = 0
        self._last_sequence = -1
        self._packets_lost = 0
    
    def start(self):
        """Start the receiver"""
        with self._lock:
            if self._running:
                return
            
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self._socket.bind(('0.0.0.0', self.listen_port))
            self._socket.settimeout(0.5)  # Timeout for clean shutdown
            
            self._running = True
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            print(f"UDP receiver started on port {self.listen_port}")
    
    def stop(self):
        """Stop the receiver"""
        with self._lock:
            self._running = False
        
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        
        with self._lock:
            if self._socket:
                self._socket.close()
                self._socket = None
        
        print(f"UDP receiver stopped (received {self._packets_received} packets, lost {self._packets_lost})")
    
    def _receive_loop(self):
        """Main receive loop"""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(MAX_PACKET_SIZE)
                
                if len(data) < HEADER_SIZE:
                    continue
                
                # Parse header
                header = data[:HEADER_SIZE]
                sequence, timestamp = struct.unpack(HEADER_FORMAT, header)
                audio_data = data[HEADER_SIZE:]
                
                # Track packet loss
                if self._last_sequence >= 0:
                    expected = (self._last_sequence + 1) % (2**32)
                    if sequence != expected:
                        lost = (sequence - expected) % (2**32)
                        if lost < 1000:  # Reasonable gap
                            self._packets_lost += lost
                
                self._last_sequence = sequence
                self._packets_received += 1
                self._bytes_received += len(data)
                
                # Call callback
                if self.callback:
                    self.callback(audio_data, sequence)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"Receive error: {e}")
    
    @property
    def stats(self) -> dict:
        return {
            'packets_received': self._packets_received,
            'bytes_received': self._bytes_received,
            'packets_lost': self._packets_lost
        }


class AudioStreamer:
    """Combined audio streamer with send and receive capabilities"""
    
    def __init__(
        self,
        target_ip: str,
        send_port: int = 5001,
        receive_port: int = 5002,
        on_receive: Optional[Callable[[bytes, int], None]] = None
    ):
        self.sender = UDPSender(target_ip, send_port)
        self.receiver = UDPReceiver(receive_port, on_receive)
        self._running = False
    
    def start(self):
        """Start both sender and receiver"""
        self.sender.start()
        self.receiver.start()
        self._running = True
    
    def stop(self):
        """Stop both sender and receiver"""
        self._running = False
        self.sender.stop()
        self.receiver.stop()
    
    def send(self, data: bytes):
        """Send audio data"""
        self.sender.send(data)
    
    def update_target(self, ip: str, port: int):
        """Update target for sender"""
        self.sender.update_target(ip, port)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def stats(self) -> dict:
        return {
            'sender': self.sender.stats,
            'receiver': self.receiver.stats
        }
