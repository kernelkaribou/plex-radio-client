#!/usr/bin/env python3
"""
I2C LCD Screen Clear Utility

Simple script to clear the I2C LCD display.
Useful for resetting the screen if it becomes corrupted or unresponsive.

Usage:
    python3 clear_screen.py
    
Or in Docker:
    docker exec plex-radio-client python3 clear_screen.py
"""

import sys
import time


def clear_i2c_lcd():
    """Clear the I2C LCD display."""
    try:
        # Import the LCD library
        from i2c_lcd import lcd
        
        print("Initializing I2C LCD...")
        display = lcd()
        
        print("Clearing display...")
        display.lcd_clear()
        
        # Add a small delay to ensure the clear command completes
        time.sleep(0.1)
        
        # Optionally display a brief "Screen Cleared" message
        display.lcd_display_string("Screen Cleared", 1)
        display.lcd_display_string("", 2)  # Clear second line
        
        time.sleep(1.0)  # Show message for 1 second
        
        # Final clear
        display.lcd_clear()
        
        print("I2C LCD screen cleared successfully!")
        return True
        
    except ImportError:
        print("ERROR: i2c_lcd module not found.")
        print("Please install it with: pip install i2c-lcd")
        return False
        
    except Exception as e:
        print(f"ERROR: Failed to clear I2C LCD screen: {e}")
        print("Possible issues:")
        print("- I2C not enabled on system")
        print("- No LCD connected")
        print("- Permission denied on /dev/i2c-1")
        print("- LCD hardware failure")
        return False


def main():
    """Main function."""
    print("I2C LCD Screen Clear Utility")
    print("=" * 30)
    
    success = clear_i2c_lcd()
    
    if success:
        print("[SUCCESS] Screen cleared successfully")
        sys.exit(0)
    else:
        print("[ERROR] Failed to clear screen")
        sys.exit(1)


if __name__ == "__main__":
    main()
