"""
test_startup_verifier.py - Test startup verification functionality
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.startup_verifier import should_run_startup_verification, run_startup_verification_if_enabled


def test_verification_disabled():
    """Test that verification is disabled by default."""
    # Make sure env var is not set
    if 'STARTUP_VERIFICATION' in os.environ:
        del os.environ['STARTUP_VERIFICATION']
    
    result = should_run_startup_verification()
    assert result is False, "Verification should be disabled by default"
    print("✅ Verification disabled by default")


def test_verification_can_be_enabled():
    """Test that verification can be enabled via env var."""
    test_cases = [
        ('true', True),
        ('True', True),
        ('TRUE', True),
        ('1', True),
        ('yes', True),
        ('on', True),
        ('false', False),
        ('False', False),
        ('0', False),
        ('no', False),
        ('off', False),
    ]
    
    for value, expected in test_cases:
        os.environ['STARTUP_VERIFICATION'] = value
        result = should_run_startup_verification()
        assert result == expected, f"Value '{value}' should return {expected}, got {result}"
        print(f"✅ STARTUP_VERIFICATION={value} → {result}")
    
    # Cleanup
    if 'STARTUP_VERIFICATION' in os.environ:
        del os.environ['STARTUP_VERIFICATION']


def test_conditional_run():
    """Test that run_startup_verification_if_enabled respects env var."""
    # Disabled
    if 'STARTUP_VERIFICATION' in os.environ:
        del os.environ['STARTUP_VERIFICATION']
    
    result = run_startup_verification_if_enabled()
    assert result is None, "Should return None when disabled"
    print("✅ Returns None when STARTUP_VERIFICATION not set")
    
    # Enabled - would actually run the generator, so we'll just check it returns something
    os.environ['STARTUP_VERIFICATION'] = 'true'
    # We won't actually call it here since it would try to generate a real short
    # Just verify the condition works
    should_run = should_run_startup_verification()
    assert should_run is True, "Should return True when STARTUP_VERIFICATION=true"
    print("✅ Correctly identifies when STARTUP_VERIFICATION=true")
    
    # Cleanup
    if 'STARTUP_VERIFICATION' in os.environ:
        del os.environ['STARTUP_VERIFICATION']


if __name__ == '__main__':
    print("\n" + "="*70)
    print("STARTUP VERIFIER CONFIGURATION TEST")
    print("="*70)
    
    try:
        test_verification_disabled()
        print()
        test_verification_can_be_enabled()
        print()
        test_conditional_run()
        
        print("\n" + "="*70)
        print("✅ ALL STARTUP VERIFIER TESTS PASSED")
        print("="*70)
        print("\n📝 Notes:")
        print("   - Actual verification requires valid API keys")
        print("   - Enable with: STARTUP_VERIFICATION=true")
        print("   - Test topic (optional): STARTUP_VERIFICATION_TOPIC=...")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
