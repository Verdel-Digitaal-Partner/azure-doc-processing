import os

import pandas as pd
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (AnalyzeDocumentRequest,
                                                  AnalyzeResult)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from pypdf import PdfReader, PdfWriter

from azure_doc_processing.blob_storage import AzureDataLake
from azure_doc_processing.logger import Logger

logger = Logger(__name__)


class DocumentIntelligence:

    def __init__(self, endpoint: str, key: str = None):
        self.client = self.get_client(endpoint, key)

    def get_client(self, endpoint: str, key: str = None) -> DocumentIntelligenceClient:
        """
        Retrieve the Azure Document Intelligence Client

        Args
            endpoint: Azure Documment Intelligence endpoint to connect to
            key: (optional) key used to connect to the client, we use the default azure credential when not provided

        Returns
            client: Azure Document Intelligence Client
        """
        if key:
            credential = AzureKeyCredential(key)
        else:
            credential = DefaultAzureCredential()

        client = DocumentIntelligenceClient(endpoint=endpoint, credential=credential)

        return client

    def analyze_doc(
        self,
        model_id: str,
        doc_url: str = None,
        doc_bytes: bytes = None,
        features: list = [],
    ) -> AnalyzeResult | None:
        """
        Analyze a document using document intelligence

        Args
            model_id: the id of the model we use to analyze the document, check https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/model-overview to see all available models.
            doc_url: url in blob account with the document to analyze
            doc_bytes: bytes of the document to analyze
            features: add-on capabalities of the model, check https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/add-on-capabilities for details

        Returns
            result: result of the document intelligence model
        """
        if doc_url is None and doc_bytes is None:
            logger.info(
                "No valid document provided. Either url_source or bytes_source must be specified."
            )
            result = None
        elif doc_url is not None and doc_bytes is not None:
            logger.info(
                "Both url and bytes provided. Either url_source or bytes_source must be specified, not both"
            )
            result = None
        else:
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                body=AnalyzeDocumentRequest(
                    url_source=doc_url,
                    bytes_source=doc_bytes,
                ),
                features=features,
                content_type="application/json",
            )

            result: AnalyzeResult = poller.result()

        return result

    def process_key_value_pairs(self, result: AnalyzeResult) -> dict:
        """
        Process the result from the prebuilt-document model to a usable object

        Args
            result: result of the prebuilt-document model

        Returns
            processed_result: result from the model as a dictionary with string values in the keys and values
        """
        processed_result = {}
        # save the key value pairs if they are valid
        for kv_pair in result.get("keyValuePairs", []):
            if kv_pair.key and kv_pair.value:
                processed_result[kv_pair.key.content] = kv_pair.value.content
            elif kv_pair.key:
                processed_result[kv_pair.key.content] = None

        return processed_result

    def process_tables(self, result: AnalyzeResult) -> list[pd.DataFrame]:
        """
        Process the tables from the prebuilt-document model to a usable object
        We ignore row span and column span, because csv format does not support spans > 1.

        Args
            result: result of the prebuilt-document model

        Returns
            tables_as_dfs: the tables in the result transformed to pandas dataframes
        """
        tables_as_dfs = []
        for table in result.get("tables", []):
            n_rows, n_cols = table["rowCount"], table["columnCount"]

            # Allocate an empty matrix for the raw strings
            matrix = [["" for _ in range(n_cols)] for _ in range(n_rows)]

            # Copy every cell’s text into the right spot
            for cell in table["cells"]:
                matrix[cell["rowIndex"]][cell["columnIndex"]] = cell["content"]

            # Split header & body and build the DataFrame
            header, *body = matrix
            df = pd.DataFrame(body, columns=header)

            tables_as_dfs.append(df)
        return tables_as_dfs


def fix_pdf_files(
    datalake: AzureDataLake,
    pdf_files: list[str],
    container: str,
    tmp_dir: str = "tmp",
    tmp_cleanup: bool = False,
) -> list[str]:
    """
    Fix PDF files to prevent 'The file is corrupted or format is unsupported' errors
    from Document Intelligence by repairing their xref tables and reuploading them with content-type.

    Args:
        datalake: AzureDataLake client to read and write the PDF files to and from blob storage.
        pdf_files: List of PDF files to fix.
        container: name of container where the files are stored
        tmp_dir: directory to temporary store the files
        tmp_cleanup: boolean indicating to clean up the temporary files (True) or not (False)

    Returns:
        fixed_files: List with PDF files ready for processing.
    """
    fixed_files = []

    for file in pdf_files:
        try:
            pdf_blob = datalake.read_from_blob(container="emails", blob=file)

            temp_input_path = os.path.join(tmp_dir, os.path.basename(file))
            temp_output_path = os.path.join(tmp_dir, f"fixed_{os.path.basename(file)}")

            with open(temp_input_path, "wb") as f:
                f.write(pdf_blob.read())

            reader = PdfReader(temp_input_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            with open(temp_output_path, "wb") as temp_output_file:
                writer.write(temp_output_file)

            blob_name = file.replace("/attachments", "")
            datalake.write_to_blob(
                container=container,
                blob=blob_name,
                filename=temp_output_path,
                content_type="application/pdf",
            )

            fixed_files.append(blob_name)

            if tmp_cleanup:
                os.remove(temp_input_path)
                os.remove(temp_output_path)
                logger.debug(f"Removed temporary files for file '{file}'")

        except Exception as e:
            logger.error(f"Error repairing PDF {file}: {e}")

    return fixed_files
