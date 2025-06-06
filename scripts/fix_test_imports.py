#!/usr/bin/env python3
"""
Fix import statements in test files for youtube_transcripts project
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single test file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track if we made changes
    original_content = content
    
    # Fix import patterns
    # Pattern 1: from youtube_transcripts.xxx import yyy
    content = re.sub(
        r'from youtube_transcripts\.(?!__)',  # Negative lookahead to not match __init__
        r'from youtube_transcripts.',
        content
    )
    
    # Pattern 2: import youtube_transcripts.xxx
    content = re.sub(
        r'import youtube_transcripts\.(?!__)',
        r'import youtube_transcripts.',
        content
    )
    
    # If content changed, write it back
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all test files"""
    test_dir = Path('tests')
    fixed_files = []
    
    # Find all Python test files
    for file_path in test_dir.rglob('*.py'):
        if file_path.name.startswith('test_') or file_path.name == 'conftest.py':
            if fix_imports_in_file(file_path):
                fixed_files.append(file_path)
                print(f"✅ Fixed imports in: {file_path}")
    
    print(f"\n📊 Summary: Fixed {len(fixed_files)} files")
    
    # Also check if there are any files importing from core, cli, or mcp directly
    print("\n🔍 Checking for other import patterns...")
    
    for file_path in test_dir.rglob('*.py'):
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for direct imports from subdirectories
        if re.search(r'from (core|cli|mcp)\.', content):
            print(f"⚠️  Found direct import in {file_path}")
            # Fix these too
            content = re.sub(r'from core\.', r'from youtube_transcripts.core.', content)
            content = re.sub(r'from cli\.', r'from youtube_transcripts.cli.', content)
            content = re.sub(r'from mcp\.', r'from youtube_transcripts.mcp.', content)
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"✅ Fixed direct imports in: {file_path}")

if __name__ == "__main__":
    main()