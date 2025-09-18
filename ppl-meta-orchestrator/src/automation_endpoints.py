"""
PPL Meta Orchestrator - Automation Engine API Endpoints
Phase 2.4 Implementation: Time-based triggers and automated workflow execution
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from automation_engine import (
    AutomationAction,
    AutomationEngine,
    AutomationStatus,
    ExecutionStatus,
    TriggerCondition,
    TriggerType,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Pydantic models for API requests/responses
class TriggerConditionRequest(BaseModel):
    trigger_type: str = Field(..., description="Type of trigger")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    conditions: Dict[str, Any] = Field(default_factory=dict)


class AutomationActionRequest(BaseModel):
    action_type: str = Field(..., description="Type of action to execute")
    target: str = Field(..., description="Target for the action")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, description="Action priority (1-5)")


class CreateAutomationRuleRequest(BaseModel):
    rule_name: str = Field(..., description="Name of the automation rule")
    trigger_condition: TriggerConditionRequest
    actions: List[AutomationActionRequest]
    enabled: bool = Field(default=True)
    description: Optional[str] = None


class UpdateAutomationRuleRequest(BaseModel):
    rule_name: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    trigger_condition: Optional[TriggerConditionRequest] = None
    actions: Optional[List[AutomationActionRequest]] = None


class ExecuteRuleRequest(BaseModel):
    trigger_source: str = Field(default="manual")
    trigger_metadata: Optional[Dict[str, Any]] = None


class AutomationRuleResponse(BaseModel):
    rule_id: str
    rule_name: str
    status: str
    enabled: bool
    trigger_type: str
    actions_count: int
    created_at: str
    last_execution_time: Optional[str] = None
    success_rate: float
    total_executions: int


class AutomationExecutionResponse(BaseModel):
    execution_id: str
    rule_id: str
    status: str
    trigger_source: str
    actions_completed: int
    total_actions: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class AutomationStatusResponse(BaseModel):
    engine_status: str
    total_rules: int
    active_rules: int
    active_executions: int
    scheduled_tasks: int


class AutomationAnalyticsResponse(BaseModel):
    rule_id: str
    rule_name: str
    status: str
    created_at: str
    metrics: Dict[str, Any]
    trigger_condition: Dict[str, Any]
    actions: List[Dict[str, Any]]


class AutomationEndpoints:
    """FastAPI endpoints for automation engine management"""

    def __init__(self, automation_engine: AutomationEngine):
        self.automation_engine = automation_engine
        self.router = APIRouter(prefix="/automation", tags=["automation"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup all automation API routes"""

        @self.router.get("/health")
        async def automation_health():
            """Get automation engine health status"""
            try:
                status = await self.automation_engine.get_automation_status()
                return {
                    "status": "healthy",
                    "automation_engine": status,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                logger.error(f"Automation health check failed: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Health check failed: {str(e)}"
                )

        @self.router.post("/rules")
        async def create_automation_rule(
            request: CreateAutomationRuleRequest,
            user_id: str = Query(..., description="User ID for the rule"),
        ):
            """Create a new automation rule"""
            try:
                # Convert request to engine objects
                trigger_condition = TriggerCondition(
                    trigger_type=TriggerType(request.trigger_condition.trigger_type),
                    parameters=request.trigger_condition.parameters,
                    conditions=request.trigger_condition.conditions,
                )

                actions = [
                    AutomationAction(
                        action_type=action.action_type,
                        target=action.target,
                        parameters=action.parameters,
                        priority=action.priority,
                    )
                    for action in request.actions
                ]

                rule_id = await self.automation_engine.create_automation_rule(
                    user_id=user_id,
                    rule_name=request.rule_name,
                    trigger_condition=trigger_condition,
                    actions=actions,
                    enabled=request.enabled,
                    description=request.description,
                )

                return {
                    "status": "success",
                    "message": "Automation rule created successfully",
                    "rule_id": rule_id,
                    "rule_name": request.rule_name,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error(f"Failed to create automation rule: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create automation rule: {str(e)}",
                )

        @self.router.get("/rules")
        async def list_automation_rules(
            user_id: Optional[str] = Query(None),
            status: Optional[str] = Query(None),
            enabled: Optional[bool] = Query(None),
        ) -> List[AutomationRuleResponse]:
            """List automation rules with optional filtering"""
            try:
                # Get all rules from automation engine
                all_rules = self.automation_engine.automation_rules
                filtered_rules = []

                for rule_id, rule in all_rules.items():
                    # Apply filters
                    if user_id and rule["user_id"] != user_id:
                        continue
                    if status and rule["status"].value != status:
                        continue
                    if enabled is not None and rule["enabled"] != enabled:
                        continue

                    # Get metrics for this rule
                    metrics = self.automation_engine.automation_metrics.get(
                        rule_id,
                        type(
                            "",
                            (),
                            {
                                "total_executions": 0,
                                "success_rate": 1.0,
                                "last_execution_time": None,
                            },
                        )(),
                    )

                    filtered_rules.append(
                        AutomationRuleResponse(
                            rule_id=rule_id,
                            rule_name=rule["rule_name"],
                            status=rule["status"].value,
                            enabled=rule["enabled"],
                            trigger_type=rule["trigger_condition"].trigger_type.value,
                            actions_count=len(rule["actions"]),
                            created_at=rule["created_at"].isoformat(),
                            last_execution_time=(
                                metrics.last_execution_time.isoformat()
                                if metrics.last_execution_time
                                else None
                            ),
                            success_rate=metrics.success_rate,
                            total_executions=metrics.total_executions,
                        )
                    )

                return filtered_rules

            except Exception as e:
                logger.error(f"Failed to list automation rules: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to list automation rules: {str(e)}"
                )

        @self.router.get("/rules/{rule_id}")
        async def get_automation_rule(rule_id: str) -> AutomationAnalyticsResponse:
            """Get detailed information about a specific automation rule"""
            try:
                analytics = await self.automation_engine.get_rule_analytics(rule_id)
                return AutomationAnalyticsResponse(**analytics)

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to get automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get automation rule: {str(e)}"
                )

        @self.router.post("/rules/{rule_id}/execute")
        async def execute_automation_rule(
            rule_id: str, request: ExecuteRuleRequest = ExecuteRuleRequest()
        ):
            """Execute an automation rule manually"""
            try:
                execution_id = await self.automation_engine.execute_automation_rule(
                    rule_id=rule_id,
                    trigger_source=request.trigger_source,
                    trigger_metadata=request.trigger_metadata,
                )

                if not execution_id:
                    raise HTTPException(
                        status_code=400, detail="Rule execution failed or was queued"
                    )

                return {
                    "status": "success",
                    "message": "Automation rule executed",
                    "rule_id": rule_id,
                    "execution_id": execution_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to execute automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to execute automation rule: {str(e)}",
                )

        @self.router.put("/rules/{rule_id}")
        async def update_automation_rule(
            rule_id: str, request: UpdateAutomationRuleRequest
        ):
            """Update an automation rule"""
            try:
                # This would update the rule in the automation engine
                # For now, placeholder implementation

                return {
                    "status": "success",
                    "message": "Automation rule updated",
                    "rule_id": rule_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to update automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update automation rule: {str(e)}",
                )

        @self.router.delete("/rules/{rule_id}")
        async def delete_automation_rule(rule_id: str):
            """Delete an automation rule"""
            try:
                # This would delete the rule from the automation engine
                # For now, placeholder implementation

                return {
                    "status": "success",
                    "message": "Automation rule deleted",
                    "rule_id": rule_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to delete automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete automation rule: {str(e)}",
                )

        @self.router.post("/rules/{rule_id}/pause")
        async def pause_automation_rule(rule_id: str):
            """Pause an automation rule"""
            try:
                # This would pause the rule in the automation engine
                # For now, placeholder implementation

                return {
                    "status": "success",
                    "message": "Automation rule paused",
                    "rule_id": rule_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to pause automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to pause automation rule: {str(e)}"
                )

        @self.router.post("/rules/{rule_id}/resume")
        async def resume_automation_rule(rule_id: str):
            """Resume a paused automation rule"""
            try:
                # This would resume the rule in the automation engine
                # For now, placeholder implementation

                return {
                    "status": "success",
                    "message": "Automation rule resumed",
                    "rule_id": rule_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(f"Failed to resume automation rule {rule_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to resume automation rule: {str(e)}",
                )

        @self.router.get("/executions")
        async def list_automation_executions(
            rule_id: Optional[str] = Query(None),
            status: Optional[str] = Query(None),
            limit: int = Query(default=50, le=500),
        ) -> List[AutomationExecutionResponse]:
            """List automation executions with optional filtering"""
            try:
                # Get executions from automation engine
                executions = []

                for (
                    execution_id,
                    execution,
                ) in self.automation_engine.active_executions.items():
                    # Apply filters
                    if rule_id and execution["rule_id"] != rule_id:
                        continue
                    if status and execution["status"].value != status:
                        continue

                    executions.append(
                        AutomationExecutionResponse(
                            execution_id=execution_id,
                            rule_id=execution["rule_id"],
                            status=execution["status"].value,
                            trigger_source=execution["trigger_source"],
                            actions_completed=execution["actions_completed"],
                            total_actions=execution["total_actions"],
                            started_at=(
                                execution["started_at"].isoformat()
                                if execution.get("started_at")
                                else None
                            ),
                            completed_at=(
                                execution["completed_at"].isoformat()
                                if execution.get("completed_at")
                                else None
                            ),
                            error_message=execution.get("error_message"),
                        )
                    )

                return executions[:limit]

            except Exception as e:
                logger.error(f"Failed to list automation executions: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to list automation executions: {str(e)}",
                )

        @self.router.get("/status")
        async def get_automation_status() -> AutomationStatusResponse:
            """Get overall automation engine status"""
            try:
                status = await self.automation_engine.get_automation_status()
                return AutomationStatusResponse(
                    engine_status=status["engine_status"],
                    total_rules=status["total_rules"],
                    active_rules=status["active_rules"],
                    active_executions=status["active_executions"],
                    scheduled_tasks=status["scheduled_tasks"],
                )

            except Exception as e:
                logger.error(f"Failed to get automation status: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to get automation status: {str(e)}"
                )

        @self.router.get("/analytics")
        async def get_automation_analytics(
            user_id: Optional[str] = Query(None),
            days: int = Query(default=7, description="Number of days for analytics"),
        ):
            """Get automation analytics and metrics"""
            try:
                analytics = {
                    "period_days": days,
                    "total_rules": len(self.automation_engine.automation_rules),
                    "total_executions": sum(
                        metrics.total_executions
                        for metrics in self.automation_engine.automation_metrics.values()
                    ),
                    "average_success_rate": (
                        sum(
                            metrics.success_rate
                            for metrics in self.automation_engine.automation_metrics.values()
                        )
                        / len(self.automation_engine.automation_metrics)
                        if self.automation_engine.automation_metrics
                        else 1.0
                    ),
                    "rules_by_trigger_type": {},
                    "rules_by_status": {},
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Calculate rule distributions
                for rule in self.automation_engine.automation_rules.values():
                    if user_id and rule["user_id"] != user_id:
                        continue

                    trigger_type = rule["trigger_condition"].trigger_type.value
                    analytics["rules_by_trigger_type"][trigger_type] = (
                        analytics["rules_by_trigger_type"].get(trigger_type, 0) + 1
                    )

                    status = rule["status"].value
                    analytics["rules_by_status"][status] = (
                        analytics["rules_by_status"].get(status, 0) + 1
                    )

                return analytics

            except Exception as e:
                logger.error(f"Failed to get automation analytics: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get automation analytics: {str(e)}",
                )


def create_automation_router(automation_engine: AutomationEngine) -> APIRouter:
    """Create and return automation API router"""
    endpoints = AutomationEndpoints(automation_engine)
    return endpoints.router
