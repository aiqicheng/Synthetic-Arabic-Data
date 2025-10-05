#!/usr/bin/env python3
"""
Test script to verify llm_batch_helper integration without requiring API calls.
"""

import sys
from pathlib import Path

def test_import():
    """Test that llm_batch_helper can be imported correctly."""
    try:
        from llm_batch_helper import process_prompts_batch, LLMConfig
        print("✅ llm_batch_helper import successful")
        print(f"   - process_prompts_batch: {process_prompts_batch}")
        print(f"   - LLMConfig: {LLMConfig}")
        return True
    except ImportError as e:
        print(f"❌ llm_batch_helper import failed: {e}")
        return False

def test_batch_generation_import():
    """Test that our batch generation module can be imported."""
    try:
        from arabic_synth.generators.batch_generation import run_batch_generation, BatchGenerationConfig
        print("✅ arabic_synth batch generation import successful")
        print(f"   - run_batch_generation: {run_batch_generation}")
        print(f"   - BatchGenerationConfig: {BatchGenerationConfig}")
        return True
    except ImportError as e:
        print(f"❌ arabic_synth batch generation import failed: {e}")
        return False

def test_config_creation():
    """Test that we can create configuration objects."""
    try:
        from arabic_synth.generators.batch_generation import BatchGenerationConfig
        from llm_batch_helper import LLMConfig
        
        # Test our config
        batch_config = BatchGenerationConfig(
            batch_size=5,
            temperature=0.7,
            top_p=0.95
        )
        print("✅ BatchGenerationConfig creation successful")
        print(f"   - batch_size: {batch_config.batch_size}")
        print(f"   - temperature: {batch_config.temperature}")
        
        # Test LLM config conversion
        llm_config = batch_config.to_llm_config("gpt-4o")
        print("✅ LLMConfig conversion successful")
        print(f"   - model_name: {llm_config.model_name}")
        print(f"   - temperature: {llm_config.temperature}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration creation failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🧪 Testing llm_batch_helper integration...")
    print("=" * 50)
    
    tests = [
        ("Import llm_batch_helper", test_import),
        ("Import batch generation module", test_batch_generation_import),
        ("Create configurations", test_config_creation),
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
        print("🎉 All integration tests passed! llm_batch_helper is ready to use.")
        print("\n💡 To use batch processing in your workflow:")
        print("   arabic-synth style-subject-workflow --use-batch-processing --batch-size 10")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
