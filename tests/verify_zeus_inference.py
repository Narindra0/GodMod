import sys
import os
import logging

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)

from src.zeus import inference

def test_inference_confidence():
    print("[TEST] Testing Zeus Inference with Confidence...")
    
    # Mock realistic match data (normalized averages!)
    match_data = {
        'pos_dom': 5, 'pos_ext': 10,
        'forme_dom': 'VVNNV', 'forme_ext': 'DDVND',
        'pts_dom': 30, 'pts_ext': 20,
        'bp_dom': 1.8, 'bc_dom': 0.9,  # Average goals
        'bp_ext': 1.1, 'bc_ext': 1.5,
        'cote_1': 2.10, 'cote_x': 3.20, 'cote_2': 3.50,
        'journee': 16
    }
    
    try:
        action, confidence = inference.predire_match(match_data)
        
        print(f"\n[RESULT] Action: {action}")
        print(f"[RESULT] Confidence: {confidence}")
        
        if isinstance(action, int) and isinstance(confidence, float):
            print("   [SUCCESS] Return types are correct.")
            if 0.0 <= confidence <= 1.0:
                 print("   [SUCCESS] Confidence is within [0, 1].")
            else:
                 print(f"   [FAIL] Confidence out of range: {confidence}")
        else:
            print(f"   [FAIL] Invalid types: {type(action)}, {type(confidence)}")
            
    except Exception as e:
        print(f"   [ERROR] Inference failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inference_confidence()
