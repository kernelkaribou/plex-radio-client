#!/usr/bin/env python3
"""
Quick test for Radio Off marquee scrolling.
"""

import time
from display_manager import create_i2c_display_manager, RadioDefaultScreen

def quick_marquee_test():
    print("=== Quick Radio Off Marquee Test ===")
    
    display = create_i2c_display_manager()
    radio_screen = RadioDefaultScreen()
    display.show_screen(radio_screen)
    
    # Set to radio OFF state
    display.update_context(is_playing=False)
    
    print("Testing Radio Off marquee for 10 seconds...")
    print("Expected: 'Radio Off  -  Radio Off  -  Radio Off  -  ' should scroll")
    
    for i in range(100):  # 10 seconds at 0.1s intervals
        display.update_display()
        time.sleep(0.1)
        
        # Print status every 2 seconds
        if i % 20 == 0:
            print(f"  {i//10 + 1} seconds elapsed...")
    
    print("Test complete! Radio Off should have been scrolling.")
    display.clear_display()

if __name__ == "__main__":
    quick_marquee_test()
