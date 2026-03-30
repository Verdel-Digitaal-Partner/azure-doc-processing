import io
import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytz
from azure.core.exceptions import AzureError, ResourceExistsError

from azure_doc_processing.blob_storage import AzureDataLake


class TestAzureDataLakeInit(unittest.TestCase):
    """Unit tests for AzureDataLake initialization."""

    @patch("azure_doc_processing.blob_storage.BlobServiceClient")
    @patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential")
    def test_init_with_account_key(self, mock_credential, mock_blob_service):
        """Client should be created with AzureNamedKeyCredential when account_key is provided."""
        dl = AzureDataLake(account_name="myaccount", account_key="mykey")

        mock_credential.assert_called_once_with("myaccount", "mykey")
        mock_blob_service.assert_called_once()
        self.assertIsNotNone(dl.client)

    @patch("azure_doc_processing.blob_storage.BlobServiceClient")
    @patch("azure_doc_processing.blob_storage.AzureSasCredential")
    def test_init_with_sas_token(self, mock_credential, mock_blob_service):
        """Client should be created with AzureSasCredential when sas_token is provided."""
        dl = AzureDataLake(account_name="myaccount", sas_token="mysas")

        mock_credential.assert_called_once_with("mysas")
        mock_blob_service.assert_called_once()
        self.assertIsNotNone(dl.client)

    @patch("azure_doc_processing.blob_storage.BlobServiceClient")
    @patch("azure_doc_processing.blob_storage.DefaultAzureCredential")
    def test_init_with_default_credential(self, mock_credential, mock_blob_service):
        """Client should use DefaultAzureCredential when no key or token is provided."""
        dl = AzureDataLake(account_name="myaccount")

        mock_credential.assert_called_once()
        mock_blob_service.assert_called_once()
        self.assertIsNotNone(dl.client)

    @patch("azure_doc_processing.blob_storage.BlobServiceClient")
    @patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential")
    def test_init_azure_error_is_handled(self, mock_credential, mock_blob_service):
        """An AzureError during client creation should be logged, not raised."""
        mock_blob_service.side_effect = AzureError("connection failed")

        dl = AzureDataLake(account_name="myaccount", account_key="mykey")
        # client attribute is never set because the exception fires first
        self.assertFalse(hasattr(dl, "client"))


class TestAzureDataLakeReadWrite(unittest.TestCase):
    """Unit tests for read/write blob operations."""

    def _make_datalake(self):
        """Helper to create an AzureDataLake with a mocked client."""
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    def test_read_from_blob(self):
        """read_from_blob should return a BytesIO with the blob contents."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        mock_download = MagicMock()
        mock_download.readall.return_value = b"hello world"
        mock_blob_client.download_blob.return_value = mock_download
        dl.client.get_blob_client.return_value = mock_blob_client

        result = dl.read_from_blob("container", "blob.txt")

        self.assertIsInstance(result, io.BytesIO)
        self.assertEqual(result.read(), b"hello world")
        dl.client.get_blob_client.assert_called_once_with(container="container", blob="blob.txt")

    @patch("builtins.open", mock_open(read_data=b"file content"))
    def test_write_to_blob_with_filename(self):
        """write_to_blob should upload from a file when filename is provided."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client

        dl.write_to_blob("container", "blob.txt", filename="/tmp/test.txt")

        mock_blob_client.upload_blob.assert_called_once()

    def test_write_to_blob_with_data_stream(self):
        """write_to_blob should upload from a data stream when provided."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client
        data = io.BytesIO(b"stream data")

        dl.write_to_blob("container", "blob.txt", data_stream=data)

        mock_blob_client.upload_blob.assert_called_once()

    def test_write_to_blob_with_content_type(self):
        """write_to_blob should pass content_type to ContentSettings."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client
        data = io.BytesIO(b"data")

        dl.write_to_blob("container", "blob.json", data_stream=data, content_type="application/json")

        call_kwargs = mock_blob_client.upload_blob.call_args
        content_settings = call_kwargs.kwargs.get("content_settings") or call_kwargs[1].get("content_settings")
        self.assertEqual(content_settings.content_type, "application/json")

    def test_write_to_blob_no_file_or_stream(self):
        """write_to_blob should not upload when neither filename nor data_stream is given."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client

        dl.write_to_blob("container", "blob.txt")

        mock_blob_client.upload_blob.assert_not_called()

    def test_write_to_blob_azure_error(self):
        """write_to_blob should handle AzureError gracefully."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = AzureError("upload failed")
        dl.client.get_blob_client.return_value = mock_blob_client

        # Should not raise
        dl.write_to_blob("container", "blob.txt", data_stream=io.BytesIO(b"data"))


class TestAzureDataLakeListBlobs(unittest.TestCase):
    """Unit tests for list_blob_files."""

    def _make_datalake(self):
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    def _make_blob(self, name, creation_time=None):
        blob = MagicMock()
        blob.name = name
        blob.creation_time = creation_time
        return blob

    def test_list_blob_files_basic(self):
        """Should return all blob names with no filters."""
        dl = self._make_datalake()
        blobs = [self._make_blob("a.txt"), self._make_blob("b.txt")]
        dl.client.get_container_client.return_value.list_blobs.return_value = blobs

        result = dl.list_blob_files("container")

        self.assertEqual(result, ["a.txt", "b.txt"])

    def test_list_blob_files_with_suffix(self):
        """Should filter blobs by suffix."""
        dl = self._make_datalake()
        blobs = [self._make_blob("a.txt"), self._make_blob("b.pdf"), self._make_blob("c.txt")]
        dl.client.get_container_client.return_value.list_blobs.return_value = blobs

        result = dl.list_blob_files("container", suffix=".txt")

        self.assertEqual(result, ["a.txt", "c.txt"])

    def test_list_blob_files_with_rem_suffix(self):
        """Should exclude blobs matching rem_suffix."""
        dl = self._make_datalake()
        blobs = [self._make_blob("a.txt"), self._make_blob("b.txt.bak"), self._make_blob("c.txt")]
        dl.client.get_container_client.return_value.list_blobs.return_value = blobs

        result = dl.list_blob_files("container", rem_suffix=".bak")

        self.assertEqual(result, ["a.txt", "c.txt"])

    def test_list_blob_files_with_start_date(self):
        """Should filter blobs by creation_time > start_date."""
        dl = self._make_datalake()
        old_time = datetime(2024, 1, 1, tzinfo=pytz.utc)
        new_time = datetime(2025, 6, 1, tzinfo=pytz.utc)
        blobs = [
            self._make_blob("old.txt", creation_time=old_time),
            self._make_blob("new.txt", creation_time=new_time),
        ]
        dl.client.get_container_client.return_value.list_blobs.return_value = blobs

        result = dl.list_blob_files(
            "container", start_date=datetime(2025, 1, 1, tzinfo=pytz.utc)
        )

        self.assertEqual(result, ["new.txt"])

    def test_list_blob_files_start_date_naive_gets_localized(self):
        """A naive start_date should be localized to UTC."""
        dl = self._make_datalake()
        new_time = datetime(2025, 6, 1, tzinfo=pytz.utc)
        blobs = [self._make_blob("new.txt", creation_time=new_time)]
        dl.client.get_container_client.return_value.list_blobs.return_value = blobs

        result = dl.list_blob_files("container", start_date=datetime(2025, 1, 1))

        self.assertEqual(result, ["new.txt"])


class TestAzureDataLakeRenameBlob(unittest.TestCase):
    """Unit tests for rename_blob."""

    def _make_datalake(self):
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    def test_rename_blob_success(self):
        """Should copy blob and delete original when md5 matches."""
        dl = self._make_datalake()

        mock_blob_client = MagicMock()
        mock_new_blob_client = MagicMock()

        md5_value = b"abc123"
        mock_blob_client.get_blob_properties.return_value = {
            "content_settings": {"content_md5": md5_value}
        }
        mock_download = MagicMock()
        mock_download.readall.return_value = b"data"
        mock_blob_client.download_blob.return_value = mock_download
        mock_new_blob_client.upload_blob.return_value = {"content_md5": md5_value}

        # get_blob_client is called 3 times: old blob, new blob, then old blob again inside read_from_blob
        dl.client.get_blob_client.side_effect = [mock_blob_client, mock_new_blob_client, mock_blob_client]

        dl.rename_blob("container", "old.txt", "new.txt")

        mock_new_blob_client.upload_blob.assert_called_once()
        mock_blob_client.delete_blob.assert_called_once()

    def test_rename_blob_resource_exists_error(self):
        """Should handle ResourceExistsError when target already exists."""
        dl = self._make_datalake()

        mock_blob_client = MagicMock()
        mock_new_blob_client = MagicMock()
        mock_blob_client.get_blob_properties.return_value = {
            "content_settings": {"content_md5": b"abc"}
        }
        mock_download = MagicMock()
        mock_download.readall.return_value = b"data"
        mock_blob_client.download_blob.return_value = mock_download
        mock_new_blob_client.upload_blob.side_effect = ResourceExistsError("exists")

        # get_blob_client is called 3 times: old blob, new blob, then old blob again inside read_from_blob
        dl.client.get_blob_client.side_effect = [mock_blob_client, mock_new_blob_client, mock_blob_client]

        # Should not raise
        dl.rename_blob("container", "old.txt", "new.txt")
        mock_blob_client.delete_blob.assert_not_called()


class TestAzureDataLakeChangeBlobContentType(unittest.TestCase):
    """Unit tests for change_blob_content_type."""

    def _make_datalake(self):
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    def test_change_blob_content_type(self):
        """Should set new content type via set_http_headers."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        mock_blob_client.get_blob_properties.return_value = {
            "content_settings": {
                "content_encoding": None,
                "cache_control": None,
                "content_language": None,
                "content_disposition": None,
            }
        }
        dl.client.get_blob_client.return_value = mock_blob_client

        dl.change_blob_content_type("container", "blob.txt", "text/plain")

        mock_blob_client.set_http_headers.assert_called_once()

    def test_change_blob_content_type_azure_error(self):
        """Should handle AzureError gracefully."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        mock_blob_client.get_blob_properties.side_effect = AzureError("fail")
        dl.client.get_blob_client.return_value = mock_blob_client

        # Should not raise
        dl.change_blob_content_type("container", "blob.txt", "text/plain")


class TestAzureDataLakeStoreJson(unittest.TestCase):
    """Unit tests for store_json."""

    def _make_datalake(self):
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    def test_store_json_dict(self):
        """Should serialize a dict to JSON and upload it."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client

        dl.store_json("container", "data.json", {"key": "value"})

        mock_blob_client.upload_blob.assert_called_once()

    def test_store_json_list(self):
        """Should serialize a list to JSON and upload it."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client

        dl.store_json("container", "data.json", [1, 2, 3])

        mock_blob_client.upload_blob.assert_called_once()


class TestAzureDataLakeWriteDataframe(unittest.TestCase):
    """Unit tests for write_dataframe_to_blob."""

    def _make_datalake(self):
        with patch("azure_doc_processing.blob_storage.BlobServiceClient"):
            with patch("azure_doc_processing.blob_storage.AzureNamedKeyCredential"):
                dl = AzureDataLake(account_name="acct", account_key="key")
        dl.client = MagicMock()
        return dl

    @patch.object(AzureDataLake, "write_to_blob")
    @patch("pandas.DataFrame.to_parquet")
    def test_write_dataframe_as_parquet(self, mock_to_parquet, mock_write):
        """Should serialize a DataFrame to parquet format and upload."""
        dl = self._make_datalake()
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        dl.write_dataframe_to_blob("container", "data.parquet", df)

        mock_to_parquet.assert_called_once()
        mock_write.assert_called_once()

    def test_write_dataframe_unsupported_extension(self):
        """Should not raise but log an error for unsupported extensions."""
        dl = self._make_datalake()
        mock_blob_client = MagicMock()
        dl.client.get_blob_client.return_value = mock_blob_client
        df = pd.DataFrame({"a": [1]})

        # Should not raise (error is caught and logged)
        dl.write_dataframe_to_blob("container", "data.csv", df)

        mock_blob_client.upload_blob.assert_not_called()


if __name__ == "__main__":
    unittest.main()
