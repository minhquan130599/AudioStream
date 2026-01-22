import sounddevice as sd

print("\n=== All Input Devices ===")
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        print(f"[{i}] {d['name']} (IN:{d['max_input_channels']}ch)")

print("\n=== All Output Devices ===")
for i, d in enumerate(sd.query_devices()):
    if d['max_output_channels'] > 0:
        print(f"[{i}] {d['name']} (OUT:{d['max_output_channels']}ch)")

print("\n=== Looking for Loopback/Stereo Mix ===")
for i, d in enumerate(sd.query_devices()):
    name_lower = d['name'].lower()
    if 'loopback' in name_lower or 'stereo mix' in name_lower or 'what u hear' in name_lower:
        print(f"[{i}] {d['name']} (IN:{d['max_input_channels']}, OUT:{d['max_output_channels']})")
