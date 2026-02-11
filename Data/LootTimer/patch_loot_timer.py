#!/usr/bin/env python3
"""
Loot Timer Patcher - DISABLED (no-op version)

All timer patches (v1-v14) have failed or caused issues.
This no-op version allows the build to complete without timer patches.
"""

import sys
from pathlib import Path

def main():
    script_dir = Path(__file__).parent

    print("="*60)
    print("Loot Timer Patcher: DISABLED")
    print("="*60)
    print("  Status: No patches applied (all versions failed)")
    print("  Chest timer: Vanilla (20 seconds)")
    print("  Reason: 13 attempts failed, v13-v14 affected enemy damage")
    print("="*60)

    # Exit successfully without patching
    sys.exit(0)

if __name__ == '__main__':
    main()
