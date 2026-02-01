#!/usr/bin/env python3
"""
Test script to verify thread-safe database implementation
"""
import sys
import os
import threading
import time
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database_manager import DatabaseManager
from core.history import get_data_dir

def test_concurrent_access():
    """Test concurrent database access from multiple threads"""
    print("Testing concurrent database access...")
    
    # Create a test database
    data_dir = get_data_dir()
    test_db_path = data_dir / "test_concurrent.db"
    
    # Remove test database if it exists
    if test_db_path.exists():
        test_db_path.unlink()
    
    # Create DatabaseManager
    db_manager = DatabaseManager(test_db_path)
    
    # Create test table
    db_manager.execute_query(
        """
        CREATE TABLE IF NOT EXISTS test_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id INTEGER,
            operation_num INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        fetch_mode='none'
    )
    
    print(f"✓ Created test database at {test_db_path}")
    
    # Test concurrent writes from multiple threads
    errors = []
    success_count = []
    
    def worker(thread_num, operations=100):
        """Worker function to perform database operations"""
        thread_id = threading.get_ident()
        local_errors = []
        local_success = 0
        
        for i in range(operations):
            try:
                # Perform insert operation
                success = db_manager.execute_transaction([
                    (
                        "INSERT INTO test_operations (thread_id, operation_num) VALUES (?, ?)",
                        (thread_id, i)
                    )
                ])
                
                if success:
                    local_success += 1
                else:
                    local_errors.append(f"Thread {thread_num}, Operation {i}: Transaction failed")
                    
            except Exception as e:
                local_errors.append(f"Thread {thread_num}, Operation {i}: {str(e)}")
        
        errors.extend(local_errors)
        success_count.append(local_success)
        print(f"  Thread {thread_num}: {local_success}/{operations} successful")
    
    # Create and start threads
    num_threads = 5
    operations_per_thread = 50
    threads = []
    
    print(f"\n✓ Starting {num_threads} threads, each performing {operations_per_thread} operations...")
    start_time = time.time()
    
    for i in range(num_threads):
        thread = threading.Thread(target=worker, args=(i, operations_per_thread))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    # Check results
    total_expected = num_threads * operations_per_thread
    total_success = sum(success_count)
    
    print(f"\n{'='*60}")
    print(f"Test Results:")
    print(f"  Total operations: {total_expected}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {len(errors)}")
    print(f"  Time: {end_time - start_time:.2f}s")
    
    # Verify database contents
    result = db_manager.execute_query(
        "SELECT COUNT(*) FROM test_operations",
        fetch_mode='one'
    )
    actual_count = result[0] if result else 0
    
    print(f"  Database records: {actual_count}")
    print(f"{'='*60}")
    
    if errors:
        print(f"\n❌ Errors occurred:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    # Clean up
    db_manager.close_all_connections()
    
    # Final verdict
    if total_success == total_expected and actual_count == total_expected:
        print(f"\n🎉 BOOM! All {total_expected} operations crushed it!")
        print("   Zero race conditions! Database is vibing perfectly! 🔥")
        return True
    else:
        print(f"\n💥 OOPS! Expected {total_expected}, got {total_success} successful, {actual_count} in DB")
        return False

def test_thread_local_connections():
    """Test that each thread gets its own connection"""
    print("\n\nTesting thread-local connections...")
    
    data_dir = get_data_dir()
    test_db_path = data_dir / "test_thread_local.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    db_manager = DatabaseManager(test_db_path)
    
    # Create test table
    db_manager.execute_query(
        """CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            thread_id INTEGER
        )""",
        fetch_mode='none'
    )
    
    connection_ids = set()
    
    def get_connection_id():
        """Get connection ID for current thread"""
        thread_id = threading.get_ident()
        # Each thread should have its own connection
        db_manager.execute_query(
            "INSERT INTO test_table (id, thread_id) VALUES (?, ?)",
            params=(thread_id, thread_id),
            fetch_mode='none'
        )
        connection_ids.add(id(db_manager._get_thread_connection()))
    
    # Create multiple threads
    threads = []
    for i in range(3):
        thread = threading.Thread(target=get_connection_id)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    db_manager.close_all_connections()
    
    print(f"✓ Number of unique connections: {len(connection_ids)}")
    
    if len(connection_ids) == 3:
        print("🎊 NICE! Each thread got its own connection like a boss!")
        return True
    else:
        print("😬 UH-OH: Threads are sharing connections (not cool)!")
        return False

if __name__ == "__main__":
    print("="*60)
    print("🧪 SQLite Thread-Safety Test Suite 🧪")
    print("="*60)
    
    test1 = test_concurrent_access()
    test2 = test_thread_local_connections()
    
    print(f"\n{'='*60}")
    if test1 and test2:
        print("🚀 EVERYTHING WORKS! ALL TESTS PASSED! 🚀")
        print("   Your database is thread-safe and absolutely crushing it!")
    else:
        print("⚠️  HOUSTON, WE HAVE A PROBLEM!")
        print("   Some tests failed - check the output above.")
    print(f"{'='*60}\n")
    
    sys.exit(0 if (test1 and test2) else 1)
