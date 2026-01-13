import io
import json
import os
from datetime import datetime

import pandas as pd
import pytz
from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
from azure.core.exceptions import AzureError, ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from azure_doc_processing.logger import Logger

logger = Logger(__name__)


class AzureDataLake:
    """
    Azure blob storage client to read and write files from and to blob
    """

    def __init__(
        self, account_name: str, account_key: str = None, sas_token: str = None
    ) -> None:
        """
        Initialize the Azure Blob Storage client

        Args:
            account_name: name of the Azure Storage account
            account_key: access key for the storage account (optional, uses DefaultAzureCredential if not provided)
            sas_token: SAS token for the storage account (optional)
        """
        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token
        self.get_blob_service_client()

    def get_blob_service_client(self):
        try:
            if self.account_key:
                credential = AzureNamedKeyCredential(self.account_name, self.account_key)
                self.client = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=credential,
                )
            elif self.sas_token:
                credential = AzureSasCredential(self.sas_token)
                self.client = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=credential,
                )
            else:
                self.client = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=DefaultAzureCredential(),
                )
            logger.debug("Configured blob service client")
        except AzureError as e:
            logger.error(f"Failed to connect to Blob Service: {e}")

    def read_from_blob(self, container: str, blob: str) -> io.BytesIO:
        """
        Read a file from disk blob storage into memory

        Args
            container: name of container to read from
            blob: name of blob to read from

        Returns
            data_bytes: In-memory binary stream of blob
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob)
        blob_data = blob_client.download_blob()
        data_bytes = io.BytesIO(blob_data.readall())
        return data_bytes

    def write_to_blob(
        self,
        container: str,
        blob: str,
        filename: str = None,
        data_stream: io.BytesIO = None,
        overwrite: bool = True,
        content_type: str = None,
    ) -> None:
        """
        Write a file from disk or from a data stream to blob storage

        Args
            container: name of container to write to
            blob: name of blob to write to
            filename: full path of file on disk to write to blob
            data_stream: data to write to blob (only relevant if filename not provided)
            overwrite: allow overwriting of blob
            content type to add when uploading file
        """
        blob_client = self.client.get_blob_client(container=container, blob=blob)

        if content_type:
            content_settings = ContentSettings(content_type=content_type)
        else:
            content_settings = ContentSettings()

        try:
            if filename:
                with open(filename, "rb") as data:
                    blob_client.upload_blob(
                        data, overwrite=overwrite, content_settings=content_settings
                    )
                logger.debug(f"Successfully stored file {container}:{blob}")
            elif data_stream:
                blob_client.upload_blob(
                    data_stream, overwrite=overwrite, content_settings=content_settings
                )
                logger.debug(f"Successfully stored file {container}:{blob}")
            else:
                logger.warning("Please provide a file or data to upload")
        except AzureError as e:
            logger.error(f"Failed to upload file to Blob Service: {e}")

    def list_blob_files(
        self,
        container: str,
        prefix: str = "",
        suffix: str = "",
        rem_suffix: str = None,
        start_date: datetime = None,
    ) -> list:
        """
        List all files in a blob container

        Args
            container: name of container to list
            prefix: set filter on prefix of blob names in list
            suffix: filter for blob names with specified suffix
            rem_suffix: remove blob names with specified suffix
            start_date: only return blobs whose creation_time > start_date

        Returns
            blob_names_filt: (filtered) names of blobs in the container
        """
        container_client = self.client.get_container_client(container)

        all_blobs = list(container_client.list_blobs(name_starts_with=prefix))
        logger.debug(f"Found {len(all_blobs)} blobs in {container} with prefix {prefix}")

        if start_date:
            if start_date.tzinfo is None or start_date.tzinfo.utcoffset(start_date) is None:
                start_date = start_date.replace(tzinfo=pytz.utc)
                logger.debug(
                    "Localized start_date to UTC because we need a offset-aware datetime"
                )

            all_blobs = [
                b for b in all_blobs if b.creation_time and b.creation_time > start_date
            ]
            logger.debug(
                f"Found {len(all_blobs)} blobs in {container} with startdate after {start_date.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        filtered_blobs = [b for b in all_blobs if b.name.endswith(suffix)]
        logger.debug(
            f"Found {len(filtered_blobs)} blobs in {container} with suffix {suffix}"
        )

        if rem_suffix:
            filtered_blobs = [b for b in filtered_blobs if not b.name.endswith(rem_suffix)]
            logger.debug(
                f"Found {len(filtered_blobs)} blobs in {container} with suffix removed {rem_suffix}"
            )

        filtered_blob_names = [b.name for b in filtered_blobs]
        return filtered_blob_names

    def rename_blob(self, container: str, blob: str, new_blob: str) -> None:
        """
        Rename a blob.
        We rename the blob by copying it to the new blob, if this was successful we delete the blob.

        Args
            container: name of container to read from
            blob: name of blob to rename
            new_blob: new name for blob
        """
        blob_client = self.client.get_blob_client(container, blob)
        new_blob_client = self.client.get_blob_client(container, new_blob)

        try:
            properties = blob_client.get_blob_properties()
            source_md5 = properties.get("content_settings", {}).get("content_md5", "source")
            data = self.read_from_blob(container, blob)
            result = new_blob_client.upload_blob(data, overwrite=False)
        except ResourceExistsError:
            logger.error(
                f"Failed to copy file because the chosen name '{new_blob}' has an existing resource. Please choose a different name."
            )
            result = {}
        except AzureError as e:
            logger.error(f"Failed to copy file from url {blob_client.url}: {e}")
            result = {}

        if result.get("content_md5", "target") == source_md5:
            try:
                blob_client.delete_blob()
                logger.debug(
                    f"Successfully renamed file {blob} to {new_blob} in {container}"
                )
            except AzureError as e:
                logger.error(f"Failed to deleted copied file {blob} from {container}: {e}")
        else:
            logger.error(f"Failed to delete {blob} because the copy failed: {result}")

    def change_blob_content_type(self, container: str, blob: str, content_type: str) -> None:
        """
        Change the content type of a blob in Azure Blob Storage.

        Args
            container: name of the container where the blob is located
            blob: name of the blob whose content type needs to be changed
            content_type: the new content type to set for the blob

        Returns
            None
        """
        try:
            blob_client = self.client.get_blob_client(container=container, blob=blob)

            properties = blob_client.get_blob_properties()
            current_content_settings = properties["content_settings"]

            new_content_settings = ContentSettings(
                content_type=content_type,
                content_encoding=current_content_settings.get("content_encoding"),
                cache_control=current_content_settings.get("cache_control"),
                content_language=current_content_settings.get("content_language"),
                content_disposition=current_content_settings.get("content_disposition"),
            )

            blob_client.set_http_headers(content_settings=new_content_settings)
            logger.debug(
                f"Content type for blob '{blob}' in container '{container}' updated to '{content_type}'"
            )
        except AzureError as e:
            logger.error(
                f"Failed to update content type for blob '{blob}' in container '{container}': {e}"
            )

    def store_json(
        self,
        container: str,
        blob_name: str,
        obj_to_json: dict | list,
    ):
        """
        Stores a dict as json file in blob storage

        Args
            datalake: azure blob storage client
            container: name of the container where the blob needs to be stored
            blob_name: name of blob to store
            obj_to_json: dictionary or list to store as json file
        """
        try:
            buffer = io.BytesIO()
            buffer.write(json.dumps(obj_to_json).encode("utf-8"))
            buffer.seek(0)

            self.write_to_blob(
                container=container,
                blob=blob_name,
                data_stream=buffer,
                content_type="application/json",
            )
            logger.info(f"Successfully stored file '{blob_name}' in blob storage")

        except Exception as e:
            logger.error(f"Failed to store file '{blob_name}' in blob storage")

    def write_dataframe_to_blob(
        self,
        container: str,
        blob_name: str,
        df: pd.DataFrame,
        overwrite: bool = True,
        excel_sheet_name: str = "Sheet1",
        parquet_engine: str = "pyarrow",
        **kwargs,
    ) -> None:
        """
        Serialise *df* to an in-memory buffer (Excel or Parquet, decided by
        blob_name’s extension) and upload it to Azure Blob Storage.

        Supported extensions
        --------------------
        • .xlsx / .xls  → Excel (XLSX writer)
        • .parquet / .pq → Parquet (pyarrow or fastparquet)

        Args
            container: Target container name.
            blob_name: Target blob name – must include one of the supported extensions.
            df: The dataframe to upload.
            overwrite: bool, Allow overwriting an existing blob.
            excel_sheet_name: Sheet name used when writing Excel.
            parquet_engine: Engine passed to ``DataFrame.to_parquet``.
        """
        ext = os.path.splitext(blob_name)[1].lower()

        buffer = io.BytesIO()
        content_type = "application/octet-stream"

        try:
            if ext in [".xlsx", ".xls"]:
                # Excel
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(
                        writer,
                        sheet_name=excel_sheet_name,
                        index=False,
                        **kwargs,
                    )
            elif ext in [".parquet", ".pq"]:
                # Parquet
                df.to_parquet(buffer, engine=parquet_engine, index=False, **kwargs)
            else:
                raise ValueError(
                    f"Unsupported file extension '{ext}'. "
                    "Use .xlsx, .xls, .parquet or .pq."
                )

            buffer.seek(0)  # rewind before upload

            self.write_to_blob(
                container=container,
                blob=blob_name,
                data_stream=buffer,
                overwrite=overwrite,
                content_type=content_type,
            )
            logger.info(f"DataFrame written to {container}:{blob_name} as {ext[1:].upper()}")

        except Exception as e:
            logger.error(f"Failed to write DataFrame to {container}:{blob_name}: {e}")
