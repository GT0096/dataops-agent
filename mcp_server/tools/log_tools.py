from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import re
import json
from pathlib import Path
from mcp_server.utils.azure_client import azure_clients
from mcp_server.models.tool_schemas import (
    FetchLogsInput, FetchLogsOutput, LogEntry, LogSource, LogLevel,
    SummarizeErrorLogsInput, SummarizeErrorLogsOutput, ErrorCluster
)
from mcp_server.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class LogTools:
    """Log intelligence tools implementation"""

    def __init__(self):
        self.df_client = azure_clients.get_datafactory_client()
        self.resource_group = settings.azure_resource_group
        self.factory_name = settings.azure_data_factory_name
        self.app_log_path = settings.log_file_path

    def fetch_logs(self, input_data: FetchLogsInput) -> FetchLogsOutput:
        """
        Fetch logs from specified source (ADF or application logs).

        Implementation:
        - For ADF: Query pipeline runs and activity runs via Azure SDK
        - For App: Read and parse local log files
        """
        try:
            logger.info(f"Fetching logs from source: {input_data.source}")

            if input_data.source == LogSource.ADF:
                logs = self._fetch_adf_logs(input_data)
            elif input_data.source == LogSource.APP:
                logs = self._fetch_app_logs(input_data)
            else:
                raise ValueError(f"Unsupported log source: {input_data.source}")

            return FetchLogsOutput(
                logs=logs,
                total_count=len(logs)
            )

        except Exception as e:
            logger.error(f"Error fetching logs: {str(e)}")
            raise

    def _fetch_adf_logs(self, input_data: FetchLogsInput) -> List[LogEntry]:
        """Fetch logs from Azure Data Factory"""
        logs = []

        # Set time range
        end_time = input_data.time_end or datetime.utcnow()
        start_time = input_data.time_start or (end_time - timedelta(hours=24))

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

        # Filter by pipeline name if specified
        if input_data.pipeline_name:
            runs = [r for r in runs if r.pipeline_name == input_data.pipeline_name]

        # Filter by run_id if specified
        if input_data.run_id:
            runs = [r for r in runs if r.run_id == input_data.run_id]

        for run in runs:
            # Add pipeline run log entry
            level = LogLevel.ERROR if run.status == "Failed" else LogLevel.INFO

            # Filter by level if specified
            if input_data.level and level != input_data.level:
                continue

            logs.append(LogEntry(
                timestamp=run.run_start,
                level=level,
                source=LogSource.ADF,
                message=f"Pipeline run {run.status}: {run.message or 'No message'}",
                pipeline_name=run.pipeline_name,
                run_id=run.run_id,
                activity_name=None,
                error_code=None,
                metadata={
                    'status': run.status,
                    'duration_ms': run.duration_in_ms if hasattr(run, 'duration_in_ms') else None
                }
            ))

            # Get activity runs for failed pipeline runs
            if run.status == "Failed":
                try:
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

                            logs.append(LogEntry(
                                timestamp=activity.activity_run_end or run.run_start,
                                level=LogLevel.ERROR,
                                source=LogSource.ADF,
                                message=f"Activity {activity.activity_name} failed: {error_message}",
                                pipeline_name=run.pipeline_name,
                                run_id=run.run_id,
                                activity_name=activity.activity_name,
                                error_code=error_code,
                                metadata={
                                    'activity_type': activity.activity_type,
                                    'error': activity.error
                                }
                            ))
                except Exception as e:
                    logger.warning(f"Could not fetch activity runs for {run.run_id}: {str(e)}")

        return logs

    def _fetch_app_logs(self, input_data: FetchLogsInput) -> List[LogEntry]:
        """Fetch logs from application log files"""
        logs = []

        if not self.app_log_path.exists():
            logger.warning(f"App log file not found: {self.app_log_path}")
            return logs

        # Set time range
        end_time = input_data.time_end or datetime.utcnow()
        start_time = input_data.time_start or (end_time - timedelta(hours=24))

        # Read log file
        with open(self.app_log_path, 'r') as f:
            for line in f:
                try:
                    # Try JSON format first
                    log_data = json.loads(line.strip())

                    # Parse timestamp
                    timestamp = datetime.fromisoformat(log_data.get('timestamp', ''))

                    # Filter by time range
                    if timestamp < start_time or timestamp > end_time:
                        continue

                    # Parse level
                    level_str = log_data.get('level', 'INFO').upper()
                    level = LogLevel[level_str] if level_str in LogLevel.__members__ else LogLevel.INFO

                    # Filter by level if specified
                    if input_data.level and level != input_data.level:
                        continue

                    # Filter by pipeline name if specified
                    if input_data.pipeline_name and log_data.get('pipeline_name') != input_data.pipeline_name:
                        continue

                    logs.append(LogEntry(
                        timestamp=timestamp,
                        level=level,
                        source=LogSource.APP,
                        message=log_data.get('message', ''),
                        pipeline_name=log_data.get('pipeline_name'),
                        run_id=log_data.get('run_id'),
                        activity_name=None,
                        error_code=None,
                        metadata=log_data.get('metadata', {})
                    ))

                except (json.JSONDecodeError, ValueError, KeyError):
                    # Fallback: parse as plain text with regex
                    # Format: YYYY-MM-DD HH:MM:SS LEVEL message
                    match = re.match(
                        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+)\s+(.*)',
                        line.strip()
                    )
                    if match:
                        timestamp_str, level_str, message = match.groups()
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                        # Filter by time range
                        if timestamp < start_time or timestamp > end_time:
                            continue

                        level = LogLevel[level_str.upper()] if level_str.upper() in LogLevel.__members__ else LogLevel.INFO

                        # Filter by level if specified
                        if input_data.level and level != input_data.level:
                            continue

                        logs.append(LogEntry(
                            timestamp=timestamp,
                            level=level,
                            source=LogSource.APP,
                            message=message,
                            pipeline_name=None,
                            run_id=None,
                            activity_name=None,
                            error_code=None,
                            metadata={}
                        ))

        return logs

    def summarize_error_logs(self, input_data: SummarizeErrorLogsInput) -> SummarizeErrorLogsOutput:
        """
        Cluster and summarize error logs to identify patterns and anomalies.

        Implementation:
        1. Fetch logs if not provided
        2. Filter for errors only
        3. Cluster similar error messages
        4. Count occurrences and track timestamps
        5. Identify anomalies (new errors, spike in frequency)
        """
        try:
            logger.info("Summarizing error logs")

            # Get logs if not provided
            if input_data.logs is None:
                fetch_input = FetchLogsInput(
                    source=input_data.source or LogSource.ADF,
                    pipeline_name=input_data.pipeline_name,
                    time_start=datetime.utcnow() - timedelta(hours=input_data.time_window_hours),
                    time_end=datetime.utcnow(),
                    level=LogLevel.ERROR
                )
                fetch_result = self.fetch_logs(fetch_input)
                logs = fetch_result.logs
            else:
                # Filter for errors
                logs = [log for log in input_data.logs if log.level == LogLevel.ERROR]

            # Cluster errors
            clusters = self._cluster_errors(logs)

            # Identify anomalies
            anomalies = self._identify_anomalies(clusters, input_data.time_window_hours)

            return SummarizeErrorLogsOutput(
                total_errors=len(logs),
                clusters=clusters,
                anomalies=anomalies
            )

        except Exception as e:
            logger.error(f"Error summarizing logs: {str(e)}")
            raise

    def _cluster_errors(self, logs: List[LogEntry]) -> List[ErrorCluster]:
        """Cluster similar error messages"""
        # Group by error_code first, then by normalized message
        error_groups = defaultdict(list)

        for log in logs:
            # Create clustering key
            key_parts = []

            if log.error_code:
                key_parts.append(log.error_code)

            # Normalize message (remove timestamps, numbers, IDs)
            normalized_msg = re.sub(r'\d{4}-\d{2}-\d{2}', '<date>', log.message)
            normalized_msg = re.sub(r'\d{2}:\d{2}:\d{2}', '<time>', normalized_msg)
            normalized_msg = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<uuid>', normalized_msg)
            normalized_msg = re.sub(r'\d+', '<num>', normalized_msg)

            # Extract first sentence as pattern
            pattern = normalized_msg.split('.')[0][:100]
            key_parts.append(pattern)

            key = '|'.join(key_parts)
            error_groups[key].append(log)

        # Convert to ErrorCluster objects
        clusters = []
        for cluster_id, (key, logs_in_cluster) in enumerate(error_groups.items()):
            # Get pattern and sample message
            parts = key.split('|')
            error_pattern = parts[-1]

            # Get affected pipelines
            affected_pipelines = list(set(
                log.pipeline_name for log in logs_in_cluster if log.pipeline_name
            ))

            # Get time range
            timestamps = [log.timestamp for log in logs_in_cluster]

            clusters.append(ErrorCluster(
                cluster_id=f"error_cluster_{cluster_id}",
                error_pattern=error_pattern,
                sample_message=logs_in_cluster[0].message,
                count=len(logs_in_cluster),
                first_occurrence=min(timestamps),
                last_occurrence=max(timestamps),
                affected_pipelines=affected_pipelines
            ))

        # Sort by count descending
        clusters.sort(key=lambda x: x.count, reverse=True)

        return clusters

    def _identify_anomalies(self, clusters: List[ErrorCluster], time_window_hours: int) -> List[str]:
        """Identify anomalous error patterns"""
        anomalies = []

        # Check for new error patterns (first seen recently)
        recent_threshold = datetime.utcnow() - timedelta(hours=time_window_hours // 2)

        for cluster in clusters:
            # New error pattern
            if cluster.first_occurrence > recent_threshold:
                anomalies.append(
                    f"New error pattern detected: '{cluster.error_pattern}' "
                    f"first seen at {cluster.first_occurrence.isoformat()}, "
                    f"occurred {cluster.count} times"
                )

            # High frequency errors
            if cluster.count > 10:
                time_span = (cluster.last_occurrence - cluster.first_occurrence).total_seconds() / 3600
                if time_span > 0:
                    rate = cluster.count / time_span
                    if rate > 2:  # More than 2 per hour
                        anomalies.append(
                            f"High frequency error: '{cluster.error_pattern}' "
                            f"occurring at {rate:.1f} times per hour"
                        )

        return anomalies

    def compare_success_vs_failure_logs(
        self,
        pipeline_name: str,
        success_run_id: str,
        failure_run_id: str
    ) -> Dict[str, Any]:
        """
        Compare logs between successful and failed pipeline runs.

        Implementation:
        1. Fetch logs for both runs
        2. Compare activity sequences
        3. Identify differences in execution paths
        4. Highlight errors present only in failure
        """
        try:
            logger.info(f"Comparing runs for pipeline: {pipeline_name}")

            # Fetch logs for success run
            success_logs = self.fetch_logs(FetchLogsInput(
                source=LogSource.ADF,
                pipeline_name=pipeline_name,
                run_id=success_run_id
            )).logs

            # Fetch logs for failure run
            failure_logs = self.fetch_logs(FetchLogsInput(
                source=LogSource.ADF,
                pipeline_name=pipeline_name,
                run_id=failure_run_id
            )).logs

            # Extract activity sequences
            success_activities = [
                log.activity_name for log in success_logs
                if log.activity_name
            ]
            failure_activities = [
                log.activity_name for log in failure_logs
                if log.activity_name
            ]

            # Find differences
            activities_only_in_failure = set(failure_activities) - set(success_activities)
            activities_only_in_success = set(success_activities) - set(failure_activities)

            # Get error messages from failure
            error_messages = [
                log.message for log in failure_logs
                if log.level == LogLevel.ERROR
            ]

            return {
                'pipeline_name': pipeline_name,
                'success_run_id': success_run_id,
                'failure_run_id': failure_run_id,
                'differences': {
                    'activities_only_in_failure': list(activities_only_in_failure),
                    'activities_only_in_success': list(activities_only_in_success),
                    'error_messages': error_messages
                },
                'summary': self._generate_comparison_summary(
                    success_activities,
                    failure_activities,
                    error_messages
                )
            }

        except Exception as e:
            logger.error(f"Error comparing logs: {str(e)}")
            raise

    def _generate_comparison_summary(
        self,
        success_activities: List[str],
        failure_activities: List[str],
        error_messages: List[str]
    ) -> str:
        """Generate human-readable comparison summary"""
        summary_parts = []

        if not failure_activities:
            summary_parts.append("Failure run has no activity logs.")
        elif not success_activities:
            summary_parts.append("Success run has no activity logs for comparison.")
        else:
            common_count = len(set(success_activities) & set(failure_activities))
            summary_parts.append(
                f"Both runs executed {common_count} common activities."
            )

        if error_messages:
            summary_parts.append(
                f"Failure run encountered {len(error_messages)} errors. "
                f"Primary error: {error_messages[0][:200]}"
            )

        return " ".join(summary_parts)
