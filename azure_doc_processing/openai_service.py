from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI

from azure_doc_processing.logger import Logger

logger = Logger(__name__)


class OpenAIDeployment:
    """
    Client to interact with a model chat deployment in Azure OpenAI
    """

    def __init__(
        self,
        endpoint: str,
        api_version: str,
        deployment_name: str,
        api_key: str = None,
        model: str = None,
        temperature: float = 0.0,
    ):
        self.client = self.get_client(
            endpoint, api_version, deployment_name, temperature, api_key
        )
        if model:
            self.model = model
        else:
            self.model = deployment_name

    def get_client(
        self,
        endpoint: str,
        api_version: str,
        deployment_name: str,
        temperature: float,
        api_key: str = None,
    ) -> AzureOpenAI:
        """
        Retrieve the Azure OpenAI Client

        Args
            endpoint: Azure OpenAI endpoint to connect to
            api_version: the OpenAI API version to use
            deployment_name: name of the chat deployment in azure open AI
            temperature: temperature used in the prompt result of the LLM
            api_key: key used to connect to the API, we use the default azure credential when not provided

        Returns
            client: Azure Document Intelligence Client
        """
        if api_key:
            logger.info("Connecting using the api key")
            client = AzureChatOpenAI(
                azure_endpoint=endpoint,
                openai_api_key=api_key,
                openai_api_version=api_version,
                deployment_name=deployment_name,
                temperature=temperature,
            )
        else:
            logger.info("No key provided, connecting using the default azure credential")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            client = AzureChatOpenAI(
                openai_api_version=api_version,
                azure_endpoint=endpoint,
                deployment_name=deployment_name,
                azure_ad_token_provider=token_provider,
                temperature=temperature,
            )

        return client
