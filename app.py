"""
LAN Audio Streaming Application
Two-way system audio streaming over network with GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import socket
from typing import Optional
import numpy as np

# System tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from config import AudioConfig
from audio_capture import AudioCapture, list_audio_devices
from audio_playback import AudioPlayback
from opus_codec import get_codec
from udp_streamer import AudioStreamer


class AudioStreamingApp:
    """Main application with modern GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎵 LAN Audio Streaming")
        self.root.geometry("500x650")
        self.root.resizable(False, False)
        
        # Set dark theme colors
        self.colors = {
            'bg': '#1a1a2e',
            'card': '#16213e',
            'accent': '#0f3460',
            'highlight': '#e94560',
            'text': '#ffffff',
            'text_dim': '#a0a0a0',
            'success': '#4ecca3',
            'warning': '#ffc107'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Load config
        self.config = AudioConfig.load()
        
        # Components
        self.capture: Optional[AudioCapture] = None
        self.playback: Optional[AudioPlayback] = None
        self.streamer: Optional[AudioStreamer] = None
        self.encoder = None
        self.decoder = None
        
        # State
        self.is_streaming = False
        self.stats_thread: Optional[threading.Thread] = None
        
        # System tray
        self.tray_icon = None
        self.is_hidden = False
        
        # Build UI
        self._create_styles()
        self._create_ui()
        self._load_devices()
        
        # Handle close - minimize to tray instead of closing
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        
        # Setup system tray
        if TRAY_AVAILABLE:
            self._setup_tray()
    
    def _create_styles(self):
        """Create custom styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Card.TFrame', background=self.colors['card'])
        style.configure('Dark.TLabel', 
                       background=self.colors['card'], 
                       foreground=self.colors['text'],
                       font=('Segoe UI', 10))
        style.configure('Title.TLabel',
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Segoe UI', 16, 'bold'))
        style.configure('Status.TLabel',
                       background=self.colors['card'],
                       foreground=self.colors['success'],
                       font=('Segoe UI', 11, 'bold'))
    
    def _create_ui(self):
        """Build the user interface"""
        # Main container
        main = tk.Frame(self.root, bg=self.colors['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_frame = tk.Frame(main, bg=self.colors['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(title_frame, text="🎵 LAN Audio Streaming",
                font=('Segoe UI', 20, 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack()
        
        tk.Label(title_frame, text="Stream system audio between computers",
                font=('Segoe UI', 10),
                bg=self.colors['bg'], fg=self.colors['text_dim']).pack()
        
        # Network Settings Card
        self._create_network_card(main)
        
        # Device Settings Card
        self._create_device_card(main)
        
        # Volume Control Card
        self._create_volume_card(main)
        
        # Control Buttons
        self._create_controls(main)
        
        # Status Card
        self._create_status_card(main)
    
    def _create_card(self, parent, title: str) -> tk.Frame:
        """Create a styled card"""
        card = tk.Frame(parent, bg=self.colors['card'], 
                       highlightbackground=self.colors['accent'],
                       highlightthickness=1)
        card.pack(fill=tk.X, pady=8)
        
        # Title
        tk.Label(card, text=title,
                font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['highlight']).pack(
                    anchor='w', padx=15, pady=(12, 8))
        
        # Content frame
        content = tk.Frame(card, bg=self.colors['card'])
        content.pack(fill=tk.X, padx=15, pady=(0, 12))
        
        return content
    
    def _create_network_card(self, parent):
        """Create network settings card"""
        content = self._create_card(parent, "🌐 Network Settings")
        
        # Peer IP
        row1 = tk.Frame(content, bg=self.colors['card'])
        row1.pack(fill=tk.X, pady=4)
        
        tk.Label(row1, text="Peer IP:", width=12, anchor='w',
                font=('Segoe UI', 10),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.peer_ip_var = tk.StringVar(value=self.config.peer_ip)
        self.peer_ip_entry = tk.Entry(row1, textvariable=self.peer_ip_var,
                                      font=('Consolas', 11),
                                      bg=self.colors['accent'], fg=self.colors['text'],
                                      insertbackground=self.colors['text'],
                                      relief=tk.FLAT, width=20)
        self.peer_ip_entry.pack(side=tk.LEFT, padx=5)
        
        # Local IP display
        local_ip = self._get_local_ip()
        tk.Label(row1, text=f"(Your IP: {local_ip})",
                font=('Segoe UI', 9),
                bg=self.colors['card'], fg=self.colors['text_dim']).pack(side=tk.LEFT, padx=10)
        
        # Ports
        row2 = tk.Frame(content, bg=self.colors['card'])
        row2.pack(fill=tk.X, pady=4)
        
        tk.Label(row2, text="Send Port:", width=12, anchor='w',
                font=('Segoe UI', 10),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.send_port_var = tk.StringVar(value=str(self.config.send_port))
        tk.Entry(row2, textvariable=self.send_port_var,
                font=('Consolas', 11), width=8,
                bg=self.colors['accent'], fg=self.colors['text'],
                insertbackground=self.colors['text'],
                relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        tk.Label(row2, text="Receive Port:", width=12, anchor='w',
                font=('Segoe UI', 10),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(20, 0))
        
        self.recv_port_var = tk.StringVar(value=str(self.config.receive_port))
        tk.Entry(row2, textvariable=self.recv_port_var,
                font=('Consolas', 11), width=8,
                bg=self.colors['accent'], fg=self.colors['text'],
                insertbackground=self.colors['text'],
                relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
    
    def _create_device_card(self, parent):
        """Create device settings card"""
        content = self._create_card(parent, "🎧 Audio Devices")
        
        # Input device
        row1 = tk.Frame(content, bg=self.colors['card'])
        row1.pack(fill=tk.X, pady=4)
        
        tk.Label(row1, text="Capture:", width=10, anchor='w',
                font=('Segoe UI', 10),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.input_device_var = tk.StringVar()
        self.input_combo = ttk.Combobox(row1, textvariable=self.input_device_var,
                                        state='readonly', width=40)
        self.input_combo.pack(side=tk.LEFT, padx=5)
        
        # Output device
        row2 = tk.Frame(content, bg=self.colors['card'])
        row2.pack(fill=tk.X, pady=4)
        
        tk.Label(row2, text="Playback:", width=10, anchor='w',
                font=('Segoe UI', 10),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.output_device_var = tk.StringVar()
        self.output_combo = ttk.Combobox(row2, textvariable=self.output_device_var,
                                         state='readonly', width=40)
        self.output_combo.pack(side=tk.LEFT, padx=5)
        
        # Refresh button
        refresh_btn = tk.Button(row2, text="🔄", 
                               font=('Segoe UI', 10),
                               bg=self.colors['accent'], fg=self.colors['text'],
                               activebackground=self.colors['highlight'],
                               relief=tk.FLAT, cursor='hand2',
                               command=self._load_devices)
        refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_volume_card(self, parent):
        """Create volume control card"""
        content = self._create_card(parent, "🔊 Volume")
        
        row = tk.Frame(content, bg=self.colors['card'])
        row.pack(fill=tk.X, pady=4)
        
        tk.Label(row, text="🔈",
                font=('Segoe UI', 12),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        self.volume_var = tk.DoubleVar(value=self.config.volume * 100)
        self.volume_scale = tk.Scale(row, from_=0, to=100,
                                     orient=tk.HORIZONTAL,
                                     variable=self.volume_var,
                                     bg=self.colors['card'], fg=self.colors['text'],
                                     troughcolor=self.colors['accent'],
                                     highlightthickness=0,
                                     length=350,
                                     command=self._on_volume_change)
        self.volume_scale.pack(side=tk.LEFT, padx=10)
        
        tk.Label(row, text="🔊",
                font=('Segoe UI', 12),
                bg=self.colors['card'], fg=self.colors['text']).pack(side=tk.LEFT)
    
    def _create_controls(self, parent):
        """Create control buttons"""
        frame = tk.Frame(parent, bg=self.colors['bg'])
        frame.pack(fill=tk.X, pady=15)
        
        # Start/Stop button
        self.toggle_btn = tk.Button(frame, text="▶  START STREAMING",
                                   font=('Segoe UI', 12, 'bold'),
                                   bg=self.colors['success'], fg=self.colors['bg'],
                                   activebackground='#3db58a',
                                   relief=tk.FLAT, cursor='hand2',
                                   width=25, height=2,
                                   command=self._toggle_streaming)
        self.toggle_btn.pack(pady=5)
    
    def _create_status_card(self, parent):
        """Create status display card"""
        content = self._create_card(parent, "📊 Status")
        
        # Status label
        self.status_var = tk.StringVar(value="⏸ Stopped")
        self.status_label = tk.Label(content, textvariable=self.status_var,
                                     font=('Segoe UI', 12, 'bold'),
                                     bg=self.colors['card'], fg=self.colors['text_dim'])
        self.status_label.pack(anchor='w')
        
        # Stats frame
        stats_frame = tk.Frame(content, bg=self.colors['card'])
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Sent stats
        self.sent_var = tk.StringVar(value="Sent: 0 packets / 0 KB")
        tk.Label(stats_frame, textvariable=self.sent_var,
                font=('Consolas', 9),
                bg=self.colors['card'], fg=self.colors['text_dim']).pack(anchor='w')
        
        # Received stats
        self.recv_var = tk.StringVar(value="Received: 0 packets / 0 KB")
        tk.Label(stats_frame, textvariable=self.recv_var,
                font=('Consolas', 9),
                bg=self.colors['card'], fg=self.colors['text_dim']).pack(anchor='w')
        
        # Lost stats
        self.lost_var = tk.StringVar(value="Lost: 0 packets")
        tk.Label(stats_frame, textvariable=self.lost_var,
                font=('Consolas', 9),
                bg=self.colors['card'], fg=self.colors['warning']).pack(anchor='w')
    
    def _load_devices(self):
        """Load available audio devices"""
        try:
            # Get all capture sources (loopback + mic)
            capture_sources = AudioCapture.get_input_devices()
            output_devices = AudioPlayback.get_output_devices()
            
            # Update input combo - now includes loopback devices
            self.input_devices = capture_sources  # (device_id, name, is_loopback)
            self.input_combo['values'] = [name for i, name, is_loopback in capture_sources]
            if capture_sources:
                # Default to first loopback device (system audio)
                self.input_combo.current(0)
            
            # Update output combo
            self.output_devices = output_devices
            self.output_combo['values'] = [f"[{i}] {name}" for i, name in output_devices]
            if output_devices:
                self.output_combo.current(0)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load devices: {e}")
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _on_volume_change(self, value):
        """Handle volume change"""
        if self.playback:
            self.playback.set_volume(float(value) / 100.0)
    
    def _toggle_streaming(self):
        """Toggle streaming on/off"""
        if self.is_streaming:
            self._stop_streaming()
        else:
            self._start_streaming()
    
    def _start_streaming(self):
        """Start audio streaming"""
        try:
            # Get settings
            peer_ip = self.peer_ip_var.get().strip()
            send_port = int(self.send_port_var.get())
            recv_port = int(self.recv_port_var.get())
            
            # Validate IP
            socket.inet_aton(peer_ip)
            
            # Get selected devices - now includes loopback info
            input_idx = self.input_combo.current()
            output_idx = self.output_combo.current()
            
            # input_devices is now (device_id, name, is_loopback)
            input_device = self.input_devices[input_idx][0] if input_idx >= 0 else None
            use_loopback = self.input_devices[input_idx][2] if input_idx >= 0 else False
            output_device = self.output_devices[output_idx][0] if output_idx >= 0 else None
            
            # For loopback mode, use default stereo (WASAPI loopback will adjust)
            # For mic input, check device channels with sounddevice
            actual_channels = self.config.channels
            if use_loopback:
                # Loopback mode - PyAudioWPatch will handle channels automatically
                actual_channels = 2  # WASAPI loopback usually supports stereo
                print(f"Using WASAPI loopback mode with {actual_channels} channels")
            elif input_device is not None:
                # Mic input - check channels with sounddevice
                import sounddevice as sd
                device_info = sd.query_devices(input_device)
                max_ch = int(device_info['max_input_channels'])
                if max_ch <= 0:
                    raise ValueError(f"Device '{device_info['name']}' does not support audio input")
                if max_ch < self.config.channels:
                    actual_channels = max_ch
                    print(f"Device only supports {actual_channels} channel(s)")
            
            # Initialize codec with actual channels
            self.encoder, self.decoder = get_codec(
                sample_rate=self.config.sample_rate,
                channels=actual_channels,
                frame_size=self.config.chunk_size
            )
            
            # Initialize playback with actual channels
            self.playback = AudioPlayback(
                sample_rate=self.config.sample_rate,
                channels=actual_channels,
                chunk_size=self.config.chunk_size,
                device=output_device
            )
            self.playback.set_volume(self.volume_var.get() / 100.0)
            self.playback.start()
            
            # Initialize streamer
            self.streamer = AudioStreamer(
                target_ip=peer_ip,
                send_port=send_port,
                receive_port=recv_port,
                on_receive=self._on_audio_received
            )
            self.streamer.start()
            
            # Initialize capture with actual channels and loopback mode
            self.capture = AudioCapture(
                sample_rate=self.config.sample_rate,
                channels=actual_channels,
                chunk_size=self.config.chunk_size,
                device=input_device,
                callback=self._on_audio_captured,
                use_loopback=use_loopback
            )
            self.capture.start()
            
            # Update UI
            self.is_streaming = True
            self.toggle_btn.configure(text="⏹  STOP STREAMING",
                                      bg=self.colors['highlight'])
            self.status_var.set("🎵 Streaming...")
            self.status_label.configure(fg=self.colors['success'])
            
            # Disable settings
            self.peer_ip_entry.configure(state='disabled')
            self.input_combo.configure(state='disabled')
            self.output_combo.configure(state='disabled')
            
            # Start stats update
            self._start_stats_update()
            
            # Save config
            self.config.peer_ip = peer_ip
            self.config.send_port = send_port
            self.config.receive_port = recv_port
            self.config.volume = self.volume_var.get() / 100.0
            self.config.save()
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your settings: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start streaming: {e}")
            self._stop_streaming()
    
    def _stop_streaming(self):
        """Stop audio streaming"""
        self.is_streaming = False
        
        # Stop components
        if self.capture:
            self.capture.stop()
            self.capture = None
        
        if self.streamer:
            self.streamer.stop()
            self.streamer = None
        
        if self.playback:
            self.playback.stop()
            self.playback = None
        
        # Update UI
        self.toggle_btn.configure(text="▶  START STREAMING",
                                  bg=self.colors['success'])
        self.status_var.set("⏸ Stopped")
        self.status_label.configure(fg=self.colors['text_dim'])
        
        # Enable settings
        self.peer_ip_entry.configure(state='normal')
        self.input_combo.configure(state='readonly')
        self.output_combo.configure(state='readonly')
    
    def _on_audio_captured(self, audio_data: np.ndarray):
        """Handle captured audio"""
        if not self.is_streaming or not self.streamer:
            return
        
        try:
            # Encode and send
            encoded = self.encoder.encode(audio_data)
            self.streamer.send(encoded)
        except Exception as e:
            print(f"Capture/send error: {e}")
    
    def _on_audio_received(self, data: bytes, sequence: int):
        """Handle received audio"""
        if not self.is_streaming or not self.playback:
            return
        
        try:
            # Decode and play
            audio_data = self.decoder.decode(data)
            self.playback.play(audio_data)
        except Exception as e:
            print(f"Receive/play error: {e}")
    
    def _start_stats_update(self):
        """Start stats update thread"""
        def update_loop():
            while self.is_streaming:
                try:
                    if self.streamer:
                        stats = self.streamer.stats
                        
                        sent = stats['sender']
                        recv = stats['receiver']
                        
                        self.sent_var.set(
                            f"Sent: {sent['packets_sent']:,} packets / "
                            f"{sent['bytes_sent'] / 1024:.1f} KB"
                        )
                        self.recv_var.set(
                            f"Received: {recv['packets_received']:,} packets / "
                            f"{recv['bytes_received'] / 1024:.1f} KB"
                        )
                        self.lost_var.set(f"Lost: {recv['packets_lost']:,} packets")
                except Exception:
                    pass
                time.sleep(0.5)
        
        self.stats_thread = threading.Thread(target=update_loop, daemon=True)
        self.stats_thread.start()
    
    def _create_tray_icon(self):
        """Create icon image for system tray"""
        # Create a simple icon (64x64 with music note symbol)
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a colored circle background
        draw.ellipse([4, 4, size-4, size-4], fill='#e94560')
        
        # Draw a simple music note
        # Note head
        draw.ellipse([35, 38, 50, 50], fill='white')
        # Note stem
        draw.rectangle([47, 15, 50, 42], fill='white')
        # Note flag
        draw.polygon([(50, 15), (50, 28), (40, 22)], fill='white')
        
        return image
    
    def _setup_tray(self):
        """Setup system tray icon and menu"""
        if not TRAY_AVAILABLE:
            return
        
        # Create tray icon image
        icon_image = self._create_tray_icon()
        
        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem('Hiển thị', self._show_from_tray, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Đang stream...' if self.is_streaming else 'Đã dừng', None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Thoát', self._quit_app)
        )
        
        # Create tray icon
        self.tray_icon = pystray.Icon(
            'LAN Audio Streaming',
            icon_image,
            'LAN Audio Streaming',
            menu
        )
    
    def _update_tray_menu(self):
        """Update tray menu to reflect current state"""
        if not TRAY_AVAILABLE or not self.tray_icon:
            return
        
        status_text = '🎵 Đang stream...' if self.is_streaming else '⏹ Đã dừng'
        
        self.tray_icon.menu = pystray.Menu(
            pystray.MenuItem('Hiển thị', self._show_from_tray, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Thoát', self._quit_app)
        )
    
    def _hide_to_tray(self):
        """Hide window to system tray"""
        if TRAY_AVAILABLE and self.tray_icon:
            self.root.withdraw()  # Hide window
            self.is_hidden = True
            
            # Start tray icon in separate thread if not running
            if not self.tray_icon._running:
                tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                tray_thread.start()
            
            # Show notification
            self.tray_icon.notify('LAN Audio Streaming', 'Ứng dụng đã thu nhỏ xuống khay hệ thống')
        else:
            # If tray not available, ask to quit
            if messagebox.askokcancel('Thoát', 'Bạn có muốn thoát ứng dụng?'):
                self._quit_app()
    
    def _show_from_tray(self, icon=None, item=None):
        """Show window from system tray"""
        self.is_hidden = False
        self.root.after(0, self._restore_window)
    
    def _restore_window(self):
        """Restore the window"""
        self.root.deiconify()  # Show window
        self.root.lift()  # Bring to front
        self.root.focus_force()  # Focus
    
    def _quit_app(self, icon=None, item=None):
        """Actually quit the application"""
        # Stop streaming
        if self.is_streaming:
            self._stop_streaming()
        
        # Stop tray icon
        if self.tray_icon and self.tray_icon._running:
            self.tray_icon.stop()
        
        # Destroy window
        self.root.after(0, self.root.destroy)
    
    def _on_close(self):
        """Handle window close - for backward compatibility"""
        self._hide_to_tray()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Entry point"""
    print("Starting LAN Audio Streaming Application...")
    print("-" * 40)
    list_audio_devices()
    
    app = AudioStreamingApp()
    app.run()


if __name__ == "__main__":
    main()
