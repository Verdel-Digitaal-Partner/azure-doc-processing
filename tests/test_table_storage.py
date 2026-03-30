import unittest
from unittest.mock import MagicMock, patch

from azure.core.exceptions import AzureError, ResourceExistsError

from azure_doc_processing.table_storage import AzureTableStorage


class TestAzureTableStorageInit(unittest.TestCase):
    """Unit tests for AzureTableStorage initialization."""

    @patch("azure_doc_processing.table_storage.TableServiceClient")
    @patch("azure_doc_processing.table_storage.AzureNamedKeyCredential")
    def test_init_with_account_key(self, mock_credential, mock_table_service):
        """Should create client with AzureNamedKeyCredential when account_key is provided."""
        ts = AzureTableStorage(account_name="myaccount", account_key="mykey")

        mock_credential.assert_called_once_with("myaccount", "mykey")
        mock_table_service.assert_called_once()
        self.assertIsNotNone(ts.client)

    @patch("azure_doc_processing.table_storage.TableServiceClient")
    @patch("azure_doc_processing.table_storage.AzureSasCredential")
    def test_init_with_sas_token(self, mock_credential, mock_table_service):
        """Should create client with AzureSasCredential when sas_token is provided."""
        ts = AzureTableStorage(account_name="myaccount", sas_token="mysas")

        mock_credential.assert_called_once_with("mysas")
        mock_table_service.assert_called_once()
        self.assertIsNotNone(ts.client)

    @patch("azure_doc_processing.table_storage.TableServiceClient")
    @patch("azure_doc_processing.table_storage.DefaultAzureCredential")
    def test_init_with_default_credential(self, mock_credential, mock_table_service):
        """Should use DefaultAzureCredential when no key or token is provided."""
        ts = AzureTableStorage(account_name="myaccount")

        mock_credential.assert_called_once()
        mock_table_service.assert_called_once()
        self.assertIsNotNone(ts.client)

    @patch("azure_doc_processing.table_storage.TableServiceClient")
    @patch("azure_doc_processing.table_storage.AzureNamedKeyCredential")
    def test_init_azure_error_raises(self, mock_credential, mock_table_service):
        """An AzureError during client creation should be re-raised."""
        mock_table_service.side_effect = AzureError("connection failed")

        with self.assertRaises(AzureError):
            AzureTableStorage(account_name="myaccount", account_key="mykey")


def _make_table_storage():
    """Helper to create an AzureTableStorage with a mocked client."""
    with patch("azure_doc_processing.table_storage.TableServiceClient"):
        with patch("azure_doc_processing.table_storage.AzureNamedKeyCredential"):
            ts = AzureTableStorage(account_name="acct", account_key="key")
    ts.client = MagicMock()
    return ts


class TestAzureTableStorageCreateTable(unittest.TestCase):
    """Unit tests for create_table."""

    def test_create_table_success(self):
        """Should call client.create_table with the table name."""
        ts = _make_table_storage()

        ts.create_table("test-table")

        ts.client.create_table.assert_called_once_with("test-table")

    def test_create_table_already_exists(self):
        """Should raise ResourceExistsError when table already exists."""
        ts = _make_table_storage()
        ts.client.create_table.side_effect = ResourceExistsError("exists")

        with self.assertRaises(ResourceExistsError):
            ts.create_table("test-table")

    def test_create_table_azure_error(self):
        """Should raise AzureError on failure."""
        ts = _make_table_storage()
        ts.client.create_table.side_effect = AzureError("fail")

        with self.assertRaises(AzureError):
            ts.create_table("test-table")


class TestAzureTableStorageDeleteTable(unittest.TestCase):
    """Unit tests for delete_table."""

    def test_delete_table_success(self):
        """Should call client.delete_table with the table name."""
        ts = _make_table_storage()

        ts.delete_table("test-table")

        ts.client.delete_table.assert_called_once_with("test-table")

    def test_delete_table_azure_error(self):
        """Should raise AzureError on failure."""
        ts = _make_table_storage()
        ts.client.delete_table.side_effect = AzureError("fail")

        with self.assertRaises(AzureError):
            ts.delete_table("test-table")


class TestAzureTableStorageStoreEntity(unittest.TestCase):
    """Unit tests for store_entity_in_table."""

    def test_store_entity_with_keys_in_entity(self):
        """Should upsert entity when PartitionKey and RowKey are in the dict."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entity = {"PartitionKey": "pk", "RowKey": "rk", "data": "value"}
        ts.store_entity_in_table("test-table", entity)

        mock_table_client.upsert_entity.assert_called_once()

    def test_store_entity_with_explicit_keys(self):
        """Should override keys when partition_key and row_key are provided."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entity = {"data": "value"}
        ts.store_entity_in_table("test-table", entity, partition_key="pk", row_key="rk")

        call_kwargs = mock_table_client.upsert_entity.call_args
        stored_entity = call_kwargs.kwargs.get("entity") or call_kwargs[1].get("entity")
        self.assertEqual(stored_entity["PartitionKey"], "pk")
        self.assertEqual(stored_entity["RowKey"], "rk")

    def test_store_entity_missing_keys_raises_value_error(self):
        """Should raise ValueError when PartitionKey or RowKey is missing."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        with self.assertRaises(ValueError):
            ts.store_entity_in_table("test-table", {"data": "value"})

    def test_store_entity_azure_error(self):
        """Should raise AzureError when upsert fails."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.upsert_entity.side_effect = AzureError("fail")
        ts.client.get_table_client.return_value = mock_table_client

        with self.assertRaises(AzureError):
            ts.store_entity_in_table(
                "test-table",
                {"PartitionKey": "pk", "RowKey": "rk"},
            )

    def test_store_entity_does_not_mutate_input(self):
        """Should not modify the original entity dictionary."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entity = {"PartitionKey": "pk", "RowKey": "rk", "data": "value"}
        original = entity.copy()
        ts.store_entity_in_table("test-table", entity, partition_key="new_pk")

        self.assertEqual(entity, original)


class TestAzureTableStorageStoreEntities(unittest.TestCase):
    """Unit tests for store_entities_in_table."""

    def test_store_entities_success(self):
        """Should return correct success_count for valid entities."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entities = [
            {"PartitionKey": "pk1", "RowKey": "rk1", "data": "a"},
            {"PartitionKey": "pk2", "RowKey": "rk2", "data": "b"},
        ]

        result = ts.store_entities_in_table("test-table", entities)

        self.assertEqual(result["success_count"], 2)
        self.assertEqual(result["error_count"], 0)

    def test_store_entities_with_errors(self):
        """Should track error_count for entities that fail."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.upsert_entity.side_effect = [None, AzureError("fail")]
        ts.client.get_table_client.return_value = mock_table_client

        entities = [
            {"PartitionKey": "pk1", "RowKey": "rk1"},
            {"PartitionKey": "pk2", "RowKey": "rk2"},
        ]

        result = ts.store_entities_in_table("test-table", entities)

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["error_count"], 1)

    def test_store_entities_custom_key_fields(self):
        """Should map custom fields to PartitionKey and RowKey."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entities = [{"id": "pk1", "name": "rk1", "data": "value"}]

        result = ts.store_entities_in_table(
            "test-table",
            entities,
            partition_key_field="id",
            row_key_field="name",
        )

        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["error_count"], 0)

    def test_store_entities_missing_custom_field(self):
        """Should count as error when custom key field is missing from entity."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        entities = [{"data": "value"}]

        result = ts.store_entities_in_table(
            "test-table",
            entities,
            partition_key_field="missing_field",
            row_key_field="also_missing",
        )

        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["error_count"], 1)


class TestAzureTableStorageQueryEntities(unittest.TestCase):
    """Unit tests for query_entities."""

    def test_query_entities_success(self):
        """Should return a list of entities from the table."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = iter(
            [{"PartitionKey": "pk", "RowKey": "rk", "data": "value"}]
        )
        ts.client.get_table_client.return_value = mock_table_client

        result = ts.query_entities("test-table", filter_query="PartitionKey eq 'pk'")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["data"], "value")

    def test_query_entities_with_select(self):
        """Should pass select parameter to query_entities."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.query_entities.return_value = iter([])
        ts.client.get_table_client.return_value = mock_table_client

        ts.query_entities("test-table", select=["PartitionKey", "data"])

        mock_table_client.query_entities.assert_called_once_with(
            query_filter=None, select=["PartitionKey", "data"]
        )

    def test_query_entities_azure_error(self):
        """Should raise AzureError on failure."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.query_entities.side_effect = AzureError("fail")
        ts.client.get_table_client.return_value = mock_table_client

        with self.assertRaises(AzureError):
            ts.query_entities("test-table")


class TestAzureTableStorageDeleteEntity(unittest.TestCase):
    """Unit tests for delete_entity."""

    def test_delete_entity_success(self):
        """Should call table_client.delete_entity with correct keys."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        ts.client.get_table_client.return_value = mock_table_client

        ts.delete_entity("test-table", "pk", "rk")

        mock_table_client.delete_entity.assert_called_once_with(
            partition_key="pk", row_key="rk"
        )

    def test_delete_entity_azure_error(self):
        """Should raise AzureError on failure."""
        ts = _make_table_storage()
        mock_table_client = MagicMock()
        mock_table_client.delete_entity.side_effect = AzureError("fail")
        ts.client.get_table_client.return_value = mock_table_client

        with self.assertRaises(AzureError):
            ts.delete_entity("test-table", "pk", "rk")


class TestAzureTableStorageListTables(unittest.TestCase):
    """Unit tests for list_tables."""

    def test_list_tables_success(self):
        """Should return a list of table names."""
        ts = _make_table_storage()
        mock_table1 = MagicMock()
        mock_table1.name = "table1"
        mock_table2 = MagicMock()
        mock_table2.name = "table2"
        ts.client.list_tables.return_value = [mock_table1, mock_table2]

        result = ts.list_tables()

        self.assertEqual(result, ["table1", "table2"])

    def test_list_tables_empty(self):
        """Should return empty list when no tables exist."""
        ts = _make_table_storage()
        ts.client.list_tables.return_value = []

        result = ts.list_tables()

        self.assertEqual(result, [])

    def test_list_tables_azure_error(self):
        """Should raise AzureError on failure."""
        ts = _make_table_storage()
        ts.client.list_tables.side_effect = AzureError("fail")

        with self.assertRaises(AzureError):
            ts.list_tables()


if __name__ == "__main__":
    unittest.main()
