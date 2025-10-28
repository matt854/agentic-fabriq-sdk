"""
Connector registry for plugin discovery and management.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from stevedore import driver, named

from ..exceptions import ConnectorError
from .base import BaseConnector, ConnectorContext


class ConnectorRegistry:
    """Registry for managing connector plugins."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._loaded_connectors: Dict[str, Type[BaseConnector]] = {}

    def load_connector(self, connector_id: str) -> Type[BaseConnector]:
        """
        Load a connector by ID.

        Args:
            connector_id: The connector ID (e.g., 'slack', 'github')

        Returns:
            The connector class

        Raises:
            ConnectorError: If connector cannot be loaded
        """
        if connector_id in self._loaded_connectors:
            return self._loaded_connectors[connector_id]

        try:
            # Load via stevedore
            mgr = driver.DriverManager(
                namespace="af_connector_plugins",
                name=connector_id,
                invoke_on_load=False,
            )
            connector_class = mgr.driver
            
            # Validate connector class
            if not issubclass(connector_class, BaseConnector):
                raise ConnectorError(
                    f"Connector {connector_id} must inherit from BaseConnector"
                )

            self._loaded_connectors[connector_id] = connector_class
            self.logger.info(f"Loaded connector: {connector_id}")
            return connector_class

        except Exception as e:
            self.logger.error(f"Failed to load connector {connector_id}: {e}")
            raise ConnectorError(f"Failed to load connector {connector_id}: {e}")

    def list_available_connectors(self) -> List[str]:
        """
        List all available connector IDs.

        Returns:
            List of connector IDs
        """
        try:
            from stevedore import extension
            mgr = extension.ExtensionManager(
                namespace="af_connector_plugins",
                invoke_on_load=False,
            )
            return [ep.name for ep in mgr.extensions]
        except Exception as e:
            self.logger.error(f"Failed to list connectors: {e}")
            return []

    def get_connector_info(self, connector_id: str) -> Dict[str, Any]:
        """
        Get information about a connector.

        Args:
            connector_id: The connector ID

        Returns:
            Connector information
        """
        try:
            connector_class = self.load_connector(connector_id)
            return {
                "id": connector_id,
                "name": connector_class.__name__,
                "description": connector_class.__doc__ or "No description",
                "version": getattr(connector_class, "__version__", "unknown"),
                "tool_id": getattr(connector_class, "TOOL_ID", None),
                "agent_id": getattr(connector_class, "AGENT_ID", None),
                "required_scopes": getattr(connector_class, "REQUIRED_SCOPES", []),
            }
        except Exception as e:
            return {
                "id": connector_id,
                "error": str(e),
            }

    def create_connector_instance(
        self, connector_id: str, context: ConnectorContext
    ) -> BaseConnector:
        """
        Create a connector instance.

        Args:
            connector_id: The connector ID
            context: Connector context

        Returns:
            Connector instance

        Raises:
            ConnectorError: If connector cannot be created
        """
        try:
            connector_class = self.load_connector(connector_id)
            return connector_class(context)
        except Exception as e:
            self.logger.error(f"Failed to create connector {connector_id}: {e}")
            raise ConnectorError(f"Failed to create connector {connector_id}: {e}")

    def load_multiple_connectors(self, connector_ids: List[str]) -> Dict[str, Type[BaseConnector]]:
        """
        Load multiple connectors.

        Args:
            connector_ids: List of connector IDs

        Returns:
            Dictionary of connector_id -> connector_class
        """
        try:
            mgr = named.NamedExtensionManager(
                namespace="af_connector_plugins",
                names=connector_ids,
                invoke_on_load=False,
            )
            
            result = {}
            for ext in mgr.extensions:
                connector_class = ext.obj
                if not issubclass(connector_class, BaseConnector):
                    self.logger.warning(
                        f"Skipping {ext.name}: not a BaseConnector subclass"
                    )
                    continue
                
                result[ext.name] = connector_class
                self._loaded_connectors[ext.name] = connector_class
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to load connectors {connector_ids}: {e}")
            raise ConnectorError(f"Failed to load connectors: {e}")

    def validate_connector(self, connector_id: str) -> bool:
        """
        Validate a connector.

        Args:
            connector_id: The connector ID

        Returns:
            True if connector is valid, False otherwise
        """
        try:
            connector_class = self.load_connector(connector_id)
            
            # Check required attributes
            if hasattr(connector_class, "TOOL_ID"):
                if not connector_class.TOOL_ID:
                    self.logger.error(f"Connector {connector_id} has empty TOOL_ID")
                    return False
            elif hasattr(connector_class, "AGENT_ID"):
                if not connector_class.AGENT_ID:
                    self.logger.error(f"Connector {connector_id} has empty AGENT_ID")
                    return False
            else:
                self.logger.error(f"Connector {connector_id} missing TOOL_ID or AGENT_ID")
                return False
            
            # Check required methods
            if not hasattr(connector_class, "invoke"):
                self.logger.error(f"Connector {connector_id} missing invoke method")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Connector {connector_id} validation failed: {e}")
            return False

    def get_connector_schema(self, connector_id: str) -> Dict[str, Any]:
        """
        Get the schema for a connector.

        Args:
            connector_id: The connector ID

        Returns:
            Connector schema
        """
        try:
            connector_class = self.load_connector(connector_id)
            
            # Create a dummy context for schema generation
            import logging
            import httpx
            from ..auth.token_cache import TokenManager, VaultClient
            
            dummy_http = httpx.AsyncClient()
            dummy_vault = VaultClient("http://localhost", dummy_http, logging.getLogger())
            dummy_token_manager = TokenManager("default", dummy_vault)
            
            dummy_context = ConnectorContext(
                tenant_id="default",
                user_id="system",
                http=dummy_http,
                token_manager=dummy_token_manager,
                logger=logging.getLogger(),
            )
            
            # Create instance to get schema
            instance = connector_class(dummy_context)
            
            if hasattr(instance, "get_schema"):
                return instance.get_schema()
            else:
                return {
                    "connector_id": connector_id,
                    "methods": [],
                    "description": "Schema not available",
                }
        except Exception as e:
            self.logger.error(f"Failed to get schema for {connector_id}: {e}")
            return {
                "connector_id": connector_id,
                "error": str(e),
            }

    def clear_cache(self):
        """Clear the connector cache."""
        self._loaded_connectors.clear()
        self.logger.info("Connector cache cleared")

    def get_loaded_connectors(self) -> Dict[str, Type[BaseConnector]]:
        """Get all loaded connectors."""
        return self._loaded_connectors.copy()


# Global registry instance
_registry = ConnectorRegistry()


def get_connector_registry() -> ConnectorRegistry:
    """Get the global connector registry."""
    return _registry 