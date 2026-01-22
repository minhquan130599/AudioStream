# 🎵 LAN Audio Streaming

Ứng dụng stream âm thanh hệ thống giữa 2 máy tính qua mạng LAN với độ trễ thấp.

## ✨ Tính năng

- 🔊 **WASAPI Loopback** - Capture âm thanh hệ thống (không cần Stereo Mix)
- 🎧 **Two-way streaming** - Stream âm thanh 2 chiều giữa 2 máy
- 🎛️ **Opus Codec** - Nén âm thanh chất lượng cao, giảm 90% băng thông
- 📊 **Real-time stats** - Hiển thị thống kê gói tin gửi/nhận
- 🎨 **Dark theme UI** - Giao diện đẹp, dễ sử dụng
- 📥 **System Tray** - Thu nhỏ xuống khay hệ thống khi đóng

## 📋 Yêu cầu

- Windows 10/11
- Python 3.8+
- 2 máy tính trong cùng mạng LAN

## 🚀 Cài đặt

```bash
# Clone hoặc download project
cd AudioTool

# Cài đặt dependencies
pip install -r requirements.txt

# Cài thêm PyAudioWPatch cho WASAPI Loopback
pip install pyaudiowpatch

# Cài pystray cho System Tray
pip install pystray pillow
```

## 📦 Dependencies

```
numpy
sounddevice
opuslib
pyaudiowpatch
pystray
pillow
```

## 🎮 Cách sử dụng

### 1. Khởi động ứng dụng

```bash
python app.py
```

### 2. Cấu hình trên cả 2 máy

| Máy A | Máy B |
|-------|-------|
| Peer IP: `IP của máy B` | Peer IP: `IP của máy A` |
| Send Port: `5001` | Send Port: `5002` |
| Receive Port: `5002` | Receive Port: `5001` |

> ⚠️ **Lưu ý**: Send Port của máy A = Receive Port của máy B và ngược lại

### 3. Chọn thiết bị

- **Capture**: Chọn `🔊 [System Audio]...` để stream âm thanh hệ thống
- **Playback**: Chọn thiết bị phát (tai nghe/loa)

### 4. Bắt đầu streaming

Nhấn **▶ START STREAMING** trên cả 2 máy

## 🖥️ System Tray

- **Nhấn X** → Ẩn xuống khay hệ thống
- **Click đúp icon tray** → Hiển thị lại cửa sổ
- **Chuột phải → Thoát** → Đóng ứng dụng hoàn toàn

## 📁 Cấu trúc Project

```
AudioTool/
├── app.py              # Ứng dụng chính với GUI
├── audio_capture.py    # Module capture âm thanh (WASAPI Loopback)
├── audio_playback.py   # Module phát âm thanh
├── opus_codec.py       # Encoder/Decoder Opus
├── udp_streamer.py     # Gửi/nhận UDP packets
├── config.py           # Cấu hình ứng dụng
├── config.json         # File lưu cấu hình
├── requirements.txt    # Dependencies
└── README.md           # Tài liệu này
```

## ⚙️ Cấu hình mặc định

| Tham số | Giá trị | Mô tả |
|---------|---------|-------|
| Sample Rate | 48000 Hz | Tối ưu cho Opus |
| Channels | 2 (Stereo) | Âm thanh stereo |
| Chunk Size | 960 samples | 20ms tại 48kHz |
| Opus Bitrate | 64 kbps | Chất lượng tốt, băng thông thấp |

## 🔧 Troubleshooting

### Lỗi "Invalid number of channels"
- Chọn thiết bị `🔊 [System Audio]...` thay vì microphone Bluetooth

### Không thấy System Audio trong danh sách
- Đảm bảo đã cài `pyaudiowpatch`:
  ```bash
  pip install pyaudiowpatch
  ```

### Không nhận được âm thanh
- Kiểm tra IP và Port đã cấu hình đúng
- Kiểm tra firewall không chặn port UDP
- Đảm bảo cả 2 máy trong cùng mạng LAN

### Âm thanh bị giật/lag
- Giảm Opus bitrate trong `config.py`
- Kiểm tra kết nối mạng

## 📝 License

MIT License

## 👨‍💻 Author

Created with ❤️ for LAN audio streaming
