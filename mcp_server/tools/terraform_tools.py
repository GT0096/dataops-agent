import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from mcp_server.models.tool_schemas import (
    ParseTerraformPlanInput, ParseTerraformPlanOutput, ResourceChange,
    DetectInfraDriftInput, DetectInfraDriftOutput, DriftItem,
    TerraformAction
)
from mcp_server.utils.azure_client import azure_clients
from mcp_server.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class TerraformTools:
    """Terraform infrastructure reasoning tools"""

    def __init__(self):
        self.resource_client = azure_clients.get_resource_client()
        self.plans_dir = settings.terraform_plans_dir

    def parse_terraform_plan(self, input_data: ParseTerraformPlanInput) -> ParseTerraformPlanOutput:
        """
        Parse Terraform plan JSON and categorize resource changes.

        Implementation:
        1. Load plan JSON file
        2. Extract resource_changes array
        3. Categorize by action type (create, update, delete)
        4. Identify high-risk changes (deletions, destructive updates)
        5. Extract before/after values for updates
        """
        try:
            logger.info(f"Parsing Terraform plan: {input_data.plan_path}")

            # Load plan file
            plan_path = Path(input_data.plan_path)
            if not plan_path.is_absolute():
                plan_path = self.plans_dir / plan_path

            if not plan_path.exists():
                raise FileNotFoundError(f"Plan file not found: {plan_path}")

            with open(plan_path, 'r') as f:
                plan_data = json.load(f)

            # Extract resource changes
            resource_changes = plan_data.get('resource_changes', [])

            created = []
            updated = []
            deleted = []
            high_risk = []

            for change in resource_changes:
                actions = change.get('change', {}).get('actions', [])
                resource_type = change.get('type', '')
                resource_name = change.get('name', '')
                address = change.get('address', '')
                before = change.get('change', {}).get('before', None)
                after = change.get('change', {}).get('after', None)

                # Determine action type
                action_list = [TerraformAction(a) for a in actions if a in TerraformAction._value2member_map_]
                is_destructive = TerraformAction.DELETE in action_list

                resource_change = ResourceChange(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    address=address,
                    actions=action_list,
                    before=before,
                    after=after,
                    is_destructive=is_destructive
                )

                # Categorize
                if TerraformAction.CREATE in action_list and TerraformAction.DELETE not in action_list:
                    created.append(resource_change)
                elif TerraformAction.UPDATE in action_list:
                    updated.append(resource_change)
                    # Check if update is destructive (e.g., changing immutable properties)
                    if self._is_destructive_update(resource_type, before, after):
                        high_risk.append(resource_change)
                elif TerraformAction.DELETE in action_list:
                    deleted.append(resource_change)
                    high_risk.append(resource_change)

            return ParseTerraformPlanOutput(
                plan_path=str(plan_path),
                created_resources=created,
                updated_resources=updated,
                deleted_resources=deleted,
                high_risk_changes=high_risk
            )

        except Exception as e:
            logger.error(f"Error parsing Terraform plan: {str(e)}")
            raise

    def _is_destructive_update(
        self,
        resource_type: str,
        before: Optional[Dict],
        after: Optional[Dict]
    ) -> bool:
        """Check if an update is destructive (requires replacement)"""
        if not before or not after:
            return False

        # Define properties that force replacement for common resource types
        immutable_properties = {
            'azurerm_virtual_machine': ['location', 'vm_size'],
            'azurerm_storage_account': ['location', 'account_tier'],
            'azurerm_virtual_network': ['location', 'address_space'],
            'azurerm_linux_virtual_machine': ['location', 'size'],
        }

        if resource_type in immutable_properties:
            for prop in immutable_properties[resource_type]:
                if before.get(prop) != after.get(prop):
                    return True

        return False

    def detect_infra_drift(self, input_data: DetectInfraDriftInput) -> DetectInfraDriftOutput:
        """
        Detect drift between Terraform plan and actual Azure resources.

        Implementation:
        1. Parse Terraform plan to get expected resources
        2. Query Azure to get actual resources in resource group
        3. Compare and identify:
           - Resources in Azure but not in plan (extra)
           - Resources in plan but not in Azure (missing)
           - Configuration drift (optional, simplified)
        """
        try:
            logger.info(f"Detecting infrastructure drift for RG: {input_data.resource_group_name}")

            drift_items = []

            # Get expected resources from plan
            expected_resources = {}
            if input_data.plan_path:
                plan_result = self.parse_terraform_plan(
                    ParseTerraformPlanInput(plan_path=input_data.plan_path)
                )
                # Build expected resource map
                for resource in (plan_result.created_resources + plan_result.updated_resources):
                    expected_resources[resource.address] = resource

            # Get actual resources from Azure
            actual_resources = list(self.resource_client.resources.list_by_resource_group(
                resource_group_name=input_data.resource_group_name
            ))

            # Build map of actual resources
            actual_resource_map = {
                f"{r.type}/{r.name}": r
                for r in actual_resources
            }

            # Find resources in Azure but not in plan
            if expected_resources:
                for resource_key in actual_resource_map.keys():
                    # Simplified matching (in production, use more robust matching)
                    found_in_plan = False
                    for expected_addr in expected_resources.keys():
                        if resource_key in expected_addr or expected_addr in resource_key:
                            found_in_plan = True
                            break

                    if not found_in_plan:
                        drift_items.append(DriftItem(
                            resource_type=actual_resource_map[resource_key].type,
                            resource_name=actual_resource_map[resource_key].name,
                            drift_type="extra_in_cloud",
                            details=f"Resource exists in Azure but not defined in Terraform plan"
                        ))

            # Find resources in plan but not in Azure
            if expected_resources:
                for expected_addr, expected_resource in expected_resources.items():
                    # Check if exists in actual
                    found_in_azure = False
                    for actual_key in actual_resource_map.keys():
                        if expected_resource.resource_name in actual_key:
                            found_in_azure = True
                            break

                    if not found_in_azure and TerraformAction.CREATE not in expected_resource.actions:
                        drift_items.append(DriftItem(
                            resource_type=expected_resource.resource_type,
                            resource_name=expected_resource.resource_name,
                            drift_type="missing_in_cloud",
                            details=f"Resource defined in Terraform but not found in Azure"
                        ))

            return DetectInfraDriftOutput(
                has_drift=len(drift_items) > 0,
                drift_items=drift_items
            )

        except Exception as e:
            logger.error(f"Error detecting infrastructure drift: {str(e)}")
            raise

    def explain_plan_diff(
        self,
        plan_path: str,
        check_drift: bool = True
    ) -> Dict[str, Any]:
        """
        High-level explanation of Terraform plan with risk analysis.
        This combines parse_terraform_plan and detect_infra_drift
        to provide LLM-friendly summary.
        """
        try:
            logger.info(f"Explaining Terraform plan: {plan_path}")

            # Parse plan
            plan_result = self.parse_terraform_plan(
                ParseTerraformPlanInput(plan_path=plan_path)
            )

            # Check drift if requested
            drift_result = None
            if check_drift:
                try:
                    drift_result = self.detect_infra_drift(
                        DetectInfraDriftInput(
                            resource_group_name=settings.azure_resource_group,
                            plan_path=plan_path
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not check drift: {str(e)}")

            # Generate summary
            summary_parts = []

            if plan_result.created_resources:
                summary_parts.append(
                    f"{len(plan_result.created_resources)} resources will be created"
                )
            if plan_result.updated_resources:
                summary_parts.append(
                    f"{len(plan_result.updated_resources)} resources will be updated"
                )
            if plan_result.deleted_resources:
                summary_parts.append(
                    f"{len(plan_result.deleted_resources)} resources will be DELETED"
                )

            summary = ". ".join(summary_parts) + "."

            # Build risk items
            risk_items = []
            for resource in plan_result.high_risk_changes:
                risk_reason = "Resource will be deleted" if TerraformAction.DELETE in resource.actions else "Destructive update"
                risk_items.append({
                    'resource': f"{resource.resource_type}.{resource.resource_name}",
                    'action': ', '.join([a.value for a in resource.actions]),
                    'risk_reason': risk_reason
                })

            return {
                'plan_path': plan_path,
                'summary': summary,
                'resource_counts': {
                    'created': len(plan_result.created_resources),
                    'updated': len(plan_result.updated_resources),
                    'deleted': len(plan_result.deleted_resources)
                },
                'risk_items': risk_items,
                'has_high_risk': len(risk_items) > 0,
                'drift': drift_result.dict() if drift_result else None
            }

        except Exception as e:
            logger.error(f"Error explaining plan diff: {str(e)}")
            raise
