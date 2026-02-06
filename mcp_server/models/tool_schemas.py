from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PipelineStatus(str, Enum):
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    IN_PROGRESS = "InProgress"
    QUEUED = "Queued"
    CANCELLED = "Cancelled"


class LogSource(str, Enum):
    ADF = "adf"
    APP = "app"


class LogLevel(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"


class TerraformAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"


# Pipeline Tool Schemas
class GetPipelineStatusInput(BaseModel):
    pipeline_name: str = Field(..., description="Name of the ADF pipeline")
    environment: str = Field(default="dev", description="Environment (dev/prod)")


class PipelineRunInfo(BaseModel):
    run_id: str
    pipeline_name: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]


class GetPipelineStatusOutput(BaseModel):
    pipeline_name: str
    last_run_status: PipelineStatus
    last_run_start: datetime
    last_run_end: Optional[datetime]
    last_success_time: Optional[datetime]
    last_failure_reason: Optional[str]
    recent_runs: List[PipelineRunInfo]


class GetPipelineDependenciesInput(BaseModel):
    pipeline_name: str
    environment: str = Field(default="dev")


class PipelineDependency(BaseModel):
    pipeline_name: str
    dependency_type: str  # "upstream", "downstream", "dataset"
    resource_name: str


class GetPipelineDependenciesOutput(BaseModel):
    pipeline_name: str
    upstream_pipelines: List[str]
    downstream_pipelines: List[str]
    datasets_consumed: List[str]
    datasets_produced: List[str]
    linked_services: List[str]


class GetFailedTasksSummaryInput(BaseModel):
    pipeline_name: str
    time_window_hours: int = Field(default=24, description="Time window in hours")


class FailedTask(BaseModel):
    activity_name: str
    error_code: str
    error_message: str
    failure_count: int
    first_failure: datetime
    last_failure: datetime


class GetFailedTasksSummaryOutput(BaseModel):
    pipeline_name: str
    time_window_hours: int
    total_failures: int
    failed_tasks: List[FailedTask]


# Key Vault Tool Schemas
class GetKeyVaultSecretsInput(BaseModel):
    prefix: Optional[str] = Field(None, description="Filter secrets by name prefix")
    include_high_risk: bool = Field(default=True, description="Include high-risk secrets")


class SecretInfo(BaseModel):
    name: str
    enabled: bool
    created_on: datetime
    updated_on: datetime
    tags: Dict[str, str]
    risk_level: Optional[str]


class GetKeyVaultSecretsOutput(BaseModel):
    secrets: List[SecretInfo]
    total_count: int


class GetSecretUsageInput(BaseModel):
    secret_name: str


class SecretUsage(BaseModel):
    pipeline_name: str
    linked_service_name: str
    environment: str
    is_production_critical: bool


class GetSecretUsageOutput(BaseModel):
    secret_name: str
    usage_count: int
    usages: List[SecretUsage]


# Log Tool Schemas
class FetchLogsInput(BaseModel):
    source: LogSource
    pipeline_name: Optional[str] = None
    run_id: Optional[str] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    level: Optional[LogLevel] = None


class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    source: LogSource
    message: str
    pipeline_name: Optional[str]
    run_id: Optional[str]
    activity_name: Optional[str]
    error_code: Optional[str]
    metadata: Dict[str, Any] = {}


class FetchLogsOutput(BaseModel):
    logs: List[LogEntry]
    total_count: int


class SummarizeErrorLogsInput(BaseModel):
    logs: Optional[List[LogEntry]] = None
    source: Optional[LogSource] = None
    pipeline_name: Optional[str] = None
    time_window_hours: int = 24


class ErrorCluster(BaseModel):
    cluster_id: str
    error_pattern: str
    sample_message: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    affected_pipelines: List[str]


class SummarizeErrorLogsOutput(BaseModel):
    total_errors: int
    clusters: List[ErrorCluster]
    anomalies: List[str]


# Terraform Tool Schemas
class ParseTerraformPlanInput(BaseModel):
    plan_path: str = Field(..., description="Path to terraform plan JSON file")


class ResourceChange(BaseModel):
    resource_type: str
    resource_name: str
    address: str
    actions: List[TerraformAction]
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    is_destructive: bool


class ParseTerraformPlanOutput(BaseModel):
    plan_path: str
    created_resources: List[ResourceChange]
    updated_resources: List[ResourceChange]
    deleted_resources: List[ResourceChange]
    high_risk_changes: List[ResourceChange]


class DetectInfraDriftInput(BaseModel):
    resource_group_name: str
    plan_path: Optional[str] = None


class DriftItem(BaseModel):
    resource_type: str
    resource_name: str
    drift_type: str  # "extra_in_cloud", "missing_in_cloud", "configuration_drift"
    details: str


class DetectInfraDriftOutput(BaseModel):
    has_drift: bool
    drift_items: List[DriftItem]


# Cloud Resource Tool Schemas
class ListResourcesByTagInput(BaseModel):
    tag_key: str
    tag_value: str
    resource_group: Optional[str] = None


class ResourceInfo(BaseModel):
    resource_id: str
    resource_name: str
    resource_type: str
    location: str
    tags: Dict[str, str]


class ListResourcesByTagOutput(BaseModel):
    resources: List[ResourceInfo]
    count: int
