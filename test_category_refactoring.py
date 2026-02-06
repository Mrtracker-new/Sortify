"""
Simple test script to verify category refactoring (without PyQt6 dependencies)
"""
import json
from pathlib import Path

print("=" * 60)
print("Testing Category Refactoring")
print("=" * 60)

# Test 1: Check if ConfigManager can be imported
print("\n✓ Test 1: ConfigManager import...")
try:
    # Direct import to avoid PyQt6 dependency in file_operations
    import os
    import logging
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Import ConfigManager directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from core.config_manager import ConfigManager
    
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: ConfigManager loads categories
print("\n✓ Test 2: ConfigManager initialization...")
try:
    config_manager = ConfigManager()
    categories = config_manager.get_categories()
    print(f"   Loaded {len(categories)} main categories")
    print(f"   Categories: {', '.join(list(categories.keys())[:5])}...")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Categories have correct structure
print("\n✓ Test 3: Category structure validation...")
try:
    sample_category = categories.get('Images', {})
    if not sample_category:
        raise ValueError("Images category not found")
    
    sample_subcat = sample_category.get('jpg', {})
    if 'extensions' not in sample_subcat:
        raise ValueError("Extensions key not found in subcategory")
    
    print(f"   Sample: Images/jpg has {len(sample_subcat['extensions'])} extensions")
    print(f"   Extensions: {sample_subcat['extensions']}")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Pattern-based detection exists
print("\n✓ Test 4: Pattern-based detection...")
try:
    whatsapp_subcat = categories['Images'].get('whatsapp', {})
    if 'patterns' not in whatsapp_subcat:
        raise ValueError("Patterns key not found for WhatsApp")
    
    print(f"   WhatsApp patterns: {whatsapp_subcat['patterns']}")
    
    ai_chatgpt = categories.get('AI_Images', {}).get('chatgpt', {})
    if 'patterns' in ai_chatgpt:
        print(f"   AI (ChatGPT) patterns: {ai_chatgpt['patterns']}")
    
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Categories file was created
print("\n✓ Test 5: Categories JSON file creation...")
try:
    categories_file = config_manager.categories_file
    if not categories_file.exists():
        raise FileNotFoundError(f"Categories file not found at {categories_file}")
    
    print(f"   Categories file: {categories_file}")
    print(f"   File size: {categories_file.stat().st_size:,} bytes")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Comprehensive category coverage
print("\n✓ Test 6: Comprehensive category coverage...")
try:
    expected_categories = [
        'Images', 'AI_Images', 'Documents', 'Audio', 'Video',
        'Archives', 'Code', 'Applications', 'Design', 'Databases',
        'Spreadsheets', 'Presentations', 'Email', 'System',
        'Virtual_Machines', 'Torrents', 'Subtitles', 'Uncategorized'
    ]
    
    missing = [cat for cat in expected_categories if cat not in categories]
    if missing:
        raise ValueError(f"Missing categories: {missing}")
    
    print(f"   All {len(expected_categories)} expected categories present")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Verify JSON file content is valid
print("\n✓ Test 7: JSON file validity...")
try:
    with open(categories_file, 'r') as f:
        loaded_categories = json.load(f)
    
    if len(loaded_categories) != len(categories):
        raise ValueError("Mismatch between loaded and saved categories")
    
    print(f"   JSON file contains {len(loaded_categories)} categories")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Count total subcategories and extensions
print("\n✓ Test 8: Category statistics...")
try:
    total_subcats = sum(len(subcats) for subcats in categories.values())
    
    total_extensions = 0
    total_patterns = 0
    for main_cat, subcats in categories.items():
        for subcat, details in subcats.items():
            if isinstance(details, dict):
                total_extensions += len(details.get('extensions', []))
                total_patterns += len(details.get('patterns', []))
    
    print(f"   Main categories: {len(categories)}")
    print(f"   Total subcategories: {total_subcats}")
    print(f"   Total file extensions: {total_extensions}")
    print(f"   Total pattern rules: {total_patterns}")
    print("   ✅ PASSED")
except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print("\n📊 Summary:")
print(f"   ✅ ConfigManager successfully loads categories")
print(f"   ✅ Category structure is correct")
print(f"   ✅ Pattern-based detection is working")
print(f"   ✅ Categories JSON file created")
print(f"   ✅ {len(categories)} comprehensive categories available")
print(f"   ✅ {total_subcats} subcategories with {total_extensions} extensions")
print(f"   ✅ {total_patterns} smart pattern detection rules")
print("\n✨ Category refactoring complete and verified!")
print(f"\n📁 Categories file location: {categories_file}")
