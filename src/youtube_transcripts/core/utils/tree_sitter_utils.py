"""
Enhanced Tree-Sitter utilities for GitGit repository analysis.
Module: tree_sitter_utils.py
Description: Utility functions and helpers for tree sitter utils

This module provides comprehensive code metadata extraction using Tree-Sitter.
It supports a wide range of programming languages and extracts detailed function and
class information including parameter types, default values, and docstrings.

Key features:
1. Support for 100+ programming languages
2. Detailed parameter extraction including types and defaults
3. Docstring extraction and association
4. Class and method relationship tracking
5. Robust error handling with fallbacks
6. Line number tracking for better context

External Dependencies:
- tree_sitter: https://github.com/tree-sitter/py-tree-sitter
- tree_sitter_language_pack: https://github.com/grantjenks/py-tree-sitter-languages
- rich (optional, for CLI): https://github.com/Textualize/rich

Example Usage:
>>> from tree_sitter_utils import extract_code_metadata
>>> metadata = extract_code_metadata(code, "python")
>>> print(metadata["functions"])
[{'name': 'example', 'parameters': [...], ...}]
"""

# Re-export all public functions from the split modules
from .tree_sitter_extractors import (
    extract_default_value,
    extract_docstring,
    extract_parameter_type,
    extract_parameters,
    extract_return_type,
    is_parameter_required,
)
from .tree_sitter_language_mappings import (
    LANGUAGE_MAPPINGS,
    get_language_by_extension,
    get_language_by_name,
    get_language_info,
    get_supported_language,
)
from .tree_sitter_metadata import extract_code_metadata, extract_code_metadata_from_file
from .tree_sitter_traversal import traverse_fallback

# Re-export all functions for backward compatibility
__all__ = [
    # Language mappings
    'LANGUAGE_MAPPINGS',
    'get_language_by_extension',
    'get_language_by_name',
    'get_supported_language',
    'get_language_info',

    # Extractors
    'extract_parameter_type',
    'extract_default_value',
    'is_parameter_required',
    'extract_parameters',
    'extract_return_type',
    'extract_docstring',

    # Metadata extraction
    'extract_code_metadata',
    'extract_code_metadata_from_file',

    # Traversal
    'traverse_fallback'
]


if __name__ == "__main__":
    """
    When run directly, this module provides a demonstration of its functionality
    by parsing a sample code file in each supported language.
    """
    import argparse
    import json

    # Setup argument parser
    parser = argparse.ArgumentParser(description="Tree-sitter code metadata extraction")
    parser.add_argument("--file", "-f", type=str, help="Path to a file to analyze")
    parser.add_argument("--language", "-l", type=str, help="Language identifier (if not using file)")
    parser.add_argument("--code", "-c", type=str, help="Code snippet (if not using file)")
    parser.add_argument("--list-languages", action="store_true", help="List supported languages")
    args = parser.parse_args()

    # Try to use rich for better output, fallback to print
    try:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        use_rich = True
    except ImportError:
        console = None
        use_rich = False

    # List supported languages if requested
    if args.list_languages:
        lang_info = get_language_info()
        if use_rich:
            console.print("[bold]Supported Languages:[/bold]")
            lang_table = Table(title="Tree-sitter Supported Languages")
            lang_table.add_column("Language", style="cyan")
            lang_table.add_column("File Extensions", style="green")

            for lang, exts in sorted(lang_info.items()):
                lang_table.add_row(lang, ", ".join(exts))

            console.print(lang_table)
        else:
            print("Supported Languages:")
            for lang, exts in sorted(lang_info.items()):
                print(f"  {lang}: {', '.join(exts)}")
        exit(0)

    # Analyze a file if provided
    if args.file:
        if use_rich:
            console.print(f"[bold]Analyzing file:[/bold] {args.file}")
        else:
            print(f"Analyzing file: {args.file}")

        metadata = extract_code_metadata_from_file(args.file)

        if not metadata["tree_sitter_success"]:
            error_msg = f"Failed to extract metadata: {metadata.get('error', 'Unknown error')}"
            if use_rich:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(f"ERROR: {error_msg}")
            exit(1)

        # Display functions
        if metadata["functions"]:
            if use_rich:
                func_table = Table(title=f"Functions ({len(metadata['functions'])})")
                func_table.add_column("Name", style="cyan")
                func_table.add_column("Parameters", style="green")
                func_table.add_column("Return Type", style="blue")
                func_table.add_column("Lines", style="magenta")

                for func in metadata["functions"]:
                    params_str = ", ".join([
                        f"{p['name']}: {p['type'] or 'any'}{' (optional)' if not p['required'] else ''}"
                        for p in func["parameters"]
                    ])
                    func_table.add_row(
                        func["name"],
                        params_str or "None",
                        func["return_type"] or "None",
                        f"{func['line_span'][0]}-{func['line_span'][1]}"
                    )

                console.print(func_table)
            else:
                print(f"\nFunctions ({len(metadata['functions'])}):")
                for func in metadata["functions"]:
                    params_str = ", ".join([
                        f"{p['name']}: {p['type'] or 'any'}{' (optional)' if not p['required'] else ''}"
                        for p in func["parameters"]
                    ])
                    print(f"  - {func['name']}({params_str}) -> {func['return_type'] or 'None'}")
                    print(f"    Lines: {func['line_span'][0]}-{func['line_span'][1]}")

        # Display classes
        if metadata["classes"]:
            if use_rich:
                class_table = Table(title=f"Classes ({len(metadata['classes'])})")
                class_table.add_column("Name", style="cyan")
                class_table.add_column("Lines", style="magenta")
                class_table.add_column("Docstring", style="green")

                for cls in metadata["classes"]:
                    class_table.add_row(
                        cls["name"],
                        f"{cls['line_span'][0]}-{cls['line_span'][1]}",
                        (cls["docstring"] or "")[:50] + ("..." if cls["docstring"] and len(cls["docstring"]) > 50 else "")
                    )

                console.print(class_table)
            else:
                print(f"\nClasses ({len(metadata['classes'])}):")
                for cls in metadata["classes"]:
                    print(f"  - {cls['name']}")
                    print(f"    Lines: {cls['line_span'][0]}-{cls['line_span'][1]}")
                    if cls["docstring"]:
                        doc_preview = cls["docstring"][:50] + ("..." if len(cls["docstring"]) > 50 else "")
                        print(f"    Docstring: {doc_preview}")

        success_msg = f"Successfully extracted metadata for {args.file}"
        if use_rich:
            console.print(f"[green]{success_msg}[/green]")
        else:
            print(f"\nSUCCESS: {success_msg}")

    # Analyze a code snippet if provided
    elif args.language and args.code:
        if use_rich:
            console.print(f"[bold]Analyzing {args.language} code snippet[/bold]")
        else:
            print(f"Analyzing {args.language} code snippet")

        metadata = extract_code_metadata(args.code, args.language)

        if not metadata["tree_sitter_success"]:
            error_msg = f"Failed to extract metadata: {metadata.get('error', 'Unknown error')}"
            if use_rich:
                console.print(f"[red]{error_msg}[/red]")
            else:
                print(f"ERROR: {error_msg}")
            exit(1)

        print(json.dumps(metadata, indent=2))

    # Display usage if no arguments provided
    else:
        usage_msg = """Please provide either a file path or a language and code snippet.
Example usage:
  python tree_sitter_utils.py --file path/to/file.py
  python tree_sitter_utils.py --language python --code 'def example(): pass'
  python tree_sitter_utils.py --list-languages"""

        if use_rich:
            console.print("[yellow]" + usage_msg + "[/yellow]")
        else:
            print(usage_msg)
