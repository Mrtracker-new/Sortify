"""
Test script to verify HistoryManager singleton pattern
"""
import sys
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.history import HistoryManager

def test_singleton():
    """Test that HistoryManager is a singleton"""
    print("Testing HistoryManager Singleton Pattern")
    print("=" * 50)
    
    # Test 1: Basic singleton behavior
    print("\n1. Basic Singleton Test:")
    h1 = HistoryManager()
    h2 = HistoryManager()
    
    print(f"   Instance 1 ID: {id(h1)}")
    print(f"   Instance 2 ID: {id(h2)}")
    print(f"   Same instance: {h1 is h2}")
    assert h1 is h2, "FAILED: Instances are not the same!"
    print("   ✓ PASSED")
    
    # Test 2: Thread safety
    print("\n2. Thread Safety Test:")
    instances = []
    
    def create_instance():
        instances.append(HistoryManager())
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=create_instance)
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All instances should be the same
    first_instance = instances[0]
    all_same = all(inst is first_instance for inst in instances)
    
    print(f"   Created {len(instances)} instances from {len(threads)} threads")
    print(f"   All instances identical: {all_same}")
    assert all_same, "FAILED: Thread safety violated!"
    print("   ✓ PASSED")
    
    # Test 3: No re-initialization
    print("\n3. Re-initialization Guard Test:")
    h = HistoryManager()
    original_db_path = h.db_path
    
    # Call init again (happens when calling HistoryManager() multiple times)
    h.__init__()
    
    # db_path should remain the same
    same_path = h.db_path == original_db_path
    print(f"   DB path unchanged: {same_path}")
    assert same_path, "FAILED: Instance was re-initialized!"
    print("   ✓ PASSED")
    
    print("\n" + "=" * 50)
    print("✅ All tests PASSED - Singleton pattern working correctly!")
    print("=" * 50)

if __name__ == "__main__":
    test_singleton()
