"""
Tree-Sitter metadata extraction core functionality.
Module: tree_sitter_metadata.py
Description: Implementation of tree sitter metadata functionality

This module provides the main metadata extraction functions using Tree-Sitter,
including language-specific queries and fallback traversal methods for extracting
function and class information from source code.

External Dependencies:
- tree_sitter: https://github.com/tree-sitter/py-tree-sitter
- tree_sitter_language_pack: https://github.com/grantjenks/py-tree-sitter-languages

Example Usage:
>>> from tree_sitter_metadata import extract_code_metadata
>>> metadata = extract_code_metadata(code, "python")
>>> print(metadata["functions"])
[{'name': 'example', 'parameters': [...], ...}]
"""

import os
from typing import Any

try:
    import tree_sitter_languages as tsl
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False
    tsl = None

# Try to use loguru if available, otherwise use standard logging
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Import from our split modules
from .tree_sitter_extractors import extract_docstring, extract_parameters, extract_return_type
from .tree_sitter_language_mappings import get_language_by_extension, get_supported_language

# Language-specific query patterns
LANGUAGE_QUERIES = {
    "python": """
        (function_definition
            name: (identifier) @func_name
            parameters: (parameters) @params
            body: (block) @body
        ) @function

        (class_definition
            name: (identifier) @class_name
            body: (block) @class_body
        ) @class
    """,
    "javascript": """
        (function_declaration
            name: (identifier) @func_name
            parameters: (formal_parameters) @params
            body: (statement_block) @body
        ) @function

        (method_definition
            name: (property_identifier) @method_name
            parameters: (formal_parameters) @params
            body: (statement_block) @body
        ) @method

        (class_declaration
            name: (identifier) @class_name
            body: (class_body) @class_body
        ) @class
    """,
    "typescript": """
        (function_declaration
            name: (identifier) @func_name
            parameters: (formal_parameters) @params
            body: (statement_block) @body
        ) @function

        (method_definition
            name: (property_identifier) @method_name
            parameters: (formal_parameters) @params
            body: (statement_block) @body
        ) @method

        (class_declaration
            name: (identifier) @class_name
            body: (class_body) @class_body
        ) @class
    """,
    "java": """
        (method_declaration
            name: (identifier) @method_name
            parameters: (formal_parameters) @params
            body: (block) @body
        ) @method

        (class_declaration
            name: (identifier) @class_name
            body: (class_body) @class_body
        ) @class
    """,
    "cpp": """
        (function_definition
            declarator: (function_declarator
                declarator: (identifier) @func_name
                parameters: (parameter_list) @params
            )
            body: (compound_statement) @body
        ) @function

        (class_specifier
            name: (type_identifier) @class_name
            body: (field_declaration_list) @class_body
        ) @class
    """,
    "go": """
        (function_declaration
            name: (identifier) @func_name
            parameters: (parameter_list) @params
            body: (block) @body
        ) @function

        (method_declaration
            name: (field_identifier) @method_name
            parameters: (parameter_list) @params
            body: (block) @body
        ) @method
    """,
    "ruby": """
        (method
            name: (identifier) @method_name
            parameters: (method_parameters) @params
            body: (body_statement) @body
        ) @method

        (class
            name: (constant) @class_name
            body: (body_statement) @class_body
        ) @class
    """
}


def process_query_captures(capture_results: Any, code: str, language_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Process the captures from a Tree-sitter query.
    
    Args:
        capture_results: The capture results from query.captures()
        code: The source code being analyzed
        language_id: The language identifier
        
    Returns:
        Tuple of (functions list, classes list)
    """
    functions = []
    classes = []

    # Handle dictionary case (most likely based on debug output)
    if isinstance(capture_results, dict):
        # Process functions/methods
        function_nodes = capture_results.get("function", []) + capture_results.get("method", [])
        for node in function_nodes:
            func_info = {
                "name": "",
                "parameters": [],
                "return_type": None,
                "docstring": None,
                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                "code": code[node.start_byte:node.end_byte]
            }

            # Get function name
            if "func_name" in capture_results:
                for name_node in capture_results["func_name"]:
                    if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                        func_info["name"] = name_node.text.decode("utf-8")
                        break

            if "method_name" in capture_results and not func_info["name"]:
                for name_node in capture_results["method_name"]:
                    if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                        func_info["name"] = name_node.text.decode("utf-8")
                        break

            # Get parameters
            if "params" in capture_results:
                for params_node in capture_results["params"]:
                    if params_node.start_byte >= node.start_byte and params_node.end_byte <= node.end_byte:
                        func_info["parameters"] = extract_parameters(params_node, language_id)
                        break

            # Get body and docstring
            if "body" in capture_results:
                for body_node in capture_results["body"]:
                    if body_node.start_byte >= node.start_byte and body_node.end_byte <= node.end_byte:
                        func_info["docstring"] = extract_docstring(body_node, language_id)
                        func_info["return_type"] = extract_return_type(node)
                        break

            functions.append(func_info)

        # Process classes
        class_nodes = capture_results.get("class", [])
        for node in class_nodes:
            class_info = {
                "name": "",
                "methods": [],
                "docstring": None,
                "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                "code": code[node.start_byte:node.end_byte]
            }

            # Get class name
            if "class_name" in capture_results:
                for name_node in capture_results["class_name"]:
                    if name_node.start_byte >= node.start_byte and name_node.end_byte <= node.end_byte:
                        class_info["name"] = name_node.text.decode("utf-8")
                        break

            # Get class body and docstring
            if "class_body" in capture_results:
                for body_node in capture_results["class_body"]:
                    if body_node.start_byte >= node.start_byte and body_node.end_byte <= node.end_byte:
                        class_info["docstring"] = extract_docstring(body_node, language_id)
                        break

            classes.append(class_info)

    # Handle list of tuples case (original expected format)
    else:
        current_function = None
        current_class = None

        for capture in capture_results:
            # Try to handle different capture formats
            if isinstance(capture, tuple):
                if len(capture) == 2:
                    node, name = capture
                elif len(capture) == 3:
                    # Some versions might use (start, end, name) format
                    node = capture[0]
                    name = capture[2]
                else:
                    # Skip if we can't understand the format
                    logger.debug(f"Skipping capture with unexpected format: {capture}")
                    continue
            else:
                # Skip if it's not a tuple
                logger.debug(f"Skipping non-tuple capture: {capture}")
                continue

            if name == "function" or name == "method":
                current_function = {
                    "name": "",
                    "parameters": [],
                    "return_type": None,
                    "docstring": None,
                    "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    "code": code[node.start_byte:node.end_byte]
                }
                functions.append(current_function)

            elif name == "func_name" or name == "method_name":
                if current_function:
                    current_function["name"] = node.text.decode("utf-8")

            elif name == "params":
                if current_function:
                    current_function["parameters"] = extract_parameters(node, language_id)

            elif name == "body":
                if current_function:
                    # Extract docstring and return type
                    current_function["docstring"] = extract_docstring(node, language_id)
                    current_function["return_type"] = extract_return_type(current_function.get("node", node))

            elif name == "class":
                current_class = {
                    "name": "",
                    "methods": [],
                    "docstring": None,
                    "line_span": (node.start_point[0] + 1, node.end_point[0] + 1),
                    "code": code[node.start_byte:node.end_byte]
                }
                classes.append(current_class)

            elif name == "class_name":
                if current_class:
                    current_class["name"] = node.text.decode("utf-8")

            elif name == "class_body":
                if current_class:
                    current_class["docstring"] = extract_docstring(node, language_id)

    return functions, classes


def extract_code_metadata(code: str, language: str) -> dict[str, Any]:
    """
    Extract comprehensive metadata from code using tree-sitter.
    
    Args:
        code: The source code to analyze
        language: The programming language identifier
        
    Returns:
        Dictionary containing extracted metadata
    """
    metadata = {
        "language": language,
        "functions": [],
        "classes": [],
        "tree_sitter_success": False,
        "error": None
    }

    try:
        # Skip unsupported languages
        language_id = get_supported_language(language)
        if not language_id:
            metadata["error"] = f"Unsupported language: {language}"
            return metadata

        # Get parser for the language
        if not HAS_TREE_SITTER:
            return {}
        parser = tsl.get_parser(language_id)

        # Parse the code
        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node

        # Get language-specific query or fallback to python
        query_str = LANGUAGE_QUERIES.get(language_id, LANGUAGE_QUERIES["python"])
        lang_obj = tsl.get_language(language_id)

        try:
            query = lang_obj.query(query_str)
            capture_results = query.captures(root_node)

            # Process the captures
            functions, classes = process_query_captures(capture_results, code, language_id)
            metadata["functions"] = functions
            metadata["classes"] = classes
            metadata["tree_sitter_success"] = True

        except Exception as e:
            # Fallback to a simple approach if the query fails
            logger.warning(f"Query-based extraction failed: {e}, falling back to traversal")
            from .tree_sitter_traversal import traverse_fallback
            functions, classes = traverse_fallback(root_node, code, language_id)
            metadata["functions"] = functions
            metadata["classes"] = classes
            metadata["tree_sitter_success"] = True

    except Exception as e:
        logger.error(f"Error parsing code with tree-sitter: {e}")
        metadata["error"] = str(e)
        metadata["tree_sitter_success"] = False

    return metadata


def extract_code_metadata_from_file(file_path: str) -> dict[str, Any]:
    """
    Extract code metadata from a file.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dictionary containing extracted metadata
    """
    try:
        language = get_language_by_extension(file_path)
        if not language:
            return {
                "language": "unknown",
                "functions": [],
                "classes": [],
                "tree_sitter_success": False,
                "error": f"Unsupported file extension: {os.path.splitext(file_path)[1]}"
            }

        with open(file_path, encoding='utf-8', errors='replace') as f:
            code = f.read()

        metadata = extract_code_metadata(code, language)
        metadata["file_path"] = file_path
        return metadata

    except Exception as e:
        logger.error(f"Error extracting metadata from file {file_path}: {e}")
        return {
            "language": get_language_by_extension(file_path) or "unknown",
            "functions": [],
            "classes": [],
            "file_path": file_path,
            "tree_sitter_success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """Test metadata extraction with real code."""
    test_code = '''
class Calculator:
    """A simple calculator class."""
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers together."""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        return a - b
'''

    metadata = extract_code_metadata(test_code, "python")

    print("Extracted metadata:")
    print(f"Language: {metadata['language']}")
    print(f"Success: {metadata['tree_sitter_success']}")

    if metadata['classes']:
        print(f"\nClasses ({len(metadata['classes'])}):")
        for cls in metadata['classes']:
            print(f"  - {cls['name']} (lines {cls['line_span'][0]}-{cls['line_span'][1]})")
            if cls['docstring']:
                print(f"    Docstring: {cls['docstring']}")

    if metadata['functions']:
        print(f"\nFunctions ({len(metadata['functions'])}):")
        for func in metadata['functions']:
            params = ", ".join([f"{p['name']}: {p['type'] or 'any'}" for p in func['parameters']])
            print(f"  - {func['name']}({params}) -> {func['return_type'] or 'None'}")
            if func['docstring']:
                print(f"    Docstring: {func['docstring']}")

    print("\n✅ Metadata extraction module validation passed")
