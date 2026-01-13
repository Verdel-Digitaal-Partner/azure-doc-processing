from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
from azure.core.exceptions import AzureError, ResourceExistsError
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential

from azure_doc_processing.logger import Logger

logger = Logger(__name__)


class AzureTableStorage:
    """
    Azure Table Storage client to store and manage entities in Azure Storage Tables
    """

    def __init__(
        self, account_name: str, account_key: str = None, sas_token: str = None
    ) -> None:
        """
        Initialize the Azure Table Storage client

        Args:
            account_name: name of the Azure Storage account
            account_key: access key for the storage account (optional, uses DefaultAzureCredential if not provided)
            sas_token: SAS token for the storage account (optional)
        """
        self.account_name = account_name
        self.account_key = account_key
        self.sas_token = sas_token
        self.get_table_service_client()

    def get_table_service_client(self):
        """
        Create and configure the Table Service Client
        """
        try:
            if self.account_key:
                credential = AzureNamedKeyCredential(self.account_name, self.account_key)
                self.client = TableServiceClient(
                    endpoint=f"https://{self.account_name}.table.core.windows.net",
                    credential=credential,
                )
            elif self.sas_token:
                credential = AzureSasCredential(self.sas_token)
                self.client = TableServiceClient(
                    endpoint=f"https://{self.account_name}.table.core.windows.net",
                    credential=credential,
                )
            else:
                self.client = TableServiceClient(
                    endpoint=f"https://{self.account_name}.table.core.windows.net",
                    credential=DefaultAzureCredential(),
                )
            logger.debug("Configured table service client")
        except AzureError as e:
            logger.error(f"Failed to connect to Table Service: {e}")
            raise

    def create_table(self, table_name: str) -> None:
        """
        Create a new table in Azure Storage

        Args:
            table_name: name of the table to create

        Raises:
            ResourceExistsError: if table already exists
            AzureError: if table creation fails
        """
        try:
            self.client.create_table(table_name)
            logger.info(f"Successfully created table '{table_name}'")
        except ResourceExistsError:
            logger.error(f"Table '{table_name}' already exists")
            raise
        except AzureError as e:
            logger.error(f"Failed to create table '{table_name}': {e}")
            raise

    def delete_table(self, table_name: str) -> None:
        """
        Delete a table from Azure Storage

        Args:
            table_name: name of the table to delete
        """
        try:
            self.client.delete_table(table_name)
            logger.info(f"Successfully deleted table '{table_name}'")
        except AzureError as e:
            logger.error(f"Failed to delete table '{table_name}': {e}")
            raise

    def store_entity_in_table(
        self,
        table_name: str,
        entity: dict,
        partition_key: str = None,
        row_key: str = None,
    ) -> None:
        """
        Store an entity in an Azure Storage Table

        Args:
            table_name: name of the table to store the entity in
            entity: dictionary representing the entity to store
            partition_key: partition key for the entity (if not in entity dict)
            row_key: row key for the entity (if not in entity dict)

        Note:
            - If partition_key and row_key are provided as parameters, they will override
              any PartitionKey and RowKey values in the entity dictionary
            - If not provided, the entity dict must contain 'PartitionKey' and 'RowKey' keys
            - Uses upsert operation (insert or update if exists)
            - Table must exist before calling this method
        """
        try:
            # Create table client
            table_client = self.client.get_table_client(table_name=table_name)

            # Prepare entity with required keys
            table_entity = entity.copy()

            if partition_key:
                table_entity["PartitionKey"] = str(partition_key)
            if row_key:
                table_entity["RowKey"] = str(row_key)

            # Validate that PartitionKey and RowKey are present
            if "PartitionKey" not in table_entity or "RowKey" not in table_entity:
                raise ValueError("Entity must have 'PartitionKey' and 'RowKey'")

            # Upsert the entity (insert or update if exists)
            table_client.upsert_entity(entity=table_entity)
            logger.info(
                f"Successfully stored entity in table '{table_name}' "
                f"(PartitionKey: {table_entity['PartitionKey']}, RowKey: {table_entity['RowKey']})"
            )

        except ValueError as e:
            logger.error(f"Invalid entity data: {e}")
            raise
        except AzureError as e:
            logger.error(f"Failed to store entity in table '{table_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing entity in table '{table_name}': {e}")
            raise

    def store_entities_in_table(
        self,
        table_name: str,
        entities: list[dict],
        partition_key_field: str = "PartitionKey",
        row_key_field: str = "RowKey",
    ) -> dict:
        """
        Store multiple entities in an Azure Storage Table

        Args:
            table_name: name of the table to store entities in
            entities: list of dictionaries representing entities to store
            partition_key_field: name of the field to use as PartitionKey (default: 'PartitionKey')
            row_key_field: name of the field to use as RowKey (default: 'RowKey')

        Returns:
            dict with 'success_count' and 'error_count'

        Note:
            Each entity dict must contain the specified partition_key_field and row_key_field.
            Table must exist before calling this method.
        """
        success_count = 0
        error_count = 0

        for entity in entities:
            try:
                # Prepare entity with field mapping
                entity_to_store = entity.copy()

                # Extract partition and row keys from custom fields if specified
                partition_key = None
                row_key = None

                if partition_key_field != "PartitionKey" and partition_key_field in entity:
                    partition_key = entity[partition_key_field]
                elif partition_key_field == "PartitionKey" and "PartitionKey" in entity:
                    partition_key = entity["PartitionKey"]

                if row_key_field != "RowKey" and row_key_field in entity:
                    row_key = entity[row_key_field]
                elif row_key_field == "RowKey" and "RowKey" in entity:
                    row_key = entity["RowKey"]

                # Validate keys are present
                if partition_key is None:
                    raise ValueError(f"Entity missing field '{partition_key_field}'")
                if row_key is None:
                    raise ValueError(f"Entity missing field '{row_key_field}'")

                # Use the single entity store function
                self.store_entity_in_table(
                    table_name=table_name,
                    entity=entity_to_store,
                    partition_key=partition_key,
                    row_key=row_key,
                )
                success_count += 1

            except (ValueError, AzureError) as e:
                error_count += 1
                logger.error(
                    f"Failed to store entity (PartitionKey: {entity.get(partition_key_field)}, "
                    f"RowKey: {entity.get(row_key_field)}): {e}"
                )

        logger.info(
            f"Stored {success_count} entities in table '{table_name}' "
            f"({error_count} errors)"
        )

        return {"success_count": success_count, "error_count": error_count}

    def query_entities(
        self,
        table_name: str,
        filter_query: str = None,
        select: list[str] = None,
    ) -> list[dict]:
        """
        Query entities from an Azure Storage Table

        Args:
            table_name: name of the table to query
            filter_query: OData filter query string (e.g., "PartitionKey eq 'mypartition'")
            select: list of properties to return (returns all if not specified)

        Returns:
            list of entities matching the query
        """
        try:
            table_client = self.client.get_table_client(table_name=table_name)

            entities = table_client.query_entities(query_filter=filter_query, select=select)

            result = list(entities)
            logger.debug(f"Retrieved {len(result)} entities from table '{table_name}'")
            return result

        except AzureError as e:
            logger.error(f"Failed to query entities from table '{table_name}': {e}")
            raise

    def delete_entity(
        self,
        table_name: str,
        partition_key: str,
        row_key: str,
    ) -> None:
        """
        Delete an entity from an Azure Storage Table

        Args:
            table_name: name of the table
            partition_key: partition key of the entity to delete
            row_key: row key of the entity to delete
        """
        try:
            table_client = self.client.get_table_client(table_name=table_name)
            table_client.delete_entity(partition_key=partition_key, row_key=row_key)
            logger.info(
                f"Successfully deleted entity from table '{table_name}' "
                f"(PartitionKey: {partition_key}, RowKey: {row_key})"
            )
        except AzureError as e:
            logger.error(
                f"Failed to delete entity from table '{table_name}' "
                f"(PartitionKey: {partition_key}, RowKey: {row_key}): {e}"
            )
            raise

    def list_tables(self) -> list[str]:
        """
        List all tables in the storage account

        Returns:
            list of table names
        """
        try:
            tables = self.client.list_tables()
            table_names = [table.name for table in tables]
            logger.debug(f"Found {len(table_names)} tables in storage account")
            return table_names
        except AzureError as e:
            logger.error(f"Failed to list tables: {e}")
            raise
