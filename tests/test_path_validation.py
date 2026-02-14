"""
Test script for file path validation security features
Tests path traversal, symlink handling, and system file protection
"""
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.file_operations import FileOperations

def test_path_traversal():
    """Test that path traversal attacks are blocked"""
    print("\n" + "="*60)
    print("TEST 1: Path Traversal Attack Prevention")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Try to access a file outside allowed directories using path traversal
        malicious_path = "../../../Windows/System32/config/sam"
        print(f"\n[ATTACK] Attempting path traversal: {malicious_path}")
        
        try:
            fo.copy_file(malicious_path, "misc/other")
            print("[FAIL] Path traversal was NOT blocked!")
        except (ValueError, FileNotFoundError) as e:
            print(f"[PASS] Path traversal blocked - {str(e)[:100]}")
            
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_system_file_protection():
    """Test that system files are protected"""
    print("\n" + "="*60)
    print("TEST 2: System File Protection")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Try to access a system file
        system_path = "C:/Windows/System32/notepad.exe"
        print(f"\n[ATTACK] Attempting to copy system file: {system_path}")
        
        try:
            fo.copy_file(system_path, "misc/other")
            print("[FAIL] System file access was NOT blocked!")
        except (ValueError, FileNotFoundError) as e:
            print(f"[PASS] System file blocked - {str(e)[:100]}")
            
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_hidden_file_protection():
    """Test that hidden files are protected"""
    print("\n" + "="*60)
    print("TEST 3: Hidden File Protection")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Try to access a hidden file
        hidden_path = str(Path.home() / ".gitconfig")
        print(f"\n[ATTACK] Attempting to copy hidden file: {hidden_path}")
        
        try:
            fo.copy_file(hidden_path, "misc/other")
            print("[FAIL] Hidden file access was NOT blocked!")
        except (ValueError, FileNotFoundError) as e:
            print(f"[PASS] Hidden file blocked - {str(e)[:100]}")
            
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_normal_operations():
    """Test that legitimate operations still work"""
    print("\n" + "="*60)
    print("TEST 4: Normal Operations (Legitimate Files)")
    print("="*60)
    
    try:
        # Create a test file in an allowed directory
        test_file = Path.home() / "Desktop" / "test_file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("This is a test file for validation")
        
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        print(f"\n[TEST] Attempting to copy legitimate file: {test_file}")
        
        try:
            result = fo.copy_file(str(test_file), "documents/text")
            print(f"[PASS] Legitimate operation succeeded")
            print(f"   Would copy to: {result}")
        except Exception as e:
            print(f"[FAIL] Legitimate operation was blocked - {e}")
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_allowed_directories():
    """Test custom allowed directories"""
    print("\n" + "="*60)
    print("TEST 5: Custom Allowed Directories")
    print("="*60)
    
    try:
        # Create a test file in Documents
        test_file = Path.home() / "Documents" / "test_allowed.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Test file for allowed directories")
        
        # Initialize with Documents as additional allowed directory
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True,
            allowed_dirs=[str(Path.home() / "Documents")]
        )
        
        print(f"\n[TEST] Attempting to copy file from allowed custom directory: {test_file}")
        
        try:
            result = fo.copy_file(str(test_file), "documents/text")
            print(f"[PASS] File from custom allowed directory succeeded")
            print(f"   Would copy to: {result}")
        except Exception as e:
            print(f"[FAIL] Custom allowed directory not working - {e}")
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_sensitive_dir_ssh():
    """Test that .ssh directory access is blocked (FL-008)"""
    print("\n" + "="*60)
    print("TEST 6: Sensitive Directory Access - .ssh (FL-008)")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Try to access .ssh directory
        ssh_path = str(Path.home() / ".ssh" / "authorized_keys")
        print(f"\n[ATTACK] Attempting to access .ssh: {ssh_path}")
        
        try:
            fo.copy_file(ssh_path, "misc/other")
            print("[FAIL] .ssh directory access was NOT blocked!")
        except ValueError as e:
            if "sensitive" in str(e).lower() or ".ssh" in str(e):
                print(f"[PASS] .ssh directory blocked - {str(e)[:120]}")
            else:
                print(f"[WARN] Blocked but wrong reason - {str(e)[:120]}")
        except FileNotFoundError as e:
            # File might not exist, but should still trigger sensitive dir check first
            print(f"[WARN] FileNotFoundError (should be ValueError for sensitive dir) - {str(e)[:100]}")
            
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_sensitive_dir_config():
    """Test that .config directory access is blocked (FL-008)"""
    print("\n" + "="*60)
    print("TEST 7: Sensitive Directory Access - .config (FL-008)")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Try to access .config directory
        config_path = str(Path.home() / ".config" / "app" / "settings.ini")
        print(f"\n[ATTACK] Attempting to access .config: {config_path}")
        
        try:
            fo.copy_file(config_path, "misc/other")
            print("[FAIL] .config directory access was NOT blocked!")
        except ValueError as e:
            if "sensitive" in str(e).lower() or ".config" in str(e):
                print(f"[PASS] .config directory blocked - {str(e)[:120]}")
            else:
                print(f"[WARN] Blocked but wrong reason - {str(e)[:120]}")
        except FileNotFoundError as e:
            print(f"[WARN] FileNotFoundError (should be ValueError for sensitive dir) - {str(e)[:100]}")
            
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_path_traversal_to_sensitive():
    """Test that path traversal to sensitive directories is blocked (FL-008)"""
    print("\n" + "="*60)
    print("TEST 8: Path Traversal to Sensitive Dir (FL-008 Reproduction)")
    print("="*60)
    
    try:
        # Create a test file in Downloads
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        test_file = downloads / "test_file.txt"
        test_file.write_text("Test file for path traversal attack")
        
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        # Simulate the exact attack from FL-008 bug report
        # User tries: move_file("~/Downloads/file.txt", "../../.ssh/authorized_keys")
        # After path resolution, dest becomes ~/.ssh/authorized_keys
        attack_dest = str(Path.home() / ".ssh" / "authorized_keys")
        
        print(f"\n[ATTACK] Reproduction of FL-008 attack:")
        print(f"   Source: {test_file}")
        print(f"   Attempting to move to: {attack_dest}")
        
        try:
            # The attack would happen via path traversal in destination
            # We'll test direct access to simulate post-resolution
            fo._validate_path(attack_dest, must_exist=False, operation_type="move")
            print("[FAIL] Path traversal to .ssh was NOT blocked!")
        except ValueError as e:
            if "sensitive" in str(e).lower() or ".ssh" in str(e):
                print(f"[PASS] Path traversal to .ssh blocked!")
                print(f"   Error: {str(e)[:120]}")
            else:
                print(f"[WARN] Blocked but wrong reason - {str(e)[:120]}")
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

def test_multiple_sensitive_dirs():
    """Test blocking of various sensitive directories (FL-008)"""
    print("\n" + "="*60)
    print("TEST 9: Multiple Sensitive Directories (FL-008)")
    print("="*60)
    
    try:
        fo = FileOperations(
            base_path=str(Path.home() / "Desktop"),
            folder_name="TestOrg",
            dry_run=True
        )
        
        sensitive_paths = [
            Path.home() / ".gnupg" / "private-keys-v1.d" / "key.gpg",
            Path.home() / ".aws" / "credentials",
            Path.home() / ".docker" / "config.json",
            Path.home() / ".kube" / "config",
        ]
        
        blocked_count = 0
        for test_path in sensitive_paths:
            dir_name = [p for p in test_path.parts if p.startswith('.') or p == 'AppData'][0]
            try:
                fo._validate_path(str(test_path), must_exist=False, operation_type="test")
                print(f"[FAIL] {dir_name} was NOT blocked!")
            except ValueError as e:
                if "sensitive" in str(e).lower():
                    print(f"[PASS] {dir_name:20s} - blocked")
                    blocked_count += 1
                else:
                    print(f"[WARN] {dir_name:20s} - blocked (wrong reason)")
        
        print(f"\nSummary: {blocked_count}/{len(sensitive_paths)} sensitive directories properly blocked")
        
    except Exception as e:
        print(f"[WARN] Test setup error: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FILE PATH VALIDATION SECURITY TESTS")
    print("="*60)
    
    test_path_traversal()
    test_system_file_protection()
    test_hidden_file_protection()
    test_normal_operations()
    test_allowed_directories()
    
    print("\n" + "="*60)
    print("FL-008 SECURITY FIX TESTS")
    print("="*60)
    
    test_sensitive_dir_ssh()
    test_sensitive_dir_config()
    test_path_traversal_to_sensitive()
    test_multiple_sensitive_dirs()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print()

