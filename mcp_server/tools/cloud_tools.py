from typing import List, Dict, Any
from datetime import datetime, timedelta
from mcp_server.utils.azure_client import azure_clients
from mcp_server.models.tool_schemas import (
    ListResourcesByTagInput, ListResourcesByTagOutput, ResourceInfo
)
from mcp_server.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class CloudTools:
    """Azure cloud resource context tools"""

    def __init__(self):
        self.resource_client = azure_clients.get_resource_client()

    def list_resources_by_tag(self, input_data: ListResourcesByTagInput) -> ListResourcesByTagOutput:
        """
        List Azure resources filtered by tag.

        Implementation:
        1. Query all resources (optionally filtered by RG)
        2. Filter by matching tag key and value
        3. Return resource metadata
        """
        try:
            logger.info(f"Listing resources with tag {input_data.tag_key}={input_data.tag_value}")

            # Get resources
            if input_data.resource_group:
                resources = list(self.resource_client.resources.list_by_resource_group(
                    resource_group_name=input_data.resource_group
                ))
            else:
                resources = list(self.resource_client.resources.list())

            # Filter by tag
            matching_resources = []
            for resource in resources:
                if resource.tags and input_data.tag_key in resource.tags:
                    if resource.tags[input_data.tag_key] == input_data.tag_value:
                        matching_resources.append(ResourceInfo(
                            resource_id=resource.id,
                            resource_name=resource.name,
                            resource_type=resource.type,
                            location=resource.location,
                            tags=resource.tags or {}
                        ))

            return ListResourcesByTagOutput(
                resources=matching_resources,
                count=len(matching_resources)
            )

        except Exception as e:
            logger.error(f"Error listing resources by tag: {str(e)}")
            raise

    def get_resource_health(self, resource_id: str) -> Dict[str, Any]:
        """
        Get health status of a specific Azure resource.

        Implementation:
        1. Parse resource ID
        2. Query resource details
        3. Return health metadata
        """
        try:
            logger.info(f"Getting health for resource: {resource_id}")

            # Get resource by ID
            resource = self.resource_client.resources.get_by_id(
                resource_id=resource_id,
                api_version="2021-04-01"  # Generic API version
            )

            # Basic health info
            health_info = {
                'resource_id': resource_id,
                'resource_name': resource.name,
                'resource_type': resource.type,
                'provisioning_state': getattr(resource.properties, 'provisioningState', 'Unknown') if resource.properties else 'Unknown',
                'location': resource.location,
                'status': 'healthy' if getattr(resource.properties, 'provisioningState', '') == 'Succeeded' else 'unknown'
            }

            return health_info

        except Exception as e:
            logger.error(f"Error getting resource health: {str(e)}")
            raise

    def get_recent_resource_changes(
        self,
        resource_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent changes to a resource (simplified version).
        In production, this would use Azure Activity Log or Resource Graph.
        For demo, we return basic change detection.
        """
        try:
            logger.info(f"Getting recent changes for: {resource_id}")

            # Get current resource state
            resource = self.resource_client.resources.get_by_id(
                resource_id=resource_id,
                api_version="2021-04-01"
            )

            # Simplified: check last modified time if available
            changes = []
            if hasattr(resource, 'properties'):
                changes.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'change_type': 'state_check',
                    'details': f"Current provisioning state: {getattr(resource.properties, 'provisioningState', 'Unknown')}"
                })

            # Note: In production, query Azure Activity Log for actual changes:
            # - Tag updates
            # - Property changes
            # - Access policy modifications
            # This requires azure-mgmt-monitor SDK

            return changes

        except Exception as e:
            logger.error(f"Error getting resource changes: {str(e)}")
            raise
