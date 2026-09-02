"""Check setupapi.dll and cfgmgr32.dll for PnP Device Node Creation."""

import ctypes
from pathlib import Path

setupapi = ctypes.windll.setupapi
cfgmgr = ctypes.windll.cfgmgr32

print("setupapi loaded:", bool(setupapi))
print("cfgmgr32 loaded:", bool(cfgmgr))

# Check for SwDevice.dll location in System32 or SysWOW64
for p in [Path("C:/Windows/System32/swdevice.dll"), Path("C:/Windows/SysWOW64/swdevice.dll")]:
    print(f"Path {p}: {p.exists()}")
