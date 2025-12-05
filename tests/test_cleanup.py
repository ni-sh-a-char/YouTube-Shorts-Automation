"""
Test cleanup functionality.
Verifies that output folder is deleted after successful operations.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler import cleanup_output_folder


def test_cleanup_creates_and_deletes():
    """Test that cleanup_output_folder deletes a folder and its contents."""
    test_dir = 'test_output_cleanup'
    
    # Create test directory with files
    Path(test_dir).mkdir(exist_ok=True)
    test_file = Path(test_dir) / 'test_file.txt'
    test_file.write_text('This is a test file')
    
    print(f"✅ Created test directory: {test_dir}")
    print(f"   Contents: {list(Path(test_dir).iterdir())}")
    
    # Verify it exists
    assert Path(test_dir).exists(), f"Test directory {test_dir} was not created"
    print(f"✅ Directory exists before cleanup")
    
    # Run cleanup
    result = cleanup_output_folder(test_dir)
    
    # Verify it was deleted
    assert result is True, "Cleanup returned False"
    assert not Path(test_dir).exists(), f"Directory {test_dir} still exists after cleanup"
    print(f"✅ Directory deleted after cleanup")
    print(f"✅ Cleanup test PASSED")


def test_cleanup_nonexistent_dir():
    """Test that cleanup handles non-existent directories gracefully."""
    test_dir = 'nonexistent_dir_test'
    
    # Ensure it doesn't exist
    if Path(test_dir).exists():
        import shutil
        shutil.rmtree(test_dir)
    
    # Run cleanup on non-existent directory
    result = cleanup_output_folder(test_dir)
    
    # Should still return True (graceful handling)
    assert result is True, "Cleanup should return True even for non-existent directories"
    print(f"✅ Cleanup handles non-existent directories gracefully")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("CLEANUP FUNCTIONALITY TEST")
    print("="*70)
    
    try:
        test_cleanup_creates_and_deletes()
        print()
        test_cleanup_nonexistent_dir()
        
        print("\n" + "="*70)
        print("✅ ALL CLEANUP TESTS PASSED")
        print("="*70)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
