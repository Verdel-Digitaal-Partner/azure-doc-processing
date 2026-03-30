# azure-doc-processing

**azure-doc-processing** is a Python library designed to simplify and
standardize the use of common Azure services in document-processing
workflows.\
It reduces repeated boilerplate code across projects and provides a
clean, consistent, DRY development experience.

The library offers convenient wrappers and utilities around Azure SDK
components, focusing primarily on document processing.
------------------------------------------------------------------------

## Development

This repository uses:

-   **pyenv** for Python version management\
-   **Poetry 1.8.5** for dependency & environment management\
-   **poethepoet** for task automation\
-   **pytest** for testing

Using `poethepoet`:

  Command        Description
  -------------- ---------------------------------------
  `poe test`     Run the full test suite
  `poe format`   Format code (autoflake, black, isort)

While developing python code, follow these principles (in order of importance):
1. Modularity and Separation of Concerns (SoC)
2. Readability and Maintainability
3. Keep It Simple, Stupid (KISS)
4. Don't Repeat Yourself (DRY)

Use the following code style guidelines:
- Use snake_case for variable and function names.
- Use PascalCase for class names.

Always include docstring in your Python functions. Use the following format for docstrings:

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Describe the function's purpose here.

    Args:
        param1 (type): Description of param1.
        param2 (type): Description of param2.

    Returns:
        return_type: Description of the return value.
    """
    # Function implementation here
```