# azure-doc-processing

**azure-doc-processing** is a Python library designed to simplify and
standardize the use of common Azure services in document-processing
workflows.\
It reduces repeated boilerplate code across projects and provides a
clean, consistent, DRY development experience.

The library offers convenient wrappers and utilities around Azure SDK
components, focusing primarily on document processing.

------------------------------------------------------------------------

## Features

### Supported Azure Services

| Service                            | Module                                          |
|------------------------------------|-------------------------------------------------|
| **Azure Storage (Blob Storage)**   | `azure_doc_processing.blob_storage`             |
| **Azure Document Intelligence**    | `azure_doc_processing.document_intelligence`    |
| **Azure Key Vault**                | `azure_doc_processing.keyvault`                 |
| **Azure OpenAI**                   | `azure_doc_processing.openai_service`           |
| **Azure Storage (Table Storage)**  | `azure_doc_processing.table_storage`            |

### Additional Functionality

#### Standardized Logger

``` python
from azure_doc_processing.logger import Logger

logger = Logger(__name__)
```

#### Document Utilities

Generic helper functions for document-processing tasks are available
under:

``` python
import azure_doc_processing.utils as utils
```

------------------------------------------------------------------------

## Installation

Once published to PyPI:

``` bash
pip install azure-doc-processing
```

Or with Poetry:

``` bash
poetry add azure-doc-processing
```

------------------------------------------------------------------------

## Quick Example
Using key-based authentication:
``` python
from azure_doc_processing.blob_storage import AzureDataLake
from azure_doc_processing.logger import Logger

logger = Logger(__name__)

datalake = AzureDataLake(
    os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
    os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
)

blob_files = datalake.list_blob_files(container="my-container",prefix="my-prefix/")
logger.info(f"Found {len(blob_files)} in container")
```

Using DefaultAzureCredential authentication:
``` python
from azure_doc_processing.blob_storage import AzureDataLake
from azure_doc_processing.logger import Logger

logger = Logger(__name__)

datalake = AzureDataLake(
    os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
)

blob_files = datalake.list_blob_files(container="my-container",prefix="my-prefix/")
logger.info(f"Found {len(blob_files)} in container")
```

------------------------------------------------------------------------

## Development

This repository uses:

-   **pyenv** for Python version management\
-   **Poetry 1.8.5** for dependency & environment management\
-   **poethepoet** for task automation\
-   **pytest** for testing

### Setup

Install all dependencies:

``` bash
poetry install
```

### Development Dependencies

Add development-only packages with:

``` bash
poetry add <package> --group dev
```

### Available Tasks

Using `poethepoet`:

  Command        Description
  -------------- ---------------------------------------
  `poe test`     Run the full test suite
  `poe format`   Format code (autoflake, black, isort)

Before committing changes, run:

``` bash
poe format
poe test
```
------------------------------------------------------------------------

## Publishing the Package

This project includes automated publishing scripts.

### Prerequisites

Make sure you have:

- An API token for **TestPyPI** and/or **PyPI**
- A valid `~/.pypirc` file, for example:

  ```ini
  [testpypi]
  username = __token__
  password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

  [pypi]
  username = __token__
  password = pypi-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
  ```

### Publish to TestPyPI (dry run)
Use this when testing new releases.
This publishes the package under a temporary test name and performs an install + import smoke test.

`poe publish-testpypi`

### Publish to PyPi (real release)
Use this when releasing an official version.
Make sure you’ve bumped the version in `pyproject.toml`.

`poe publish-pypi`

Publishing will fail if the version already exists on PyPI.
Real releases should use unique, semantic version increments.


------------------------------------------------------------------------

## License

This project is licensed under the **Apache License 2.0**.\
See the `LICENSE` and `NOTICE` files for details.

------------------------------------------------------------------------

## Contributing

Contributions are welcome!\
Please open an issue or submit a pull request via GitHub.

------------------------------------------------------------------------

## Acknowledgements

Maintained by Verdel Digitaal Partner
