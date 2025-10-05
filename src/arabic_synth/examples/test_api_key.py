#!/usr/bin/env python3
"""
Test script to verify that the OpenAI API key is accessible from the .env file.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_env_loading():
    """Test that environment variables can be loaded from .env file."""
    print("🔍 Testing .env file loading...")
    
    # Load environment variables
    load_dotenv()
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY') or os.getenv('openai_api_key')
    
    if api_key:
        print("✅ OpenAI API key found!")
        print(f"   - Key length: {len(api_key)} characters")
        print(f"   - Key starts with: {api_key[:10]}...")
        return True
    else:
        print("❌ OpenAI API key not found")
        print("   - Checked OPENAI_API_KEY and openai_api_key")
        print("   - Please ensure your .env file contains: OPENAI_API_KEY=your_key_here")
        return False

def test_batch_generation_import():
    """Test that batch generation can be imported and API key verified."""
    try:
        from arabic_synth.generators.batch_generation import verify_api_key
        print("✅ Batch generation module imported successfully")
        
        # Test API key verification
        if verify_api_key():
            print("✅ API key verification passed")
            return True
        else:
            print("❌ API key verification failed")
            return False
    except Exception as e:
        print(f"❌ Failed to import batch generation: {e}")
        return False

def main():
    """Run API key tests."""
    print("🧪 Testing OpenAI API key accessibility...")
    print("=" * 50)
    
    tests = [
        ("Load .env file", test_env_loading),
        ("Batch generation API key check", test_batch_generation_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 API key is ready for batch processing!")
        print("\n💡 You can now run:")
        print("   arabic-synth style-subject-workflow --use-batch-processing")
    else:
        print("⚠️  API key setup needs attention. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
