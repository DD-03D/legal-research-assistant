import re

# Test the fixed regex pattern
pattern = r'[^\w\s\.\,\;\:\!\?\(\)\[\]\"\'%\$&\-]'

print("Testing fixed regex pattern...")
try:
    compiled = re.compile(pattern)
    print("Pattern compiled successfully!")
    
    # Test with sample text
    test_text = "This is a test with special chars: @#*{}|\\~`+=<>?"
    result = re.sub(pattern, '', test_text)
    print(f"Original: {test_text}")
    print(f"Cleaned:  {result}")
    
except re.error as e:
    print(f"ERROR: {e}")
