"""
Test script to verify the programmatic device setup
python -m measurements.helpers.test_setup_programmatic.test_setup_emulation
"""

import sys

from laboneq.simple import Experiment, Session

from examples.leftline_setup import get_device_setup


def main():
    print("Testing LabOne Q setup configuration...")

    try:
        device_setup = get_device_setup()
        print("✓ Device setup created successfully")
        instruments = list(device_setup.instruments)
        print(f"  - Number of instruments: {len(instruments)}")
        for i, instr in enumerate(instruments):
            print(f"  - Instrument {i+1}: {instr.uid}")
    except Exception as e:
        print(f"✗ Failed to create device setup: {str(e)}")
        return False

    try:
        print("\nCreating LabOne Q session with emulation...")
        session = Session(device_setup=device_setup)
        print("✓ Session created successfully")
    except Exception as e:
        print(f"✗ Failed to create session: {str(e)}")
        return False

    # Try to connect in emulation mode (should work without physical instruments)
    try:
        print("\nConnecting to session in emulation mode...")
        session.connect(do_emulation=True)
        print("✓ Connected to session in emulation mode")
    except Exception as e:
        print(f"✗ Failed to connect in emulation mode: {str(e)}")
        return False

    print("\nSession test passed successfully!")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
