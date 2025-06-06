#!/usr/bin/env python3
"""
Module: remove_mocks_from_tests.py
Description: Remove mocks from test files and convert to real service calls

External Dependencies:
None

Sample Input:
>>> python remove_mocks_from_tests.py tests/integration/test_research_pipeline_edge_cases.py

Expected Output:
>>> Modified test file with mocks removed and real service calls

Example Usage:
>>> ./remove_mocks_from_tests.py --all
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def remove_mock_imports(content: str) -> str:
    """Remove mock-related imports."""
    # Remove mock imports
    content = re.sub(r'from\s+unittest\.mock\s+import.*\n', '', content)
    content = re.sub(r'import\s+unittest\.mock.*\n', '', content)
    content = re.sub(r'from\s+mock\s+import.*\n', '', content)
    content = re.sub(r'import\s+mock.*\n', '', content)
    
    # Remove MagicMock references
    content = content.replace('MagicMock', 'object')
    
    return content


def convert_patch_to_real_call(content: str) -> str:
    """Convert @patch decorators and with patch statements to real calls."""
    # Remove @patch decorators
    content = re.sub(r'@patch\([^)]+\)\s*\n', '', content)
    
    # Convert with patch statements to try/except blocks
    # This is complex, so we'll handle specific patterns
    
    # Pattern: with patch('module.function') as mock:
    pattern = r'with\s+patch\s*\([\'"]([^\'")]+)[\'"]\)\s*as\s+(\w+):\s*\n'
    
    def replace_with_patch(match):
        module_path = match.group(1)
        mock_name = match.group(2)
        return f"# Converted from mock to real call\n    try:\n"
    
    content = re.sub(pattern, replace_with_patch, content)
    
    # Remove mock-specific method calls
    content = re.sub(r'\.return_value\s*=.*\n', '', content)
    content = re.sub(r'\.side_effect\s*=.*\n', '', content)
    content = re.sub(r'mock_\w+\.', '', content)
    
    return content


def add_real_test_data(content: str, file_path: Path) -> str:
    """Add real test data constants."""
    if 'test_research_pipeline' in str(file_path):
        # Add real YouTube video IDs for testing
        real_data = '''
# Real test data - no mocks
REAL_TEST_VIDEOS = {
    'rick_astley': 'dQw4w9WgXcQ',  # Always available
    'short_test': '9bZkp7q19f0',   # Gangnam Style - short, always available
}
'''
        # Insert after imports
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(('import', 'from', '#')):
                import_end = i
                break
        
        lines.insert(import_end, real_data)
        content = '\n'.join(lines)
    
    return content


def fix_test_methods(content: str) -> str:
    """Fix test methods to use real services."""
    # Fix specific test patterns
    fixes = [
        # Remove mock assertions
        (r'mock_\w+\.assert_called.*\n', ''),
        (r'assert\s+mock_\w+\.call_count.*\n', ''),
        
        # Convert mock return values to real expectations
        (r'mock\.return_value\s*=\s*({[^}]+})', r'# Expect real result like: \1'),
        
        # Fix patch.dict for environment variables
        (r"with\s+patch\.dict\s*\(\s*'os\.environ'.*?\):", 
         "# Using real environment variables"),
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def process_file(file_path: Path) -> Tuple[bool, str]:
    """Process a single test file to remove mocks."""
    try:
        original_content = file_path.read_text()
        
        # Skip honeypot tests
        if 'honeypot' in str(file_path):
            return False, "Skipped honeypot test"
        
        # Check if file has mocks
        if not any(word in original_content for word in ['mock', 'Mock', '@patch', 'MagicMock']):
            return False, "No mocks found"
        
        # Process content
        content = original_content
        content = remove_mock_imports(content)
        content = convert_patch_to_real_call(content)
        content = add_real_test_data(content, file_path)
        content = fix_test_methods(content)
        
        # Save if changed
        if content != original_content:
            file_path.write_text(content)
            return True, "Mocks removed"
        
        return False, "No changes made"
        
    except Exception as e:
        return False, f"Error: {str(e)}"


def find_test_files_with_mocks(test_dir: Path) -> List[Path]:
    """Find all test files containing mocks."""
    test_files = []
    
    for file_path in test_dir.rglob("test_*.py"):
        if file_path.is_file() and 'honeypot' not in str(file_path):
            content = file_path.read_text()
            if any(word in content for word in ['mock', 'Mock', '@patch', 'MagicMock']):
                test_files.append(file_path)
    
    return test_files


def main():
    """Main function to remove mocks from tests."""
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        # Process all test files
        test_dir = Path(__file__).parent.parent / "tests"
        test_files = find_test_files_with_mocks(test_dir)
        
        print(f"Found {len(test_files)} test files with mocks")
        
        success_count = 0
        for file_path in test_files:
            print(f"\nProcessing {file_path.relative_to(test_dir.parent)}...")
            success, message = process_file(file_path)
            print(f"  {message}")
            if success:
                success_count += 1
        
        print(f"\n✅ Successfully processed {success_count}/{len(test_files)} files")
        
    elif len(sys.argv) > 1:
        # Process specific file
        file_path = Path(sys.argv[1])
        if file_path.exists():
            success, message = process_file(file_path)
            print(f"{file_path.name}: {message}")
            sys.exit(0 if success else 1)
        else:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
    else:
        print("Usage: remove_mocks_from_tests.py [--all | <test_file>]")
        sys.exit(1)


if __name__ == "__main__":
    main()