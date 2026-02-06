import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from azure.mgmt.datafactory.models import PipelineRun
from mcp_server.utils.azure_client import azure_clients
from mcp_server.models.tool_schemas import (
    GetPipelineStatusInput, GetPipelineStatusOutput, PipelineRunInfo,
    GetPipelineDependenciesInput, GetPipelineDependenciesOutput,
    GetFailedTasksSummaryInput, GetFailedTasksSummaryOutput, FailedTask,
    PipelineStatus
)
from mcp_server.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class ADFTools:
    """Azure Data Factory tools implementation"""

    def __init__(self):
        self.df_client = azure_clients.get_datafactory_client()
        self.resource_group = settings.azure_resource_group
        self.factory_name = settings.azure_data_factory_name

    def get_pipeline_status(self, input_data: GetPipelineStatusInput) -> GetPipelineStatusOutput:
        """
        Get the current status and recent run history of an ADF pipeline.

        Implementation:
        1. Query pipeline runs from ADF
        2. Sort by start time descending
        3. Extract last run details
        4. Find last successful and failed runs
        5. Return structured status
        """
        try:
            logger.info(f"Fetching status for pipeline: {input_data.pipeline_name}")

            # Calculate time range (last 7 days)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)

            # Query pipeline runs
            filter_params = {
                'last_updated_after': start_time,
                'last_updated_before': end_time
            }

            runs = list(self.df_client.pipeline_runs.query_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                filter_parameters=filter_params
            ).value)

            # Filter for specific pipeline
            pipeline_runs = [
                run for run in runs
                if run.pipeline_name == input_data.pipeline_name
            ]

            # Sort by start time descending
            pipeline_runs.sort(key=lambda x: x.run_start, reverse=True)

            if not pipeline_runs:
                raise ValueError(f"No runs found for pipeline: {input_data.pipeline_name}")

            # Get last run
            last_run = pipeline_runs[0]

            # Find last success and failure
            last_success = next(
                (run for run in pipeline_runs if run.status == "Succeeded"),
                None
            )
            last_failure = next(
                (run for run in pipeline_runs if run.status == "Failed"),
                None
            )

            # Convert to PipelineRunInfo objects
            recent_runs = []
            for run in pipeline_runs[:10]:  # Last 10 runs
                duration = None
                if run.run_start and run.run_end:
                    duration = (run.run_end - run.run_start).total_seconds()

                recent_runs.append(PipelineRunInfo(
                    run_id=run.run_id,
                    pipeline_name=run.pipeline_name,
                    status=PipelineStatus(run.status),
                    start_time=run.run_start,
                    end_time=run.run_end,
                    duration_seconds=duration,
                    error_message=run.message if run.status == "Failed" else None
                ))

            return GetPipelineStatusOutput(
                pipeline_name=input_data.pipeline_name,
                last_run_status=PipelineStatus(last_run.status),
                last_run_start=last_run.run_start,
                last_run_end=last_run.run_end,
                last_success_time=last_success.run_start if last_success else None,
                last_failure_reason=last_failure.message if last_failure else None,
                recent_runs=recent_runs
            )

        except Exception as e:
            logger.error(f"Error fetching pipeline status: {str(e)}")
            raise

    def get_pipeline_dependencies(self, input_data: GetPipelineDependenciesInput) -> GetPipelineDependenciesOutput:
        """
        Analyze pipeline dependencies by parsing pipeline JSON definition.

        Implementation:
        1. Fetch pipeline definition from ADF
        2. Parse activities to find Execute Pipeline activities (upstream)
        3. Parse datasets consumed and produced
        4. Extract linked services used
        5. Query other pipelines to find downstream dependencies
        """
        try:
            logger.info(f"Analyzing dependencies for pipeline: {input_data.pipeline_name}")

            # Get pipeline definition
            pipeline = self.df_client.pipelines.get(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                pipeline_name=input_data.pipeline_name
            )

            upstream_pipelines = []
            datasets_consumed = []
            datasets_produced = []
            linked_services = set()

            # Parse activities
            if hasattr(pipeline, 'activities') and pipeline.activities:
                for activity in pipeline.activities:
                    # Check for Execute Pipeline activities (upstream dependencies)
                    if activity.type == "ExecutePipeline":
                        if hasattr(activity, 'type_properties'):
                            pipeline_ref = activity.type_properties.get('pipeline', {})
                            if 'referenceName' in pipeline_ref:
                                upstream_pipelines.append(pipeline_ref['referenceName'])

                    # Check for Copy activities (datasets)
                    elif activity.type == "Copy":
                        if hasattr(activity, 'type_properties'):
                            # Source dataset
                            if 'source' in activity.type_properties:
                                source = activity.type_properties['source']
                                if 'dataset' in source:
                                    datasets_consumed.append(source['dataset'].get('referenceName', ''))
                            # Sink dataset
                            if 'sink' in activity.type_properties:
                                sink = activity.type_properties['sink']
                                if 'dataset' in sink:
                                    datasets_produced.append(sink['dataset'].get('referenceName', ''))

                    # Extract linked services from activity
                    if hasattr(activity, 'linked_service_name'):
                        if activity.linked_service_name:
                            linked_services.add(activity.linked_service_name.reference_name)

            # Find downstream pipelines (pipelines that execute this one)
            downstream_pipelines = []
            all_pipelines = list(self.df_client.pipelines.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            for other_pipeline in all_pipelines:
                if other_pipeline.name == input_data.pipeline_name:
                    continue

                if hasattr(other_pipeline, 'activities') and other_pipeline.activities:
                    for activity in other_pipeline.activities:
                        if activity.type == "ExecutePipeline":
                            if hasattr(activity, 'type_properties'):
                                pipeline_ref = activity.type_properties.get('pipeline', {})
                                if pipeline_ref.get('referenceName') == input_data.pipeline_name:
                                    downstream_pipelines.append(other_pipeline.name)
                                    break

            return GetPipelineDependenciesOutput(
                pipeline_name=input_data.pipeline_name,
                upstream_pipelines=upstream_pipelines,
                downstream_pipelines=downstream_pipelines,
                datasets_consumed=list(set(datasets_consumed)),
                datasets_produced=list(set(datasets_produced)),
                linked_services=list(linked_services)
            )

        except Exception as e:
            logger.error(f"Error analyzing pipeline dependencies: {str(e)}")
            raise

    def get_failed_tasks_summary(self, input_data: GetFailedTasksSummaryInput) -> GetFailedTasksSummaryOutput:
        """
        Summarize failed activities across pipeline runs within a time window.

        Implementation:
        1. Query pipeline runs within time window
        2. For each failed run, fetch activity runs
        3. Aggregate failures by activity name and error code
        4. Count occurrences and track timestamps
        """
        try:
            logger.info(f"Analyzing failed tasks for pipeline: {input_data.pipeline_name}")

            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=input_data.time_window_hours)

            # Query pipeline runs
            filter_params = {
                'last_updated_after': start_time,
                'last_updated_before': end_time
            }

            runs = list(self.df_client.pipeline_runs.query_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name,
                filter_parameters=filter_params
            ).value)

            # Filter for specific pipeline and failed status
            failed_runs = [
                run for run in runs
                if run.pipeline_name == input_data.pipeline_name and run.status == "Failed"
            ]

            # Aggregate failed activities
            failure_map = {}  # Key: (activity_name, error_code)

            for run in failed_runs:
                # Get activity runs for this pipeline run
                activity_runs = list(self.df_client.activity_runs.query_by_pipeline_run(
                    resource_group_name=self.resource_group,
                    factory_name=self.factory_name,
                    run_id=run.run_id,
                    filter_parameters={}
                ).value)

                for activity in activity_runs:
                    if activity.status == "Failed":
                        error_code = activity.error.get('errorCode', 'UNKNOWN') if activity.error else 'UNKNOWN'
                        error_message = activity.error.get('message', 'No error message') if activity.error else 'No error message'
                        key = (activity.activity_name, error_code)

                        if key not in failure_map:
                            failure_map[key] = {
                                'activity_name': activity.activity_name,
                                'error_code': error_code,
                                'error_message': error_message,
                                'count': 0,
                                'first_failure': activity.activity_run_end or datetime.utcnow(),
                                'last_failure': activity.activity_run_end or datetime.utcnow()
                            }

                        failure_map[key]['count'] += 1

                        # Update timestamps
                        if activity.activity_run_end:
                            if activity.activity_run_end < failure_map[key]['first_failure']:
                                failure_map[key]['first_failure'] = activity.activity_run_end
                            if activity.activity_run_end > failure_map[key]['last_failure']:
                                failure_map[key]['last_failure'] = activity.activity_run_end

            # Convert to FailedTask objects
            failed_tasks = [
                FailedTask(
                    activity_name=data['activity_name'],
                    error_code=data['error_code'],
                    error_message=data['error_message'],
                    failure_count=data['count'],
                    first_failure=data['first_failure'],
                    last_failure=data['last_failure']
                )
                for data in failure_map.values()
            ]

            # Sort by failure count descending
            failed_tasks.sort(key=lambda x: x.failure_count, reverse=True)

            return GetFailedTasksSummaryOutput(
                pipeline_name=input_data.pipeline_name,
                time_window_hours=input_data.time_window_hours,
                total_failures=len(failed_runs),
                failed_tasks=failed_tasks
            )

        except Exception as e:
            logger.error(f"Error analyzing failed tasks: {str(e)}")
            raise

    def get_all_pipelines(self) -> List[Dict[str, Any]]:
        """
        List all pipelines in the Data Factory with metadata.
        Used by: get_adf_pipelines MCP tool
        """
        try:
            pipelines = list(self.df_client.pipelines.list_by_factory(
                resource_group_name=self.resource_group,
                factory_name=self.factory_name
            ))

            result = []
            for pipeline in pipelines:
                # Extract basic info
                pipeline_info = {
                    'name': pipeline.name,
                    'description': getattr(pipeline, 'description', None),
                    'uses_key_vault': False,
                    'linked_services': [],
                    'environment': 'dev'  # Can be enhanced with tags
                }

                # Check if pipeline uses Key Vault
                if hasattr(pipeline, 'activities') and pipeline.activities:
                    for activity in pipeline.activities:
                        if hasattr(activity, 'linked_service_name') and activity.linked_service_name:
                            ls_name = activity.linked_service_name.reference_name
                            pipeline_info['linked_services'].append(ls_name)

                            # Check if linked service uses Key Vault
                            try:
                                ls = self.df_client.linked_services.get(
                                    resource_group_name=self.resource_group,
                                    factory_name=self.factory_name,
                                    linked_service_name=ls_name
                                )
                                # Check if connection string references Key Vault
                                if hasattr(ls, 'type_properties'):
                                    props_str = str(ls.type_properties)
                                    if 'AzureKeyVault' in props_str or 'vault' in props_str.lower():
                                        pipeline_info['uses_key_vault'] = True
                            except:
                                pass

                result.append(pipeline_info)

            return result

        except Exception as e:
            logger.error(f"Error listing pipelines: {str(e)}")
            raise
