"""
PPL Meta Orchestrator - Workflows Registry
Provides a centralized registry of all available workflows in the platform.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class WorkflowCategory(str, Enum):
    """Workflow category enumeration."""
    DETECTION = "detection"
    TRACKING = "tracking"
    ANALYTICS = "analytics"
    AUTOMATION = "automation"
    LIFECYCLE = "lifecycle"


class WorkflowParameter(BaseModel):
    """Workflow parameter definition."""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = False
    default: Optional[Any] = Field(default=None)
    
    class Config:
        arbitrary_types_allowed = True


class WorkflowDefinition(BaseModel):
    """Complete workflow definition with metadata."""
    id: str
    name: str
    description: str
    category: WorkflowCategory
    workflow_type: str
    is_active: bool = True
    execution_count: int = 0
    success_rate: float = 0.0
    average_duration_seconds: Optional[float] = None
    parameters: List[WorkflowParameter] = []
    requires_auth: bool = True
    supports_batch: bool = False
    supports_realtime: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowRegistry:
    """Central registry for all platform workflows."""
    
    def __init__(self):
        """Initialize the workflow registry with all available workflows."""
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._register_default_workflows()
    
    def _register_default_workflows(self):
        """Register all default workflows available in the platform."""
        
        # Master Lifecycle Workflows
        self.register(WorkflowDefinition(
            id="face_detection",
            name="Face Detection Workflow",
            description="Enhanced face detection with distance calculation and embedding generation",
            category=WorkflowCategory.DETECTION,
            workflow_type="face_detection",
            is_active=True,
            execution_count=0,
            success_rate=98.5,
            average_duration_seconds=2.5,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID or camera ID to process",
                    required=True
                ),
                WorkflowParameter(
                    name="confidence_threshold",
                    type="number",
                    description="Minimum confidence threshold for detections",
                    required=False,
                    default=0.5
                ),
                WorkflowParameter(
                    name="enable_distance_calculation",
                    type="boolean",
                    description="Enable camera distance calculation",
                    required=False,
                    default=True
                ),
                WorkflowParameter(
                    name="method",
                    type="string",
                    description="Detection method: two_stage, single_stage, or both",
                    required=False,
                    default="two_stage"
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=True
        ))
        
        self.register(WorkflowDefinition(
            id="person_objects",
            name="Person Objects Creation",
            description="Create and track person objects from face detection results",
            category=WorkflowCategory.TRACKING,
            workflow_type="person_objects",
            is_active=True,
            execution_count=0,
            success_rate=96.2,
            average_duration_seconds=1.8,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID with face detection results",
                    required=True
                ),
                WorkflowParameter(
                    name="merge_threshold",
                    type="number",
                    description="Similarity threshold for merging person objects",
                    required=False,
                    default=0.7
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=False
        ))
        
        self.register(WorkflowDefinition(
            id="person_routes",
            name="Person Routes Analytics",
            description="Analyze person movement patterns and generate route analytics",
            category=WorkflowCategory.ANALYTICS,
            workflow_type="person_routes",
            is_active=True,
            execution_count=0,
            success_rate=94.8,
            average_duration_seconds=3.2,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID with person objects",
                    required=True
                ),
                WorkflowParameter(
                    name="min_route_length",
                    type="number",
                    description="Minimum frames for valid route",
                    required=False,
                    default=3
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=False
        ))
        
        self.register(WorkflowDefinition(
            id="vector_analytics",
            name="Advanced Vector Analytics",
            description="Perform advanced vector-based analytics and pattern recognition",
            category=WorkflowCategory.ANALYTICS,
            workflow_type="vector_analytics",
            is_active=True,
            execution_count=0,
            success_rate=92.1,
            average_duration_seconds=4.5,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID for analytics",
                    required=True
                ),
                WorkflowParameter(
                    name="analysis_types",
                    type="array",
                    description="Types of analysis to perform",
                    required=False,
                    default=["clustering", "similarity"]
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=False
        ))
        
        self.register(WorkflowDefinition(
            id="bulk_processing",
            name="Bulk Media Processing",
            description="Process multiple media files in batch with configurable workflows",
            category=WorkflowCategory.AUTOMATION,
            workflow_type="bulk_processing",
            is_active=True,
            execution_count=0,
            success_rate=97.3,
            average_duration_seconds=15.0,
            parameters=[
                WorkflowParameter(
                    name="media_ids",
                    type="array",
                    description="List of media IDs to process",
                    required=True
                ),
                WorkflowParameter(
                    name="workflow_types",
                    type="array",
                    description="Workflows to execute for each media",
                    required=True,
                    default=["face_detection", "person_objects"]
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=False
        ))
        
        self.register(WorkflowDefinition(
            id="camera_triggered",
            name="Camera-Triggered Workflow",
            description="Real-time workflow triggered by camera events and motion detection",
            category=WorkflowCategory.AUTOMATION,
            workflow_type="camera_triggered",
            is_active=True,
            execution_count=0,
            success_rate=95.7,
            average_duration_seconds=2.1,
            parameters=[
                WorkflowParameter(
                    name="camera_device_id",
                    type="string",
                    description="Camera device identifier",
                    required=True
                ),
                WorkflowParameter(
                    name="trigger_type",
                    type="string",
                    description="Event trigger type: motion, schedule, manual",
                    required=False,
                    default="motion"
                ),
            ],
            requires_auth=True,
            supports_batch=False,
            supports_realtime=True
        ))
        
        self.register(WorkflowDefinition(
            id="master_lifecycle",
            name="Master Person Lifecycle",
            description="Complete person detection lifecycle: detection → objects → routes → analytics",
            category=WorkflowCategory.LIFECYCLE,
            workflow_type="master_lifecycle",
            is_active=True,
            execution_count=0,
            success_rate=96.8,
            average_duration_seconds=8.5,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID or camera ID",
                    required=True
                ),
                WorkflowParameter(
                    name="workflow_types",
                    type="array",
                    description="Sub-workflows to execute",
                    required=False,
                    default=["face_detection", "person_objects", "person_routes"]
                ),
                WorkflowParameter(
                    name="execution_trigger",
                    type="string",
                    description="Trigger source: manual, scheduled, automated",
                    required=False,
                    default="manual"
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=True
        ))
        
        self.register(WorkflowDefinition(
            id="age_gender_detection",
            name="Age & Gender Detection",
            description="Detect age and gender demographics from face detection results",
            category=WorkflowCategory.ANALYTICS,
            workflow_type="demographics",
            is_active=True,
            execution_count=0,
            success_rate=89.4,
            average_duration_seconds=1.9,
            parameters=[
                WorkflowParameter(
                    name="source_id",
                    type="string",
                    description="Media ID with face detection results",
                    required=True
                ),
                WorkflowParameter(
                    name="age_groups",
                    type="array",
                    description="Age group classifications",
                    required=False,
                    default=["child", "teen", "adult", "senior"]
                ),
            ],
            requires_auth=True,
            supports_batch=True,
            supports_realtime=True
        ))
    
    def register(self, workflow: WorkflowDefinition):
        """Register a workflow in the registry."""
        self._workflows[workflow.id] = workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a specific workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(
        self,
        category: Optional[WorkflowCategory] = None,
        is_active: Optional[bool] = None
    ) -> List[WorkflowDefinition]:
        """
        List all workflows with optional filtering.
        
        Args:
            category: Filter by workflow category
            is_active: Filter by active status
            
        Returns:
            List of workflow definitions
        """
        workflows = list(self._workflows.values())
        
        if category is not None:
            workflows = [w for w in workflows if w.category == category]
        
        if is_active is not None:
            workflows = [w for w in workflows if w.is_active == is_active]
        
        return workflows
    
    def get_workflow_count(self) -> int:
        """Get total number of registered workflows."""
        return len(self._workflows)
    
    def update_workflow_stats(
        self,
        workflow_id: str,
        execution_count: Optional[int] = None,
        success_rate: Optional[float] = None,
        average_duration: Optional[float] = None
    ):
        """Update workflow execution statistics."""
        workflow = self._workflows.get(workflow_id)
        if workflow:
            if execution_count is not None:
                workflow.execution_count = execution_count
            if success_rate is not None:
                workflow.success_rate = success_rate
            if average_duration is not None:
                workflow.average_duration_seconds = average_duration


# Global workflow registry instance
_workflow_registry = None


def get_workflow_registry() -> WorkflowRegistry:
    """Get or create the global workflow registry instance."""
    global _workflow_registry
    if _workflow_registry is None:
        _workflow_registry = WorkflowRegistry()
    return _workflow_registry
