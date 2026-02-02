"""
Test script to verify FileOperations initialization fix with actual PyQt6
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.file_operations import FileOperations

def test_fail_fast_on_none_values():
    """Test that FileOperations raises ValueError when None values are passed in non-dry-run mode"""
    print("🧪 Test 1: Let's see if FileOperations has our back when we forget to pass values...")
    
    try:
        file_ops = FileOperations(base_path=None, folder_name=None, dry_run=False)
        print("  💀 Oof! It let us through with nothing but air. That's not good!")
        return False
    except ValueError as e:
        expected_msg = "base_path and folder_name are required for non-dry-run mode"
        if expected_msg in str(e):
            print(f"  🎉 Nice! It caught our mistake and said: '{e}'")
            return True
        else:
            print(f"  🤔 Hmm, it complained but said something weird: '{e}'")
            return False
    except Exception as e:
        print(f"  🚨 Plot twist! It exploded with: {type(e).__name__}: {e}")
        return False

def test_dry_run_accepts_none():
    """Test that FileOperations accepts None values in dry-run mode"""
    print("\n🧪 Test 2: Dry-run mode should chill out and let None values slide...")
    
    try:
        file_ops = FileOperations(base_path=None, folder_name=None, dry_run=True)
        print(f"  🎉 Sweet! It created a FileOperations with home at: {file_ops.base_dir}")
        
        # Verify default values were used
        expected_path = Path.home() / "Documents" / "Organized Files"
        if file_ops.base_dir == expected_path:
            print(f"  🎯 Bullseye! Default path is exactly where it should be: {file_ops.base_dir}")
            return True
        else:
            print(f"  🤔 Wait, that's not where we expected: got {file_ops.base_dir}, wanted {expected_path}")
            return False
    except Exception as e:
        print(f"  🚨 Yikes! Something went sideways: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_valid_parameters():
    """Test that FileOperations works correctly with valid parameters"""
    print("\n🧪 Test 3: The happy path - everything goes right!")
    
    try:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        file_ops = FileOperations(base_path=temp_dir, folder_name="TestOrg", dry_run=False)
        print(f"  🎉 FileOperations is alive and kicking at: {file_ops.base_dir}")
        
        # Verify the path was created
        if file_ops.base_dir.exists():
            print(f"  📁 Beautiful! The folder actually exists on disk.")
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            return True
        else:
            print(f"  👻 Spooky... the folder should exist but doesn't.")
            return False
    except Exception as e:
        print(f"  🚨 Even the happy path hit a snag: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_partial_none_values():
    """Test that FileOperations fails when only one parameter is None"""
    print("\n🧪 Test 4: What if we only give it half the info?")
    
    try:
        file_ops = FileOperations(base_path="/some/path", folder_name=None, dry_run=False)
        print("  💀 It accepted our half-baked input! That's risky...")
        return False
    except ValueError as e:
        print(f"  🎉 Good catch! It said: '{e}'")
        return True
    except Exception as e:
        print(f"  🚨 Unexpected drama: {type(e).__name__}: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("🚀 FileOperations Initialization Fix - The Test Gauntlet")
    print("=" * 70)
    
    tests = [
        test_fail_fast_on_none_values,
        test_dry_run_accepts_none,
        test_valid_parameters,
        test_partial_none_values
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  💥 Test went totally off the rails: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    emoji = "🎊" if passed == total else "😬"
    print(f"{emoji} Final Score: {passed}/{total} tests passed")
    print("=" * 70)
    
    if all(results):
        print("🏆 Crushing it! Everything works perfectly!")
        return 0
    else:
        print("🔧 Back to the drawing board... something's broken.")
        return 1

if __name__ == "__main__":
    sys.exit(main())