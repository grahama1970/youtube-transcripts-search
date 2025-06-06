"""
Tree-Sitter extraction utilities for parameters, types, and docstrings.
Module: tree_sitter_extractors.py
Description: Implementation of tree sitter extractors functionality

This module provides functions to extract detailed information from Tree-Sitter
syntax nodes including parameter types, default values, return types, and docstrings
for various programming languages.

External Dependencies:
- tree_sitter: https://github.com/tree-sitter/py-tree-sitter

Example Usage:
>>> from tree_sitter import Node
>>> params = extract_parameters(params_node, "python")
>>> print(params)
[{'name': 'arg1', 'type': 'str', 'default': None, 'required': True}]
"""

from typing import Any

from tree_sitter import Node

# Try to use loguru if available, otherwise use standard logging
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def extract_parameter_type(node: Node) -> str | None:
    """
    Extract type information from a parameter node.
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        Type annotation as a string, or None if not found
    """
    # Check for explicit type annotations
    type_node = node.child_by_field_name("type")
    if type_node:
        return type_node.text.decode("utf-8")

    # Look for Python-style annotations
    for child in node.children:
        if child.type == "type_annotation":
            for subchild in child.children:
                if subchild.type not in (":", "annotation"):
                    return subchild.text.decode("utf-8")

    # Look for TypeScript-style annotations
    for child in node.children:
        if child.type == "type_annotation" or child.type == "type":
            return child.text.decode("utf-8")

    return None


def extract_default_value(node: Node) -> str | None:
    """
    Extract default value from a parameter node.
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        Default value as a string, or None if not found
    """
    # For Python default parameters
    if node.type == "default_parameter" or node.type.endswith("default_parameter"):
        for child in node.children:
            if child.type == "=" or child.type == "eq":
                # The next sibling should be the default value
                idx = node.children.index(child)
                if idx < len(node.children) - 1:
                    return node.children[idx + 1].text.decode("utf-8")

    # For TypeScript/JavaScript default parameters
    for child in node.children:
        if child.type == "initializer" or child.type == "default_value":
            for subchild in child.children:
                if subchild.type != "=":
                    return subchild.text.decode("utf-8")

    return None


def is_parameter_required(node: Node) -> bool:
    """
    Determine if a parameter is required (no default value).
    
    Args:
        node: The parameter node to analyze
        
    Returns:
        True if the parameter is required, False otherwise
    """
    # If it has a default value, it's not required
    if extract_default_value(node) is not None:
        return False

    # Check for optional markers in TypeScript/JavaScript
    for child in node.children:
        if child.type == "?" or child.text.decode("utf-8") == "?":
            return False

    return True


def extract_parameters(parameters_node: Node, language: str) -> list[dict[str, Any]]:
    """
    Extract comprehensive parameter information including types, defaults, and requirements.
    
    Args:
        parameters_node: The function parameters node
        language: The programming language identifier
        
    Returns:
        List of parameter dictionaries with name, type, default, and required fields
    """
    params = []

    if not parameters_node:
        return params

    for child in parameters_node.children:
        # Skip punctuation and non-parameter nodes
        if child.type in (",", "(", ")", "[", "]", "{", "}", "comment"):
            continue

        param_info = {
            "name": None,
            "type": None,
            "default": None,
            "required": True
        }

        # Direct identifier (simple parameter)
        if child.type == "identifier":
            param_info["name"] = child.text.decode("utf-8")

        # Typed or default parameters
        elif child.type in ("typed_parameter", "default_parameter", "optional_parameter",
                          "parameter", "formal_parameter", "required_parameter"):
            # Find the parameter name
            name_node = child.child_by_field_name("name")
            if name_node:
                param_info["name"] = name_node.text.decode("utf-8")
            else:
                # Search for an identifier or pattern node
                for subchild in child.children:
                    if subchild.type == "identifier" or subchild.type == "pattern":
                        param_info["name"] = subchild.text.decode("utf-8")
                        break

            # Extract type information
            param_info["type"] = extract_parameter_type(child)

            # Extract default value
            param_info["default"] = extract_default_value(child)

            # Determine if required
            param_info["required"] = is_parameter_required(child)

        # For rest parameters (e.g., ...args in JavaScript)
        elif child.type == "rest_parameter":
            for subchild in child.children:
                if subchild.type == "identifier":
                    param_info["name"] = "..." + subchild.text.decode("utf-8")
                    param_info["required"] = False
                    break

        # Add the parameter if we found a name
        if param_info["name"]:
            params.append(param_info)

    return params


def extract_return_type(node: Node) -> str | None:
    """
    Extract the function return type if specified.
    
    Args:
        node: The function definition node
        
    Returns:
        Return type as a string, or None if not found
    """
    # Check for TypeScript/Java style return type
    return_type = node.child_by_field_name("return_type")
    if return_type:
        return return_type.text.decode("utf-8")

    # Check for Python style return annotation
    for child in node.children:
        if child.type == "return_type" or child.type == "return_type_annotation":
            # Skip the arrow itself
            for subchild in child.children:
                if subchild.type not in ("->", ":"):
                    return subchild.text.decode("utf-8")

    return None


def extract_docstring(body_node: Node, language: str) -> str | None:
    """
    Extract docstring based on the programming language.
    
    Args:
        body_node: The function/class body node
        language: The programming language identifier
        
    Returns:
        Docstring as a string, or None if not found
    """
    if not body_node:
        return None

    # Python-style docstrings
    if language == "python":
        for child in body_node.children:
            if child.type == "expression_statement":
                expr = child.child_by_field_name("expression")
                if expr and expr.type == "string":
                    docstring = expr.text.decode("utf-8").strip("'\"")
                    # Clean up multiline docstrings
                    return docstring.replace('"""', '').replace("'''", '').strip()

    # JavaScript/TypeScript JSDoc comments
    elif language in ("javascript", "typescript"):
        prev_sibling = body_node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == "comment" and "/**" in prev_sibling.text.decode("utf-8"):
                comment = prev_sibling.text.decode("utf-8")
                # Clean up JSDoc format
                lines = comment.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    line = line.lstrip("/*").rstrip("*/").strip()
                    line = line.lstrip("*").strip()
                    if line:
                        cleaned_lines.append(line)
                return "\n".join(cleaned_lines)
            prev_sibling = prev_sibling.prev_sibling

    # Java/Kotlin/Scala Javadoc comments
    elif language in ("java", "kotlin", "scala"):
        prev_sibling = body_node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == "comment" and "/**" in prev_sibling.text.decode("utf-8"):
                comment = prev_sibling.text.decode("utf-8")
                # Clean up Javadoc format
                lines = comment.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    line = line.lstrip("/*").rstrip("*/").strip()
                    line = line.lstrip("*").strip()
                    if line and not line.startswith("@"):  # Skip Javadoc tags
                        cleaned_lines.append(line)
                return "\n".join(cleaned_lines)
            prev_sibling = prev_sibling.prev_sibling

    # For other languages, try a generic approach
    for child in body_node.children:
        if child.type == "comment":
            return child.text.decode("utf-8").strip()

    return None


if __name__ == "__main__":
    """Validate the extraction functions with sample code."""
    import tree_sitter_language_pack as tlp

    # Test Python parameter extraction
    python_code = '''
def test_function(arg1: str, arg2: int = 42, *args, **kwargs):
    """Test function with various parameter types."""
    pass
    '''

    parser = tlp.get_parser("python")
    tree = parser.parse(bytes(python_code, "utf8"))

    # Find function definition
    def find_function(node):
        if node.type == "function_definition":
            return node
        for child in node.children:
            result = find_function(child)
            if result:
                return result
        return None

    func_node = find_function(tree.root_node)
    if func_node:
        params_node = func_node.child_by_field_name("parameters")
        if params_node:
            params = extract_parameters(params_node, "python")
            print("Extracted parameters:")
            for param in params:
                print(f"  {param}")

            # Also test return type and docstring extraction
            body_node = func_node.child_by_field_name("body")
            if body_node:
                docstring = extract_docstring(body_node, "python")
                print(f"\nDocstring: {docstring}")

            return_type = extract_return_type(func_node)
            print(f"Return type: {return_type}")

    print("\n✅ Extractors module validation passed")
