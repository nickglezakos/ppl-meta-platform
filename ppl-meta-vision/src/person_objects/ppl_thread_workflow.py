"""
PPL Meta Vision Service - PPL Thread Workflow Controller
Main workflow orchestration for the PPL Thread (Person Objects) processing system.

This controller manages the complete person objects workflow by:
1. Orchestrating face grouping using VisionFaceGroupingEngine
2. Managing quality analysis with PersonQualityAnalyzer
3. Storing results in the Phase 1 database schema
4. Providing PPL Meta Mini compatible output format
5. Handling workflow state and error management

Key Features:
- Complete workflow orchestration from face detections to person objects
- PPL Meta Mini compatible response format
- Database integration with Phase 1 schema
- Comprehensive error handling and workflow tracking
- Independent implementation with zero PPL Mini dependencies
"""

import asyncio
import httpx
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Database imports (Phase 1 integration)
try:
    from database import VisionDatabase
    from database.person_objects_migrations import PersonObjectsMigration
except ImportError:
    # For standalone testing, create mock classes
    class VisionDatabase:
        def __init__(self):
            pass

    class PersonObjectsMigration:
        @staticmethod
        def validate_person_objects_schema(db):
            return True


# Core algorithm imports (Phase 2 integration)
from .face_grouping_engine import VisionFaceGroupingEngine
from .quality_analyzer import PersonQualityAnalyzer

logger = logging.getLogger(__name__)


class PPLThreadWorkflowController:
    """
    Main workflow controller for PPL Thread (Person Objects) processing.

    This workflow operates as a second-level processing stage that takes
    existing face detection data and applies advanced grouping to create
    person objects with the same structure as PPL Meta Mini output.

    Architecture:
    - Phase 1: Database schema for person objects storage
    - Phase 2: Core face grouping and quality analysis algorithms
    - Phase 3: Workflow orchestration and API integration (this class)
    """

    def __init__(self, database: VisionDatabase):
        """
        Initialize the PPL Thread workflow controller.

        Args:
            database: Vision Service database connection
        """
        self.db = database
        self.face_grouping_engine = VisionFaceGroupingEngine()
        self.quality_analyzer = PersonQualityAnalyzer()

        # Workflow configuration
        self.orchestrator_url = "http://localhost:8002"
        self.orchestrator_token = "internal-service-token-ppl-meta-vision"
        self.default_tolerance_percent = 20.0  # Fallback if orchestrator unreachable
        self.max_processing_time_minutes = 30
        self.batch_size = 100
        self._velocity_sensitivity_cache = None
        self._cache_timestamp = None

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        """Check if string is a valid UUID format."""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False

    async def _fetch_velocity_sensitivity_from_orchestrator(self) -> float:
        """
        Fetch velocity sensitivity setting from orchestrator service.
        
        Uses caching to avoid repeated API calls within the same workflow session.
        Falls back to default_tolerance_percent if orchestrator is unreachable.
        
        Returns:
            Velocity sensitivity percentage (5.0-50.0)
        """
        # Check cache (valid for 60 seconds)
        if self._velocity_sensitivity_cache is not None and self._cache_timestamp:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < 60:
                logger.debug(f"Using cached velocity sensitivity: {self._velocity_sensitivity_cache}%")
                return self._velocity_sensitivity_cache
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(
                    f"{self.orchestrator_url}/api/v1/settings/workflow/velocity-sensitivity",
                    headers={"Authorization": f"Bearer {self.orchestrator_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    value = data.get("value", self.default_tolerance_percent)
                    
                    # Update cache
                    self._velocity_sensitivity_cache = value
                    self._cache_timestamp = datetime.now()
                    
                    logger.info(
                        f"Fetched velocity sensitivity from orchestrator: {value}% "
                        f"(recommendation: {data.get('recommendation', 'N/A')})"
                    )
                    return value
                else:
                    logger.warning(
                        f"Orchestrator returned status {response.status_code}, "
                        f"using fallback: {self.default_tolerance_percent}%"
                    )
                    return self.default_tolerance_percent
                    
        except httpx.TimeoutException:
            logger.warning(
                f"Orchestrator timeout, using fallback: {self.default_tolerance_percent}%"
            )
            return self.default_tolerance_percent
        except Exception as e:
            logger.warning(
                f"Error fetching velocity sensitivity from orchestrator: {e}, "
                f"using fallback: {self.default_tolerance_percent}%"
            )
            return self.default_tolerance_percent

    def find_session_uuid_by_media_uuid(self, media_uuid: str) -> Optional[str]:
        """
        Find session UUID by media UUID through database query.

        This is a dynamic discovery method that directly queries the face_detection_sessions
        table to find the session UUID associated with a given media UUID.

        Args:
            media_uuid: The media UUID to search for

        Returns:
            Session UUID if found, None otherwise
        """
        if not self._is_valid_uuid(media_uuid):
            logger.warning("Invalid media UUID format: %s", media_uuid)
            return None

        try:
            cursor = self.db.connection.cursor()

            query = """
            SELECT session_uuid 
            FROM face_detection_sessions 
            WHERE media_uuid = %s 
            ORDER BY created_at DESC 
            LIMIT 1
            """

            cursor.execute(query, (media_uuid,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                session_uuid = result[0]
                logger.info(
                    "Found session UUID %s for media UUID %s", session_uuid, media_uuid
                )
                return session_uuid
            else:
                logger.warning("No session found for media UUID %s", media_uuid)
                return None

        except Exception as e:
            logger.error("Error finding session by media UUID: %s", e)
            if "cursor" in locals():
                cursor.close()
            return None

    def create_session_for_legacy_media(
        self, media_uuid: str, face_count: int
    ) -> Optional[str]:
        """
        Create a face detection session for legacy media that has face data but no session.

        This enables PPL Thread processing for legacy media by creating the required
        session entry in the face_detection_sessions table.

        Args:
            media_uuid: The media UUID with existing face detections
            face_count: Number of faces detected for this media

        Returns:
            Session UUID if created successfully, None otherwise
        """
        if not self._is_valid_uuid(media_uuid):
            logger.warning("Invalid media UUID format: %s", media_uuid)
            return None

        try:
            session_uuid = str(uuid.uuid4())
            cursor = self.db.connection.cursor()

            # First, ensure media record exists (create if missing for legacy data)
            media_check_query = "SELECT COUNT(*) FROM media_records WHERE media_id = %s"
            cursor.execute(media_check_query, (media_uuid,))
            media_exists = cursor.fetchone()[0] > 0

            if not media_exists:
                # Create minimal media record for legacy data
                media_insert_query = """
                INSERT INTO media_records (media_id, filename, created_at, source) 
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(
                    media_insert_query,
                    (
                        media_uuid,
                        f"legacy_media_{media_uuid[:8]}.mp4",  # Placeholder filename
                        datetime.now(),
                        "legacy_processor",
                    ),
                )
                logger.info("Created media record for legacy media %s", media_uuid)

            # Insert session record for legacy media
            insert_query = """
            INSERT INTO face_detection_sessions 
            (session_uuid, media_uuid, total_faces_detected, started_at, processing_status, session_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    session_uuid,
                    media_uuid,
                    face_count,
                    datetime.now(),  # started_at
                    "completed",  # processing_status - mark as completed since faces already exist
                    "bulk_processing",  # session_type - use valid constraint value
                    datetime.now(),  # created_at
                ),
            )

            self.db.connection.commit()
            cursor.close()

            logger.info(
                "Created session %s for legacy media %s with %d faces",
                session_uuid,
                media_uuid,
                face_count,
            )
            return session_uuid

        except Exception as e:
            logger.error("Error creating session for legacy media: %s", e)
            if "cursor" in locals():
                cursor.close()
            if hasattr(self.db.connection, "rollback"):
                self.db.connection.rollback()
            return None

    async def start_person_objects_workflow(
        self,
        session_uuid: str,
        tolerance_percent: Optional[float] = None,
        enable_quality_analysis: bool = True,
        enable_age_detection: bool = True,
        workflow_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Start PPL Thread workflow for creating person objects from face detections.

        This is the main entry point that orchestrates the complete workflow:
        1. Validate input session and create workflow record
        2. Fetch face detections from database
        3. Apply face grouping algorithm (Phase 2 engine)
        4. Perform quality analysis and best face selection
        5. Store person objects in database (Phase 1 schema)
        6. Return PPL Meta Mini compatible results

        Args:
            session_uuid: Face detection session to process
            tolerance_percent: Position matching tolerance (5.0-50.0%). If None, fetches from orchestrator
            enable_quality_analysis: Enable best face quality analysis
            enable_age_detection: Enable age estimation (future enhancement)
            workflow_metadata: Additional workflow metadata

        Returns:
            Workflow execution results with person objects data in PPL Mini format
        """
        workflow_id = str(uuid.uuid4())
        
        # Fetch velocity sensitivity from orchestrator if not provided
        if tolerance_percent is None:
            tolerance_percent = await self._fetch_velocity_sensitivity_from_orchestrator()
        start_time = datetime.now()

        logger.info(
            "Starting PPL Thread workflow %s for session %s", workflow_id, session_uuid
        )

        try:
            # Step 1: Validate session and create workflow record
            self._validate_session_exists(session_uuid)
            self._create_workflow_record(
                workflow_id, session_uuid, tolerance_percent, workflow_metadata
            )

            # Step 2: Fetch face detection data for session
            logger.info("Fetching face detections for session %s", session_uuid)
            face_detections = self._get_session_face_detections(session_uuid)

            if not face_detections:
                raise ValueError(f"No face detections found for session {session_uuid}")

            logger.info("Found %d face detections to process", len(face_detections))

            # Step 3: Apply face grouping algorithm
            # Check if faces already have person_id from Orchestrator
            has_person_id = any("person_id" in face and face["person_id"] for face in face_detections)
            
            if has_person_id:
                logger.info(
                    "Using Orchestrator's person_id grouping (preserves IoU-based grouping)"
                )
                grouping_results = (
                    await self.face_grouping_engine.group_by_orchestrator_person_id(
                        face_detections
                    )
                )
            else:
                logger.info(
                    "Applying percentage-based tracking with %.1f%% tolerance", tolerance_percent
                )
                grouping_results = (
                    await self.face_grouping_engine.apply_percentage_based_tracking(
                        face_detections, tolerance_percent
                    )
                )

            logger.info(
                "Face grouping results received, type: %s", type(grouping_results)
            )
            if (
                isinstance(grouping_results, dict)
                and "person_objects" in grouping_results
            ):
                logger.info(
                    "Face grouping complete: %d faces → %d persons",
                    len(face_detections),
                    len(grouping_results["person_objects"]),
                )
            else:
                logger.error("Invalid grouping_results structure: %s", grouping_results)

            # Step 4: Store person objects and mappings in database (Phase 1 schema)
            logger.info(
                "About to store person objects and mappings for workflow %s",
                workflow_id,
            )
            logger.info("Grouping results keys: %s", list(grouping_results.keys()))
            logger.info("Type of grouping_results: %s", type(grouping_results))
            person_id_mapping = self._store_person_objects_and_mappings(
                workflow_id, session_uuid, grouping_results
            )

            logger.info(
                "Face mappings storage completed, moving to quality analysis..."
            )
            logger.info("enable_quality_analysis = %s", enable_quality_analysis)

            # Step 5: Perform quality analysis if enabled
            best_quality_faces = {}
            if enable_quality_analysis:
                logger.info(
                    "Performing quality analysis for %d persons",
                    len(grouping_results["person_objects"]),
                )

                try:
                    logger.info(
                        "About to call quality_analyzer.select_best_face_per_person..."
                    )
                    quality_analysis_results = (
                        self.quality_analyzer.select_best_face_per_person(
                            grouping_results["person_objects"],
                            face_detections,
                            grouping_results["face_mappings"],
                        )
                    )
                    logger.info(
                        "Quality analyzer returned: %s", type(quality_analysis_results)
                    )

                    # Extract just the best_faces dictionary for storage
                    best_quality_faces = quality_analysis_results["best_faces"]
                    logger.info(
                        "Extracted best_quality_faces with %d persons",
                        len(best_quality_faces),
                    )
                except Exception as quality_error:
                    logger.error("Quality analysis failed: %s", quality_error)
                    import traceback

                    logger.error("Traceback: %s", traceback.format_exc())
                    raise

                # Store quality analysis results
                logger.info(
                    "About to call _store_quality_analysis_results with %d faces",
                    len(best_quality_faces),
                )
                logger.info(
                    "best_quality_faces sample keys: %s",
                    (
                        list(best_quality_faces.keys())[:3]
                        if best_quality_faces
                        else "None"
                    ),
                )
                try:
                    self._store_quality_analysis_results(
                        workflow_id,
                        session_uuid,
                        best_quality_faces,
                        person_id_mapping,
                        quality_rankings=quality_analysis_results.get("quality_rankings", {}),
                        face_mappings=grouping_results["face_mappings"],
                    )
                except Exception as qa_error:
                    logger.error("Quality analysis storage failed: %s", qa_error)
                    logger.error("best_quality_faces structure: %s", best_quality_faces)
                    raise

                logger.info(
                    "Quality analysis complete for %d persons", len(best_quality_faces)
                )

            # Step 6: Update workflow status to completed
            processing_time = (datetime.now() - start_time).total_seconds()
            self._complete_workflow(
                workflow_id,
                len(grouping_results["person_objects"]),
                len(face_detections),
                processing_time,
            )

            # Step 7: Format response to match PPL Meta Mini structure exactly
            response = self._format_ppl_mini_compatible_response(
                grouping_results, best_quality_faces, workflow_id, session_uuid,
                person_id_mapping=person_id_mapping,
            )

            logger.info(
                "PPL Thread workflow %s completed successfully in %.2f seconds",
                workflow_id,
                processing_time,
            )

            return response

        except Exception as e:
            # Update workflow status to failed
            error_message = f"Workflow failed: {str(e)}"
            logger.error(
                "PPL Thread workflow %s failed: %s", workflow_id, error_message
            )

            try:
                self._fail_workflow(workflow_id, error_message)
            except Exception as db_error:
                logger.error("Failed to update workflow failure status: %s", db_error)

            # Re-raise original exception
            raise RuntimeError(
                f"PPL Thread workflow {workflow_id} failed: {str(e)}"
            ) from e

    async def start_person_objects_workflow_from_faces(
        self,
        face_detections: List[Dict],
        session_uuid: str,
        tolerance_percent: Optional[float] = None,
        enable_quality_analysis: bool = True,
        enable_age_detection: bool = True,
        workflow_metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Start PPL Thread workflow from in-memory face detections (NO DATABASE LOOKUP).

        This method accepts face detections directly, bypassing the database query.
        This is faster and avoids timing issues with session commits.

        Args:
            face_detections: List of face detection dicts (from Enhanced Logic V2)
            session_uuid: Session UUID to associate workflow with
            tolerance_percent: Position matching tolerance (5.0-50.0%). If None, fetches from orchestrator
            enable_quality_analysis: Enable best face quality analysis
            enable_age_detection: Enable age estimation (future enhancement)
            workflow_metadata: Additional workflow metadata

        Returns:
            Workflow execution results with person objects data in PPL Mini format
        """
        workflow_id = str(uuid.uuid4())
        
        # Fetch velocity sensitivity from orchestrator if not provided
        if tolerance_percent is None:
            tolerance_percent = await self._fetch_velocity_sensitivity_from_orchestrator()
        start_time = datetime.now()

        logger.info(
            "Starting PPL Thread workflow %s from in-memory faces (count: %d)",
            workflow_id,
            len(face_detections),
        )

        try:
            # Step 1: Validate session exists (optional for in-memory mode)
            # Try to validate but don't fail if session doesn't exist yet
            try:
                self._validate_session_exists(session_uuid)
                logger.info(f"✅ Session {session_uuid} validated successfully")
            except ValueError as session_error:
                logger.warning(
                    f"⚠️ Session {session_uuid} not found in database, continuing with in-memory mode: {session_error}"
                )
                # This is OK for in-memory mode - we have face_detections already

            # Step 2: Create workflow record with face count from memory
            self._create_workflow_record_from_faces(
                workflow_id, session_uuid, len(face_detections), tolerance_percent, workflow_metadata
            )

            # Step 3: Validate face detections have required fields
            if not face_detections:
                raise ValueError("No face detections provided")

            # Ensure face detections have position_x/position_y calculated
            for face in face_detections:
                if "position_x" not in face or "position_y" not in face:
                    # Calculate from bbox if not present
                    bbox_center_x = (face["bbox_x1"] + face["bbox_x2"]) / 2
                    bbox_center_y = (face["bbox_y1"] + face["bbox_y2"]) / 2
                    face["position_x"] = float(bbox_center_x)
                    face["position_y"] = float(bbox_center_y)

            logger.info("Validated %d face detections with positions", len(face_detections))

            # Step 4: Apply face grouping algorithm (Phase 2 core engine)
            logger.info(
                "Applying face grouping with %.1f%% tolerance", tolerance_percent
            )
            grouping_results = (
                await self.face_grouping_engine.apply_percentage_based_tracking(
                    face_detections, tolerance_percent
                )
            )

            logger.info(
                "Face grouping complete: %d faces → %d persons",
                len(face_detections),
                len(grouping_results["person_objects"]),
            )

            # Step 5: Store person objects and mappings in database (Phase 1 schema)
            logger.info(
                "Storing person objects and mappings for workflow %s",
                workflow_id,
            )
            person_id_mapping = self._store_person_objects_and_mappings(
                workflow_id, session_uuid, grouping_results
            )

            logger.info("Person objects stored successfully")

            # Step 6: Perform quality analysis if enabled
            best_quality_faces = {}
            if enable_quality_analysis:
                logger.info(
                    "Performing quality analysis for %d persons",
                    len(grouping_results["person_objects"]),
                )

                quality_analysis_results = (
                    self.quality_analyzer.select_best_face_per_person(
                        grouping_results["person_objects"],
                        face_detections,
                        grouping_results["face_mappings"],
                    )
                )

                best_quality_faces = quality_analysis_results["best_faces"]
                logger.info(
                    "Quality analysis complete for %d persons",
                    len(best_quality_faces),
                )

                # Store quality analysis results with representative faces and route data
                self._store_quality_analysis_results(
                    workflow_id,
                    session_uuid,
                    best_quality_faces,
                    person_id_mapping,
                    quality_rankings=quality_analysis_results.get("quality_rankings", {}),
                    face_mappings=grouping_results["face_mappings"],
                )

            # Step 7: Update workflow status to completed
            processing_time = (datetime.now() - start_time).total_seconds()
            self._complete_workflow(
                workflow_id,
                len(grouping_results["person_objects"]),
                len(face_detections),
                processing_time,
            )

            # Step 8: Format response to match PPL Meta Mini structure exactly
            response = self._format_ppl_mini_compatible_response(
                grouping_results, best_quality_faces, workflow_id, session_uuid,
                person_id_mapping=person_id_mapping,
            )

            logger.info(
                "PPL Thread workflow %s completed successfully in %.2f seconds (in-memory mode)",
                workflow_id,
                processing_time,
            )

            return response

        except Exception as e:
            # Update workflow status to failed
            error_message = f"Workflow failed: {str(e)}"
            logger.error(
                "PPL Thread workflow %s failed: %s", workflow_id, error_message
            )

            try:
                self._fail_workflow(workflow_id, error_message)
            except Exception as db_error:
                logger.error("Failed to update workflow failure status: %s", db_error)

            # Re-raise original exception
            raise RuntimeError(
                f"PPL Thread workflow {workflow_id} failed: {str(e)}"
            ) from e

    def get_person_objects_for_session(
        self, session_uuid: str, include_quality_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve existing person objects for a session.

        Returns results in PPL Meta Mini compatible format.

        Args:
            session_uuid: Session UUID to retrieve
            include_quality_analysis: Include quality analysis data

        Returns:
            Person objects data in PPL Mini compatible format
        """
        logger.info("Retrieving person objects for session %s", session_uuid)

        try:
            # Fetch person objects from database
            person_objects_data = self._get_stored_person_objects(
                session_uuid, include_quality_analysis
            )

            if not person_objects_data:
                return {
                    "success": False,
                    "message": "No person objects found for session",
                    "session_uuid": session_uuid,
                    "person_objects": [],
                    "statistics": {},
                }

            # Format response in PPL Mini compatible format
            response = self._format_stored_person_objects_response(
                person_objects_data, session_uuid
            )

            logger.info(
                "Retrieved person objects for session %s: %d persons",
                session_uuid,
                len(response.get("person_objects", [])),
            )

            return response

        except Exception as e:
            logger.error(
                "Failed to retrieve person objects for session %s: %s",
                session_uuid,
                str(e),
            )
            raise RuntimeError(f"Failed to retrieve person objects: {str(e)}") from e

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get detailed status information for a workflow.

        Args:
            workflow_id: Workflow ID to check

        Returns:
            Workflow status information
        """
        try:
            cursor = self.db.connection.cursor()

            query = """
            SELECT 
                workflow_id,
                session_uuid,
                status,
                input_face_count,
                output_person_count,
                tolerance_percent,
                processing_method,
                started_at,
                completed_at,
                error_message,
                metadata
            FROM person_workflows 
            WHERE workflow_id = %s
            """

            cursor.execute(query, (workflow_id,))
            result = cursor.fetchone()
            cursor.close()

            if not result:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Convert to dictionary
            columns = [desc[0] for desc in cursor.description]
            workflow_data = dict(zip(columns, result))

            return workflow_data

        except Exception as e:
            logger.error(
                "Failed to get workflow status for %s: %s", workflow_id, str(e)
            )
            raise RuntimeError(f"Failed to get workflow status: {str(e)}") from e

    def get_session_statistics(self, session_uuid: str) -> Dict[str, Any]:
        """
        Get statistics for person objects from latest workflow in a session.

        Args:
            session_uuid: Session UUID to analyze

        Returns:
            Statistical analysis from the most recent workflow
        """
        try:
            cursor = self.db.connection.cursor()

            # First, get the latest completed workflow for this session
            latest_workflow_query = """
            SELECT workflow_id
            FROM person_workflows
            WHERE session_uuid = %s
              AND status = 'completed'
            ORDER BY started_at DESC
            LIMIT 1
            """

            cursor.execute(latest_workflow_query, (session_uuid,))
            latest_workflow_result = cursor.fetchone()

            if not latest_workflow_result:
                cursor.close()
                return {
                    "session_uuid": session_uuid,
                    "total_persons": 0,
                    "total_faces": 0,
                    "has_person_objects": False,
                    "message": "No completed person objects workflows found",
                }

            latest_workflow_id = latest_workflow_result[0]
            logger.debug(
                "Using latest workflow %s for session %s statistics",
                latest_workflow_id,
                session_uuid,
            )

            # Get basic counts from the latest workflow only
            stats_query = """
            SELECT
                COUNT(DISTINCT po.person_id) as total_persons,
                COUNT(DISTINCT pfm.face_detection_id) as total_faces,
                AVG(po.face_count) as avg_faces_per_person,
                MAX(po.quality_score) as max_quality_score,
                AVG(po.quality_score) as avg_quality_score,
                COUNT(CASE WHEN po.best_face_id IS NOT NULL THEN 1 END)
                    as persons_with_quality_analysis
            FROM person_objects po
            LEFT JOIN person_face_mappings pfm ON po.person_id = pfm.person_id
            WHERE po.session_uuid = %s AND po.workflow_id = %s
            """

            cursor.execute(stats_query, (session_uuid, latest_workflow_id))
            stats_result = cursor.fetchone()
            cursor.close()

            if not stats_result or stats_result[0] == 0:
                return {
                    "session_uuid": session_uuid,
                    "total_persons": 0,
                    "total_faces": 0,
                    "has_person_objects": False,
                }

            # Calculate statistics
            columns = [desc[0] for desc in cursor.description]
            stats = dict(zip(columns, stats_result))

            # Calculate grouping efficiency
            grouping_efficiency = 0.0
            if stats["total_faces"] > 0:
                grouping_efficiency = (
                    (stats["total_faces"] - stats["total_persons"])
                    / stats["total_faces"]
                ) * 100

            max_quality_score = float(stats["max_quality_score"] or 0)
            avg_quality_score = float(stats["avg_quality_score"] or 0)
            has_quality_analysis = stats["persons_with_quality_analysis"] > 0

            return {
                "session_uuid": session_uuid,
                "total_persons": stats["total_persons"],
                "total_faces": stats["total_faces"],
                "avg_faces_per_person": round(
                    float(stats["avg_faces_per_person"] or 0), 2
                ),
                "grouping_efficiency": round(grouping_efficiency, 1),
                "max_quality_score": round(max_quality_score, 3),
                "avg_quality_score": round(avg_quality_score, 3),
                "has_quality_analysis": has_quality_analysis,
                "has_person_objects": True,
            }

        except Exception as e:
            logger.error(
                "Failed to get session statistics for %s: %s", session_uuid, str(e)
            )
            raise RuntimeError(f"Failed to get session statistics: {str(e)}") from e

    # Private workflow orchestration methods

    def _validate_session_exists(self, session_uuid: str) -> bool:
        """Validate that the session exists in face_detection_sessions table."""
        try:
            cursor = self.db.connection.cursor()

            query = (
                "SELECT COUNT(*) FROM face_detection_sessions WHERE session_uuid = %s"
            )
            cursor.execute(query, (session_uuid,))
            result = cursor.fetchone()
            cursor.close()

            if not result or result[0] == 0:
                raise ValueError(f"Face detection session {session_uuid} not found")

            return True

        except Exception as e:
            logger.error("Session validation failed for %s: %s", session_uuid, str(e))
            raise

    def _create_workflow_record(
        self,
        workflow_id: str,
        session_uuid: str,
        tolerance_percent: float,
        metadata: Optional[Dict],
    ) -> None:
        """Create initial workflow record in person_workflows table."""
        try:
            import json

            cursor = self.db.connection.cursor()

            # Get input face count
            face_count_query = """
            SELECT COUNT(*) FROM face_detections fd
            JOIN face_detection_sessions fds ON fd.media_id = fds.media_uuid
            WHERE fds.session_uuid = %s
            """
            cursor.execute(face_count_query, (session_uuid,))
            face_count_result = cursor.fetchone()
            input_face_count = face_count_result[0] if face_count_result else 0

            # Serialize metadata to JSON string for PostgreSQL storage
            metadata_json = json.dumps(metadata) if metadata else None

            # Insert workflow record
            insert_query = """
            INSERT INTO person_workflows (
                workflow_id, session_uuid, status, input_face_count, 
                tolerance_percent, processing_method, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    workflow_id,
                    session_uuid,
                    "processing",
                    input_face_count,
                    tolerance_percent,
                    "percentage_based_tracking",
                    metadata_json,
                ),
            )

            self.db.connection.commit()
            cursor.close()

            logger.debug(
                "Created workflow record %s for session %s", workflow_id, session_uuid
            )

        except Exception as e:
            logger.error("Failed to create workflow record: %s", str(e))
            self.db.connection.rollback()
            if "cursor" in locals():
                cursor.close()
            raise

    def _create_workflow_record_from_faces(
        self,
        workflow_id: str,
        session_uuid: str,
        face_count: int,
        tolerance_percent: float,
        metadata: Optional[Dict],
    ) -> None:
        """Create workflow record from in-memory face count (no DB query)."""
        try:
            import json

            cursor = self.db.connection.cursor()

            # Serialize metadata to JSON string for PostgreSQL storage
            metadata_json = json.dumps(metadata) if metadata else None

            # Insert workflow record
            insert_query = """
            INSERT INTO person_workflows (
                workflow_id, session_uuid, status, input_face_count, 
                tolerance_percent, processing_method, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                insert_query,
                (
                    workflow_id,
                    session_uuid,
                    "processing",
                    face_count,
                    tolerance_percent,
                    "percentage_based_tracking_in_memory",
                    metadata_json,
                ),
            )

            self.db.connection.commit()
            cursor.close()

            logger.debug(
                "Created workflow record %s for session %s (in-memory mode, %d faces)",
                workflow_id,
                session_uuid,
                face_count,
            )

        except Exception as e:
            logger.error("Failed to create workflow record: %s", str(e))
            self.db.connection.rollback()
            if "cursor" in locals():
                cursor.close()
            raise

    def _get_session_face_detections(self, session_uuid: str) -> List[Dict]:
        """Fetch face detections for session from database."""
        try:
            cursor = self.db.connection.cursor()

            query = """
            SELECT 
                fd.id,
                fd.frame_number,
                fd.bbox_x1,
                fd.bbox_y1,
                fd.bbox_x2,
                fd.bbox_y2,
                fd.confidence,
                fd.method,
                fd.created_at
            FROM face_detections fd
            JOIN face_detection_sessions fds ON fd.media_id = fds.media_uuid
            WHERE fds.session_uuid = %s
            ORDER BY fd.frame_number ASC, fd.created_at ASC
            """

            cursor.execute(query, (session_uuid,))
            results = cursor.fetchall()

            if not results:
                return []

            # Convert to list of dictionaries
            columns = [desc[0] for desc in cursor.description]
            face_detections = []

            for row in results:
                face_dict = dict(zip(columns, row))

                # Calculate position data from bbox (center point)
                bbox_center_x = (face_dict["bbox_x1"] + face_dict["bbox_x2"]) / 2
                bbox_center_y = (face_dict["bbox_y1"] + face_dict["bbox_y2"]) / 2
                face_dict["position_x"] = float(bbox_center_x)
                face_dict["position_y"] = float(bbox_center_y)

                face_detections.append(face_dict)

            logger.debug(
                "Fetched %d face detections for session %s",
                len(face_detections),
                session_uuid,
            )
            cursor.close()

            return face_detections

        except Exception as e:
            logger.error(
                "Failed to fetch face detections for session %s: %s",
                session_uuid,
                str(e),
            )
            if "cursor" in locals():
                cursor.close()
            raise

    def _store_person_objects_and_mappings(
        self, workflow_id: str, session_uuid: str, grouping_results: Dict
    ) -> Dict[str, str]:
        """Store person objects and face mappings in database (Phase 1 schema)."""
        try:
            logger.info(
                "Entering _store_person_objects_and_mappings for workflow %s",
                workflow_id,
            )
            cursor = self.db.connection.cursor()

            person_objects = grouping_results["person_objects"]
            face_mappings = grouping_results["face_mappings"]

            logger.info(
                "Retrieved person_objects count: %d, face_mappings count: %d",
                len(person_objects),
                len(face_mappings),
            )

            logger.debug(
                "Storing %d person objects and %d face mappings",
                len(person_objects),
                len(face_mappings),
            )

            # Store person objects - convert person_ids to UUIDs
            person_id_mapping = {}  # Map original person_id to UUID

            for person_obj in person_objects:
                # Generate UUID for person if it's not already a UUID
                original_person_id = person_obj["person_id"]
                if not self._is_valid_uuid(original_person_id):
                    person_uuid = str(uuid.uuid4())
                    person_id_mapping[original_person_id] = person_uuid
                else:
                    person_uuid = original_person_id
                    person_id_mapping[original_person_id] = person_uuid

                person_insert_query = """
                INSERT INTO person_objects (
                    person_id, session_uuid, workflow_id, face_count,
                    average_position_x, average_position_y, quality_score,
                    tracking_algorithm, tolerance_percent
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                avg_pos = person_obj["average_position"]

                # Info logging for the data being inserted
                logger.info(
                    f"Inserting person object: person_uuid={person_uuid}, avg_pos={avg_pos}"
                )
                logger.info(f"Person object data: {person_obj}")

                cursor.execute(
                    person_insert_query,
                    (
                        person_uuid,  # Use UUID instead of original person_id
                        session_uuid,
                        workflow_id,
                        person_obj["face_count"],
                        avg_pos["x"],
                        avg_pos["y"],
                        0.0,  # Will be updated by quality analysis
                        person_obj["tracking_algorithm"],
                        person_obj["tolerance_percent"],
                    ),
                )

            # Store face mappings - use UUID mapping
            logger.info(
                "Starting face mappings insertion - count: %d", len(face_mappings)
            )

            for idx, mapping in enumerate(face_mappings):
                # Early debug for problematic mappings
                if idx >= 3:  # Focus on mappings after the first 3 that work
                    logger.info("Processing face mapping %d: %s", idx, mapping)

                # Map original person_id to UUID
                try:
                    original_person_id = mapping["person_id"]
                    mapped_person_uuid = person_id_mapping.get(
                        original_person_id, original_person_id
                    )
                except Exception as field_error:
                    logger.error(
                        "Failed to access person_id in mapping %d: %s", idx, field_error
                    )
                    logger.error("Problematic mapping: %s", mapping)
                    raise

                # Debug log the mapping structure for the first few mappings
                if idx < 3:
                    logger.info("Face mapping %d: %s", idx, mapping)
                    logger.info("Mapped person UUID: %s", mapped_person_uuid)

                mapping_insert_query = """
                INSERT INTO person_face_mappings (
                    person_id, face_detection_id, match_type, match_distance,
                    frame_number, position_x, position_y
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                # Check each field individually for dict types
                mapping_values = (
                    mapped_person_uuid,  # Use mapped UUID
                    mapping["face_detection_id"],
                    mapping["match_type"],
                    mapping["match_distance"],
                    mapping["frame_number"],
                    mapping["position_x"],
                    mapping["position_y"],
                )

                # Debug the types of each value
                if idx < 3:
                    for i, val in enumerate(mapping_values):
                        if isinstance(val, dict):
                            logger.error("Dict found in position %d: %s", i, val)
                        else:
                            logger.info(
                                "Position %d type: %s, value: %s",
                                i,
                                type(val).__name__,
                                val,
                            )

                # Wrap cursor execution to catch the specific problematic mapping
                try:
                    cursor.execute(mapping_insert_query, mapping_values)
                except Exception as mapping_error:
                    logger.error(
                        "Failed to insert face mapping %d: %s", idx, mapping_error
                    )
                    logger.error("Problematic mapping data: %s", mapping)
                    logger.error("Problematic mapping values: %s", mapping_values)

                    # Check each value individually for dict types
                    for i, val in enumerate(mapping_values):
                        logger.error(
                            "Value %d: type=%s, value=%s",
                            i,
                            type(val).__name__,
                            repr(val),
                        )
                        if isinstance(val, dict):
                            logger.error("DICT DETECTED at position %d: %s", i, val)

                    raise  # Re-raise the error to maintain workflow failure

            logger.info("All face mappings processed successfully, committing...")
            try:
                self.db.connection.commit()
                logger.info("Database commit successful")
            except Exception as commit_error:
                logger.error("Database commit failed: %s", commit_error)
                raise

            try:
                cursor.close()
                logger.info("Cursor closed successfully")
            except Exception as cursor_error:
                logger.error("Cursor close failed: %s", cursor_error)
                raise

            logger.debug(
                "Successfully stored person objects and mappings for workflow %s",
                workflow_id,
            )

            return person_id_mapping

        except Exception as e:
            logger.error("Failed to store person objects and mappings: %s", str(e))
            self.db.connection.rollback()
            if "cursor" in locals():
                cursor.close()
            raise

    def _store_quality_analysis_results(
        self,
        workflow_id: str,
        session_uuid: str,
        best_quality_faces: Dict,
        person_id_mapping: Dict[str, str],
        quality_rankings: Dict = None,  # NEW: Quality rankings for representative faces
        face_mappings: List[Dict] = None,  # NEW: For complete route data
    ) -> None:
        """Update person objects with quality analysis results, representative faces, and route data."""
        try:
            logger.info(
                "Entering _store_quality_analysis_results for workflow %s",
                workflow_id,
            )
            logger.info(f"best_quality_faces type: {type(best_quality_faces)}")
            logger.info(
                f"best_quality_faces keys: {list(best_quality_faces.keys()) if best_quality_faces else 'None'}"
            )

            cursor = self.db.connection.cursor()

            face_detections = self._get_session_face_detections(session_uuid)
            face_detection_by_id = {
                str(face.get("id")): face
                for face in face_detections
                if isinstance(face, dict) and face.get("id")
            }

            # Update each person object with best face and quality score
            for person_id, quality_data in best_quality_faces.items():
                # Map internal person_id to database UUID
                actual_person_uuid = person_id_mapping.get(person_id, person_id)
                logger.info(
                    f"Processing person_id: {person_id} -> UUID: {actual_person_uuid}"
                )
                logger.info(f"quality_data type: {type(quality_data)}")
                logger.info(
                    f"quality_data keys: {list(quality_data.keys()) if isinstance(quality_data, dict) else 'Not a dict'}"
                )

                # Get top 5 representative faces for this person (for MVR quality display)
                representative_faces_data = []
                if quality_rankings and person_id in quality_rankings:
                    representative_faces_data = quality_rankings[person_id][:5]  # Top 5
                
                # Get ALL faces route data for this person (for overlay visualization)
                all_faces_route = []
                if face_mappings:
                    for mapping in face_mappings:
                        if mapping.get("person_id") == person_id:
                            face_det = face_detection_by_id.get(
                                str(mapping.get("face_detection_id", "")),
                                {},
                            )
                            all_faces_route.append({
                                "face_id": str(mapping.get("face_detection_id", "")),
                                "frame_number": face_det.get("frame_number", mapping.get("frame_number", 0)),
                                "bbox": [
                                    face_det.get("bbox_x1", 0),
                                    face_det.get("bbox_y1", 0),
                                    face_det.get("bbox_x2", 0),
                                    face_det.get("bbox_y2", 0),
                                ],
                                "confidence": face_det.get("confidence", 0.0),
                                "position": {
                                    "x": mapping.get("position_x", 0.0),
                                    "y": mapping.get("position_y", 0.0),
                                },
                            })
                    # Sort by frame number for proper route visualization
                    all_faces_route.sort(key=lambda x: x["frame_number"])
                
                import json
                update_query = """
                UPDATE person_objects 
                SET 
                    best_face_id = %s,
                    quality_score = %s,
                    estimated_age = %s,
                    distance_from_camera = %s,
                    representative_faces = %s,
                    all_faces_route_data = %s,
                    updated_at = NOW()
                WHERE person_id = %s AND workflow_id = %s
                """

                best_face_record = quality_data["face_record"]
                logger.info(f"best_face_record type: {type(best_face_record)}")
                logger.info(f"best_face_record: {best_face_record}")

                # Extract face ID safely
                if isinstance(best_face_record, dict) and "id" in best_face_record:
                    face_id = best_face_record["id"]
                elif hasattr(best_face_record, "id"):
                    face_id = best_face_record.id
                else:
                    face_id = str(best_face_record)
                    logger.warning(
                        f"Unexpected face_record format, using string conversion: {face_id}"
                    )

                estimated_age = None  # Future enhancement for age detection

                logger.info(f"About to execute query with face_id: {face_id}")
                logger.info(f"Storing {len(representative_faces_data)} representative faces and {len(all_faces_route)} route points")
                cursor.execute(
                    update_query,
                    (
                        face_id,
                        quality_data["quality_score"],
                        estimated_age,
                        None,  # Distance calculation - future enhancement
                        json.dumps(representative_faces_data),  # NEW: Top 5 quality faces
                        json.dumps(all_faces_route),  # NEW: Complete route data
                        actual_person_uuid,  # Use the mapped UUID instead of person_id
                        workflow_id,
                    ),
                )

            self.db.connection.commit()
            cursor.close()

            logger.debug(
                "Updated quality analysis for %d persons in workflow %s",
                len(best_quality_faces),
                workflow_id,
            )

        except Exception as e:
            logger.error("Failed to store quality analysis results: %s", str(e))
            self.db.connection.rollback()
            if "cursor" in locals():
                cursor.close()
            raise

    def _complete_workflow(
        self,
        workflow_id: str,
        person_count: int,
        face_count: int,
        processing_time: float,
    ) -> None:
        """Mark workflow as completed with final statistics."""
        try:
            cursor = self.db.connection.cursor()

            update_query = """
            UPDATE person_workflows 
            SET 
                status = %s,
                output_person_count = %s,
                completed_at = NOW(),
                metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
            WHERE workflow_id = %s
            """

            processing_metadata = {
                "processing_time_seconds": round(processing_time, 3),
                "faces_processed": face_count,
                "persons_created": person_count,
                "completed_timestamp": datetime.now().isoformat(),
            }

            cursor.execute(
                update_query,
                (
                    "completed",
                    person_count,
                    json.dumps(processing_metadata),
                    workflow_id,
                ),
            )

            self.db.connection.commit()
            cursor.close()

            logger.debug("Marked workflow %s as completed", workflow_id)

        except Exception as e:
            logger.error("Failed to complete workflow %s: %s", workflow_id, str(e))
            self.db.connection.rollback()
            if "cursor" in locals():
                cursor.close()
            raise

    def _fail_workflow(self, workflow_id: str, error_message: str) -> None:
        """Mark workflow as failed with error details."""
        try:
            cursor = self.db.connection.cursor()

            update_query = """
            UPDATE person_workflows 
            SET 
                status = %s,
                error_message = %s,
                completed_at = NOW()
            WHERE workflow_id = %s
            """

            cursor.execute(update_query, ("failed", error_message, workflow_id))

            self.db.connection.commit()
            cursor.close()

            logger.debug("Marked workflow %s as failed", workflow_id)

        except Exception as e:
            logger.error(
                "Failed to update workflow failure status for %s: %s",
                workflow_id,
                str(e),
            )
            if "cursor" in locals():
                cursor.close()
            # Don't raise here to avoid masking original error

    def _format_ppl_mini_compatible_response(
        self,
        grouping_results: Dict,
        best_quality_faces: Dict,
        workflow_id: str,
        session_uuid: str,
        person_id_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Format response to exactly match PPL Meta Mini FaceGroupingEngine output structure.

        This ensures 100% compatibility with existing PPL Mini integrations.
        """
        person_objects = grouping_results["person_objects"]
        face_mappings = grouping_results["face_mappings"]
        statistics = grouping_results["statistics"]

        logger.debug(
            "Formatting PPL Mini compatible response for %d persons",
            len(person_objects),
        )

        # Create group tracking list (matching PPL Mini format exactly)
        group_tracking_list = []
        for person in person_objects:
            person_id = person["person_id"]

            # Get all face IDs for this person from mappings (convert to strings)
            person_face_ids = [
                str(fm["face_detection_id"])
                for fm in face_mappings
                if fm["person_id"] == person_id
            ]

            group_tracking_list.append(
                {
                    "Merged_Group_ID": person_id,
                    "Original_Group_IDs": person_face_ids,
                    "Face_Count": person["face_count"],
                    "Average_Position": person["average_position"],
                    "Y_Coordinate_Based": False,
                    "Tracking_Based": True,
                    "Tolerance_Percent": person["tolerance_percent"],
                    "Merge_History": [],  # PPL Mini compatibility
                }
            )

        # Create best quality faces dict (matching PPL Mini format)
        best_quality_formatted = {}
        for person_id, quality_data in best_quality_faces.items():
            # Extract bbox from face record
            face_record = quality_data["face_record"]
            bbox = [
                face_record.get("bbox_x1", 0),
                face_record.get("bbox_y1", 0),
                face_record.get("bbox_x2", 0),
                face_record.get("bbox_y2", 0),
            ]

            best_quality_formatted[person_id] = {
                "face_id": str(face_record["id"]),
                "frame_number": face_record.get("frame_number", 0),
                "quality_score": quality_data["quality_score"],
                "bbox": bbox,
                "age_detection": {"estimated_age": "Unknown"},  # Future enhancement
                "distance": 0.0,  # Future enhancement
            }

        # Create summary statistics (matching PPL Mini format exactly)
        summary = {
            "total_groups": statistics["total_persons"],
            "total_persons": statistics["total_persons"],  # Added for compatibility
            "original_unique_faces": statistics["total_faces"],
            "merged_groups_count": statistics["total_persons"],
            "total_detections": statistics["total_faces"],
            "frames_processed": statistics["frames_processed"],
            "grouping_algorithm": "percentage_based_tracking",
            "tolerance_percent": statistics["tolerance_percent"],
            "tracked_faces": statistics["tracked_faces"],
            "new_faces": statistics["new_faces"],
            "merge_iterations": 0,  # PPL Mini compatibility
        }

        # Create classified faces (face mappings in PPL Mini format)
        classified_faces = []
        for mapping in face_mappings:
            classified_faces.append(
                {
                    "face_id": str(mapping["face_detection_id"]),
                    "person_id": mapping["person_id"],
                    "match_type": mapping["match_type"],
                    "match_distance": mapping["match_distance"],
                    "frame_number": mapping["frame_number"],
                    "position": {
                        "x": mapping["position_x"],
                        "y": mapping["position_y"],
                    },
                }
            )

        # Format person_objects for in-memory processing (vmeta integration)
        person_objects_formatted = []
        for person in person_objects:
            person_id = person["person_id"]
            
            # Get face IDs for this person
            person_face_ids = [
                str(fm["face_detection_id"])
                for fm in face_mappings
                if fm["person_id"] == person_id
            ]
            
            # Get best quality face data
            best_face_data = best_quality_formatted.get(person_id, {})
            
            person_objects_formatted.append(
                {
                    "person_id": person_id,
                    # Real DB UUID minted by `_store_person_objects_and_mappings`.
                    # Downstream consumers (orchestrator/vmeta) need this to keep
                    # MVR rows linkable across recordings instead of generating a
                    # fresh UUID every time the synthetic label is parsed.
                    "person_uuid": (person_id_mapping or {}).get(person_id),
                    "person_object_uuid": (person_id_mapping or {}).get(person_id),
                    "workflow_id": workflow_id,
                    "session_uuid": session_uuid,
                    "face_count": person["face_count"],
                    "face_ids": person_face_ids,
                    "average_position": person["average_position"],
                    "quality_score": person.get("quality_score", 0.0),
                    "best_face_id": best_face_data.get("face_id"),
                    "best_face_frame": best_face_data.get("frame_number"),
                    "best_face_bbox": best_face_data.get("bbox", []),
                    "tracking_metadata": {
                        "tolerance_percent": person["tolerance_percent"],
                        "tracking_algorithm": person.get(
                            "tracking_algorithm", "percentage_based_tracking"
                        ),
                        "created_at": datetime.now().isoformat(),
                    },
                }
            )

        # Final response in PPL Meta Mini compatible format
        response = {
            "workflow_id": workflow_id,
            "session_uuid": session_uuid,
            "success": True,
            "original_groups": statistics["total_faces"],
            "merged_groups": statistics["total_persons"],
            "group_tracking": group_tracking_list,
            "summary": summary,
            "statistics": summary,  # Duplicate for compatibility
            "best_quality_faces": best_quality_formatted,
            "classified_faces": classified_faces,
            "person_objects": person_objects_formatted,  # ← NEW: Full person objects for in-memory processing
            "processing_timestamp": datetime.now().isoformat(),
            "workflow_type": "ppl_thread_person_objects",
        }

        logger.debug(
            "PPL Mini compatible response formatted successfully with %d person objects",
            len(person_objects_formatted)
        )

        return response

    def _get_stored_person_objects(
        self, session_uuid: str, include_quality_analysis: bool = True
    ) -> Optional[Dict]:
        """Retrieve stored person objects data from database."""
        try:
            cursor = self.db.connection.cursor()

            # Get person objects with mappings
            person_objects_query = """
            SELECT 
                po.person_id,
                po.workflow_id,
                po.face_count,
                po.average_position_x,
                po.average_position_y,
                po.quality_score,
                po.best_face_id,
                po.estimated_age,
                po.distance_from_camera,
                po.representative_faces,
                po.all_faces_route_data,
                po.tracking_algorithm,
                po.tolerance_percent,
                po.created_at,
                po.updated_at,
                ARRAY_AGG(pfm.face_detection_id ORDER BY pfm.frame_number) as face_ids,
                ARRAY_AGG(pfm.match_type ORDER BY pfm.frame_number) as match_types,
                ARRAY_AGG(pfm.match_distance ORDER BY pfm.frame_number) as match_distances,
                ARRAY_AGG(pfm.frame_number ORDER BY pfm.frame_number) as frame_numbers,
                ARRAY_AGG(pfm.position_x ORDER BY pfm.frame_number) as position_x_values,
                ARRAY_AGG(pfm.position_y ORDER BY pfm.frame_number) as position_y_values
            FROM person_objects po
            LEFT JOIN person_face_mappings pfm ON po.person_id = pfm.person_id
            WHERE po.session_uuid = %s
            AND po.workflow_id = (
                SELECT workflow_id FROM person_workflows
                WHERE session_uuid = %s AND completed_at IS NOT NULL
                ORDER BY completed_at DESC LIMIT 1
            )
            GROUP BY po.person_id, po.workflow_id, po.face_count, po.average_position_x,
                     po.average_position_y, po.quality_score, po.best_face_id,
                     po.estimated_age, po.distance_from_camera, po.representative_faces,
                     po.all_faces_route_data, po.tracking_algorithm,
                     po.tolerance_percent, po.created_at, po.updated_at
            ORDER BY po.created_at DESC
            """

            cursor.execute(person_objects_query, (session_uuid, session_uuid))
            results = cursor.fetchall()

            if not results:
                return None

            # Convert to structured data
            columns = [desc[0] for desc in cursor.description]
            person_objects_data = []

            for row in results:
                person_data = dict(zip(columns, row))
                person_objects_data.append(person_data)

            cursor.close()
            return {"person_objects": person_objects_data, "session_uuid": session_uuid}

        except Exception as e:
            logger.error(
                "Failed to get stored person objects for session %s: %s",
                session_uuid,
                str(e),
            )
            if "cursor" in locals():
                cursor.close()
            raise

    def _format_stored_person_objects_response(
        self, person_objects_data: Dict, session_uuid: str
    ) -> Dict[str, Any]:
        """Format stored person objects data in PPL Mini compatible format."""
        try:
            person_objects = person_objects_data["person_objects"]

            if not person_objects:
                return {
                    "success": False,
                    "message": "No person objects data found",
                    "session_uuid": session_uuid,
                    "person_objects": [],
                    "statistics": {},
                }

            # Reconstruct group tracking and statistics
            group_tracking_list = []
            classified_faces = []
            person_objects_formatted = []
            total_faces = 0

            for person_data in person_objects:
                person_id = person_data["person_id"]
                face_ids = person_data["face_ids"]
                face_count = len(face_ids) if face_ids else 0
                total_faces += face_count

                representative_faces = person_data.get("representative_faces") or []
                if isinstance(representative_faces, str):
                    try:
                        representative_faces = json.loads(representative_faces)
                    except (TypeError, ValueError):
                        representative_faces = []
                if representative_faces is None:
                    representative_faces = []

                all_faces_route_data = person_data.get("all_faces_route_data") or []
                if isinstance(all_faces_route_data, str):
                    try:
                        all_faces_route_data = json.loads(all_faces_route_data)
                    except (TypeError, ValueError):
                        all_faces_route_data = []
                if all_faces_route_data is None:
                    all_faces_route_data = []

                route_points = []
                for route_face in all_faces_route_data:
                    position = route_face.get("position") or {}
                    route_points.append(
                        {
                            "face_id": route_face.get("face_id"),
                            "frame_number": route_face.get("frame_number", 0),
                            "center_x": float(position.get("x", 0.0)),
                            "center_y": float(position.get("y", 0.0)),
                            "bbox": route_face.get("bbox", []),
                            "confidence": route_face.get("confidence", 0.0),
                        }
                    )

                route_points.sort(key=lambda item: item.get("frame_number", 0))

                if route_points:
                    temporal_span = {
                        "start_frame": route_points[0].get("frame_number", 0),
                        "end_frame": route_points[-1].get("frame_number", 0),
                        "duration_frames": route_points[-1].get("frame_number", 0)
                        - route_points[0].get("frame_number", 0),
                    }
                    xs = [float(point.get("center_x", 0.0)) for point in route_points]
                    ys = [float(point.get("center_y", 0.0)) for point in route_points]
                    spatial_bounds = {
                        "min_x": min(xs),
                        "max_x": max(xs),
                        "min_y": min(ys),
                        "max_y": max(ys),
                    }
                else:
                    temporal_span = {}
                    spatial_bounds = {}

                # Group tracking entry
                group_tracking_list.append(
                    {
                        "Merged_Group_ID": person_id,
                        "Original_Group_IDs": face_ids or [],
                        "Face_Count": face_count,
                        "Average_Position": {
                            "x": float(person_data["average_position_x"]),
                            "y": float(person_data["average_position_y"]),
                        },
                        "Y_Coordinate_Based": False,
                        "Tracking_Based": True,
                        "Tolerance_Percent": float(person_data["tolerance_percent"]),
                        "Merge_History": [],
                    }
                )

                # Classified faces
                if face_ids:
                    for i, face_id in enumerate(face_ids):
                        classified_faces.append(
                            {
                                "face_id": face_id,
                                "person_id": person_id,
                                "match_type": (
                                    person_data["match_types"][i]
                                    if person_data["match_types"]
                                    else "unknown"
                                ),
                                "match_distance": (
                                    float(person_data["match_distances"][i])
                                    if person_data["match_distances"]
                                    else 0.0
                                ),
                                "frame_number": (
                                    person_data["frame_numbers"][i]
                                    if person_data["frame_numbers"]
                                    else 0
                                ),
                                "position": {
                                    "x": (
                                        float(person_data["position_x_values"][i])
                                        if person_data["position_x_values"]
                                        else 0.0
                                    ),
                                    "y": (
                                        float(person_data["position_y_values"][i])
                                        if person_data["position_y_values"]
                                        else 0.0
                                    ),
                                },
                            }
                        )

            # Summary statistics
            summary = {
                "total_groups": len(person_objects),
                "original_unique_faces": total_faces,
                "merged_groups_count": len(person_objects),
                "total_detections": total_faces,
                "grouping_algorithm": "percentage_based_tracking",
                "tolerance_percent": (
                    person_objects[0]["tolerance_percent"] if person_objects else 20.0
                ),
            }

            # Best quality faces (if available)
            best_quality_faces = {}
            for person_data in person_objects:
                if person_data["best_face_id"]:
                    person_id = person_data["person_id"]
                    best_quality_faces[person_id] = {
                        "face_id": person_data["best_face_id"],
                        "quality_score": float(person_data["quality_score"]),
                        "estimated_age": person_data["estimated_age"] or "Unknown",
                        "distance": float(person_data["distance_from_camera"] or 0.0),
                    }

                representative_faces = person_data.get("representative_faces") or []
                if isinstance(representative_faces, str):
                    try:
                        representative_faces = json.loads(representative_faces)
                    except (TypeError, ValueError):
                        representative_faces = []
                if representative_faces is None:
                    representative_faces = []

                all_faces_route_data = person_data.get("all_faces_route_data") or []
                if isinstance(all_faces_route_data, str):
                    try:
                        all_faces_route_data = json.loads(all_faces_route_data)
                    except (TypeError, ValueError):
                        all_faces_route_data = []
                if all_faces_route_data is None:
                    all_faces_route_data = []

                route_by_face_id = {}
                for route_face in all_faces_route_data:
                    if not isinstance(route_face, dict):
                        continue
                    route_face_id = route_face.get("face_id")
                    if route_face_id:
                        route_by_face_id[str(route_face_id)] = route_face

                enriched_representative_faces = []
                for face in representative_faces:
                    if not isinstance(face, dict):
                        continue

                    enriched_face = dict(face)
                    face_data = dict(enriched_face.get("face_data") or {})
                    if not face_data:
                        route_face = route_by_face_id.get(str(enriched_face.get("face_id")))
                        if route_face:
                            position = route_face.get("position") or {}
                            face_data = {
                                "id": route_face.get("face_id"),
                                "frame_number": route_face.get("frame_number"),
                                "bbox": route_face.get("bbox") or [],
                                "confidence": route_face.get("confidence"),
                                "center_x": position.get("x"),
                                "center_y": position.get("y"),
                            }

                    if face_data:
                        enriched_face["face_data"] = face_data
                    enriched_representative_faces.append(enriched_face)

                representative_faces = enriched_representative_faces

                best_face_frame = None
                best_face_bbox = []
                if representative_faces:
                    first_face = representative_faces[0] or {}
                    face_data = first_face.get("face_data") or {}
                    best_face_frame = face_data.get("frame_number")
                    best_face_bbox = face_data.get("bbox", [])

                person_objects_formatted.append(
                    {
                        "person_id": person_data["person_id"],
                        "workflow_id": person_data["workflow_id"],
                        "session_uuid": session_uuid,
                        "face_count": person_data["face_count"],
                        "face_ids": face_ids or [],
                        "average_position": {
                            "x": float(person_data["average_position_x"]),
                            "y": float(person_data["average_position_y"]),
                        },
                        "quality_score": float(person_data.get("quality_score") or 0.0),
                        "best_face_id": person_data.get("best_face_id"),
                        "best_face_frame": best_face_frame,
                        "best_face_bbox": best_face_bbox,
                        "representative_faces": representative_faces,
                        "movement_tracking": {
                            "route_points": all_faces_route_data,
                            "movement_statistics": {
                                "total_route_points": len(all_faces_route_data),
                            },
                        },
                        "tracking_metadata": {
                            "tolerance_percent": float(person_data["tolerance_percent"]),
                            "tracking_algorithm": person_data.get(
                                "tracking_algorithm", "percentage_based_tracking"
                            ),
                            "created_at": person_data["created_at"].isoformat()
                            if person_data.get("created_at")
                            else None,
                        },
                        "temporal_span": temporal_span,
                        "spatial_bounds": spatial_bounds,
                        "demographics": {
                            "age_estimate": person_data.get("estimated_age"),
                        },
                    }
                )

            return {
                "workflow_id": person_objects[0]["workflow_id"],
                "session_uuid": session_uuid,
                "success": True,
                "original_groups": total_faces,
                "merged_groups": len(person_objects),
                "total_persons": len(person_objects),  # Explicit person count
                "total_faces": total_faces,  # Fixed: explicit face count
                "group_tracking": group_tracking_list,
                "summary": summary,
                "statistics": summary,
                "best_quality_faces": best_quality_faces,
                "classified_faces": classified_faces,
                "person_objects": person_objects_formatted,
                "processing_timestamp": datetime.now().isoformat(),
                "workflow_type": "ppl_thread_person_objects",
            }

        except Exception as e:
            logger.error("Failed to format stored person objects response: %s", str(e))
            raise
