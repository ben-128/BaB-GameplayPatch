#!/usr/bin/env python3
"""
Broad search for ALL possible timer decrement patterns in the Cavern F1 overlay.
Searches the ORIGINAL (unpatched) BLAZE.ALL.

Cavern F1 overlay: offset 0x009468A8, size 137824 bytes (0x21A5C).
RAM base when loaded: 0x80080000.
"""

import struct
import os

# === Configuration ===
BLAZE_ALL_PATH = r"D:\projets\Bab_Gameplay_Patch\Blaze  Blade - Eternal Quest (Europe)\extract\BLAZE.ALL"
OVERLAY_OFFSET = 0x009468A8
OVERLAY_SIZE = 0x21A5C  # 137824 bytes
RAM_BASE = 0x80080000
