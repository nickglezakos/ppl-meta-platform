#!/usr/bin/env python3
"""
Simple test script to verify Nuitka compilation works.
"""

def main():
    print("Hello from Nuitka-compiled Python!")
    print(f"Python version: {__import__('sys').version}")
    print("✅ Nuitka compilation test successful!")

if __name__ == "__main__":
    main()
