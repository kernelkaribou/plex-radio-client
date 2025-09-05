#!/usr/bin/env python3
"""Simple I2C LCD screen clear utility."""
import time

def main():
    try:
        from i2c_lcd import lcd
        display = lcd(0x27)
        display.lcd_clear()
        print("Screen cleared")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
