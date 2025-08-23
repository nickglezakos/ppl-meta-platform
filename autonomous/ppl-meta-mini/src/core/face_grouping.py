"""
Advanced Face Grouping Engine - Core algorithm implementation.
"""

import math
from typing import Any, Dict, List

import cv2
import numpy as np
import pandas as pd


class FaceGroupingEngine:
    """
    Advanced face grouping engine that merges face groups when
    unique face IDs exceed maximum faces per frame.
    """

    def __init__(self):
        """Initialize the face grouping engine."""
        self.best_sharpness = 0.0
        self.default_noise = 10.0  # Default noise baseline
        self.default_exposure = 128.0  # Default exposure baseline
        self.default_contrast = 50.0  # Default contrast baseline

    def calculate_sharpness(self, image):
        """Calculate image sharpness using Laplacian variance."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def calculate_noise(self, image):
        """Calculate image noise using standard deviation of the Laplacian."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return np.std(laplacian)

    def calculate_exposure(self, image):
        """Calculate image exposure using mean brightness."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.mean(gray)

    def calculate_contrast(self, image):
        """Calculate image contrast using standard deviation of pixels."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return np.std(gray)

    def score_image(self, image):
        """
        Score image quality based on sharpness, noise, exposure, and contrast.
        Returns a quality score between 0 and 1 (higher is better).
        """
        sharpness = self.calculate_sharpness(image)
        noise = self.calculate_noise(image)
        exposure = self.calculate_exposure(image)
        contrast = self.calculate_contrast(image)

        # Update the best sharpness value if a larger one is found
        if sharpness > self.best_sharpness:
            self.best_sharpness = sharpness

        # Avoid division by zero
        best_sharpness = max(self.best_sharpness, 1.0)
        default_noise = max(self.default_noise, 1.0)
        default_exposure = max(self.default_exposure, 1.0)
        default_contrast = max(self.default_contrast, 1.0)

        # Normalize each metric
        normalized_sharpness = sharpness / best_sharpness
        normalized_noise = 1 - (noise / default_noise) if default_noise != 0 else 1
        normalized_exposure = exposure / default_exposure
        normalized_contrast = contrast / default_contrast

        # Combine normalized scores into a final quality score (example weights)
        quality_score = (
            (normalized_sharpness * 0.4)
            + (normalized_noise * 0.2)
            + (normalized_exposure * 0.2)
            + (normalized_contrast * 0.2)
        )

        # Round the quality score to the third digit
        return round(quality_score, 3)

    def apply_advanced_grouping(
        self,
        df: pd.DataFrame,
        max_faces_per_frame: int = None,  # Accept parameter but calculate dynamically
        proximity_threshold: float = 50.0,  # Accept but not used in notebook algorithm
        video_path: str = None,  # Add video path for quality analysis
    ) -> Dict[str, Any]:
        """
        Apply advanced face grouping algorithm using percentage-based tolerance matching.
        This is the exact notebook implementation for face classification and tracking.

        Algorithm:
        1. Process frames chronologically
        2. For first frame, assign new IDs to all faces
        3. For subsequent frames, try to match faces to existing tracks using percentage tolerance
        4. Use 20% tolerance for X, Y, and distance coordinates
        5. Calculate combined distance metric for ranking matches
        """
        # Store face data for later quality analysis
        self.stored_face_data = df.to_dict("records") if hasattr(df, "to_dict") else df

        # Normalize column names to handle both formats
        if "face_id" in df.columns and "Face_ID" not in df.columns:
            df = df.rename(
                columns={
                    "face_id": "Face_ID",
                    "frame_number": "Frame_Number",
                    "position_x": "Position_X",
                    "position_y": "Position_Y",
                }
            )

        # Handle notebook format (different column names)
        if "ID" in df.columns and "Face_ID" not in df.columns:
            df = df.rename(
                columns={
                    "ID": "Face_ID",
                    "Frame": "Frame_Number",
                    "Position X": "Position_X",
                    "Position Y": "Position_Y",
                }
            )

        print("🔍 === FACE CLASSIFICATION AND TRACKING ===")
        print("📊 Assigning unique IDs and tracking faces across frames")
        print("=" * 70)

        # Group faces by frame and sort chronologically
        frames_with_faces = []
        for frame_number in sorted(df["Frame_Number"].unique()):
            frame_faces = df[df["Frame_Number"] == frame_number].to_dict("records")
            if frame_faces:
                frames_with_faces.append(
                    {"frame_number": frame_number, "faces": frame_faces}
                )

        if not frames_with_faces:
            print("⚠️ No frames with faces found for classification")
            return {
                "original_groups": 0,
                "merged_groups": 0,
                "group_tracking": [],
                "summary": {  # Added summary field
                    "total_groups": 0,
                    "original_unique_faces": 0,
                    "merged_groups_count": 0,
                    "total_detections": 0,
                    "frames_processed": 0,
                    "max_faces_per_frame": 0,
                    "grouping_algorithm": "percentage_based_tracking",
                    "tolerance_percent": 20.0,
                    "tracked_faces": 0,
                    "new_faces": 0,
                    "merge_iterations": 0,
                },
                "statistics": {
                    "original_unique_faces": 0,
                    "merged_groups_count": 0,
                    "total_detections": 0,
                    "frames_processed": 0,
                    "max_faces_per_frame": 0,
                    "grouping_algorithm": "percentage_based_tracking",
                    "tolerance_percent": 20.0,
                    "tracked_faces": 0,
                    "new_faces": 0,
                    "merge_iterations": 0,
                },
                "regrouped_data": [],
                "merge_history": [],
                "id_mapping": {},
                "classified_faces": [],
                "best_quality_faces": {},
            }

        print(f"📋 Processing {len(frames_with_faces)} frames chronologically...")

        # Tracking data structures
        active_tracks = {}  # classification_id -> face_info
        next_classification_id = 1
        classified_faces = []

        # Tolerance for matching (20% for coordinates and distance)
        tolerance_percent = 20.0

        # Statistics
        tracked_faces = 0
        new_faces = 0

        # Process frames chronologically
        for frame_index, frame_data in enumerate(frames_with_faces):
            frame_number = frame_data["frame_number"]
            frame_faces = frame_data["faces"]

            print(
                f"\n🎯 Frame {frame_number} ({frame_index + 1}/{len(frames_with_faces)})"
            )
            print(f"   Found {len(frame_faces)} faces to classify")

            if frame_index == 0:
                # First frame: assign new IDs to all faces
                for face in frame_faces:
                    classification_id = next_classification_id
                    next_classification_id += 1

                    # Store track information
                    active_tracks[classification_id] = {
                        "classification_id": classification_id,
                        "position": {"x": face["Position_X"], "y": face["Position_Y"]},
                        "last_seen_frame": frame_number,
                        "original_face": face,
                    }

                    # Store classification result
                    classified_faces.append(
                        {
                            "classification_id": classification_id,
                            "frame_number": frame_number,
                            "position": {
                                "x": face["Position_X"],
                                "y": face["Position_Y"],
                            },
                            "original_face": face,
                            "match_type": "new_track",
                        }
                    )

                    print(
                        f"   🆕 New track {classification_id} at ({face['Position_X']:.1f}, {face['Position_Y']:.1f})"
                    )

                new_faces += len(frame_faces)
                print(f"   ✅ Created {len(frame_faces)} new tracks")

            else:
                # Subsequent frames: try to match faces to existing tracks
                face_matches = []

                for face in frame_faces:
                    face_x = face["Position_X"]
                    face_y = face["Position_Y"]

                    # Calculate distances to all active tracks
                    candidate_matches = []

                    for track_id, track_info in active_tracks.items():
                        track_x = track_info["position"]["x"]
                        track_y = track_info["position"]["y"]

                        # Calculate coordinate differences
                        x_diff = abs(face_x - track_x)
                        y_diff = abs(face_y - track_y)

                        # Calculate tolerance thresholds (20% of the coordinate values)
                        x_tolerance = track_x * (tolerance_percent / 100)
                        y_tolerance = track_y * (tolerance_percent / 100)

                        # Check if within tolerance
                        x_match = x_diff <= x_tolerance
                        y_match = y_diff <= y_tolerance

                        # Calculate Euclidean distance
                        euclidean_distance = math.sqrt(x_diff**2 + y_diff**2)

                        # Distance tolerance (20% of the average coordinate)
                        avg_coord = (track_x + track_y) / 2
                        distance_tolerance = avg_coord * (tolerance_percent / 100)
                        distance_match = euclidean_distance <= distance_tolerance

                        # Combine matching criteria
                        is_match = x_match and y_match and distance_match

                        if is_match:
                            # Calculate combined distance metric for ranking
                            combined_distance = (
                                (x_diff / max(x_tolerance, 1))
                                + (y_diff / max(y_tolerance, 1))
                                + (euclidean_distance / max(distance_tolerance, 1))
                            )

                            candidate_matches.append(
                                {
                                    "track_id": track_id,
                                    "combined_distance": combined_distance,
                                    "x_diff": x_diff,
                                    "y_diff": y_diff,
                                    "euclidean_distance": euclidean_distance,
                                    "match_details": {
                                        "x_match": x_match,
                                        "y_match": y_match,
                                        "distance_match": distance_match,
                                        "tolerances": {
                                            "x_tolerance": x_tolerance,
                                            "y_tolerance": y_tolerance,
                                            "distance_tolerance": distance_tolerance,
                                        },
                                    },
                                }
                            )

                    # Sort by combined distance (closer is better)
                    candidate_matches.sort(key=lambda x: x["combined_distance"])

                    if candidate_matches:
                        # Best match found
                        best_match = candidate_matches[0]
                        track_id = best_match["track_id"]

                        face_matches.append(
                            {
                                "face": face,
                                "track_id": track_id,
                                "match_details": best_match,
                            }
                        )

                        print(
                            f"   ✅ Matched face at ({face_x:.1f}, {face_y:.1f}) "
                            f"to track {track_id} (distance: {best_match['combined_distance']:.2f})"
                        )

                    else:
                        # No match found, create new track
                        classification_id = next_classification_id
                        next_classification_id += 1

                        face_matches.append(
                            {
                                "face": face,
                                "track_id": classification_id,
                                "match_details": {"new_track": True},
                            }
                        )

                        print(
                            f"   🆕 New track {classification_id} at ({face_x:.1f}, {face_y:.1f}) (no matches)"
                        )

                # Apply matches and update tracks
                for match in face_matches:
                    face = match["face"]
                    track_id = match["track_id"]
                    match_details = match["match_details"]

                    if "new_track" in match_details:
                        # Create new track
                        active_tracks[track_id] = {
                            "classification_id": track_id,
                            "position": {
                                "x": face["Position_X"],
                                "y": face["Position_Y"],
                            },
                            "last_seen_frame": frame_number,
                            "original_face": face,
                        }

                        classified_faces.append(
                            {
                                "classification_id": track_id,
                                "frame_number": frame_number,
                                "position": {
                                    "x": face["Position_X"],
                                    "y": face["Position_Y"],
                                },
                                "original_face": face,
                                "match_type": "new_track",
                            }
                        )

                        new_faces += 1

                    else:
                        # Update existing track
                        active_tracks[track_id]["position"] = {
                            "x": face["Position_X"],
                            "y": face["Position_Y"],
                        }
                        active_tracks[track_id]["last_seen_frame"] = frame_number

                        classified_faces.append(
                            {
                                "classification_id": track_id,
                                "frame_number": frame_number,
                                "position": {
                                    "x": face["Position_X"],
                                    "y": face["Position_Y"],
                                },
                                "original_face": face,
                                "match_type": "tracked",
                                "match_distance": match_details["combined_distance"],
                            }
                        )

                        tracked_faces += 1

                print(
                    f"   📊 Processed {len(face_matches)} faces in frame {frame_number}"
                )

        # Create final results
        unique_ids = sorted(
            list(set(cf["classification_id"] for cf in classified_faces))
        )

        print(f"\n📈 === CLASSIFICATION COMPLETE ===")
        print(f"🏷️ Unique classification IDs: {len(unique_ids)}")
        print(f"👤 Total face instances: {len(classified_faces)}")
        print(f"🎯 Tracked faces: {tracked_faces}")
        print(f"🆕 New faces: {new_faces}")
        print(f"📊 Tolerance used: {tolerance_percent}%")

        # Create updated DataFrame with new classifications
        df_regrouped = df.copy()

        # Create mapping from original face data to new classification IDs
        id_mapping = {}
        for classified_face in classified_faces:
            original_face = classified_face["original_face"]
            original_id = original_face["Face_ID"]
            new_id = classified_face["classification_id"]
            id_mapping[original_id] = new_id

        df_regrouped["Original_Face_ID"] = df_regrouped["Face_ID"]
        df_regrouped["Merged_Group_ID"] = df_regrouped["Original_Face_ID"].map(
            id_mapping
        )
        df_regrouped["Face_ID"] = df_regrouped["Merged_Group_ID"]

        # Convert numpy types to native Python types for JSON serialization
        def convert_numpy_types(obj):
            """Convert numpy types to native Python types recursively"""
            import numpy as np

            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_numpy_types(item) for item in obj)
            elif pd.isna(obj):
                return None
            return obj

        # Convert the regrouped data to ensure JSON serialization
        regrouped_data_records = df_regrouped.to_dict("records")
        regrouped_data_records = convert_numpy_types(regrouped_data_records)

        # Create group tracking in the expected format
        group_tracking_list = []
        for classification_id in unique_ids:
            group_faces = [
                f
                for f in classified_faces
                if f["classification_id"] == classification_id
            ]
            face_count = len(group_faces)

            # Calculate average position
            avg_x = sum(f["position"]["x"] for f in group_faces) / face_count
            avg_y = sum(f["position"]["y"] for f in group_faces) / face_count

            group_tracking_list.append(
                {
                    "Merged_Group_ID": str(classification_id),
                    "Original_Group_IDs": [
                        str(f["original_face"]["Face_ID"]) for f in group_faces
                    ],
                    "Face_Count": int(face_count),  # Ensure int type
                    "Average_Position": {
                        "x": float(avg_x),
                        "y": float(avg_y),
                    },  # Ensure float types
                    "Y_Coordinate_Based": False,  # This uses percentage-based matching
                    "Tracking_Based": True,
                    "Tolerance_Percent": float(tolerance_percent),  # Ensure float type
                    "Merge_History": [],
                }
            )

        # Ensure all statistics are native Python types
        original_groups_count = int(df["Face_ID"].nunique())
        merged_groups_count = int(len(unique_ids))
        total_detections = int(len(df))
        frames_processed = int(len(frames_with_faces))
        max_faces_per_frame = int(df.groupby("Frame_Number").size().max())

        # Prepare the basic result structure
        result = {
            "original_groups": original_groups_count,
            "merged_groups": merged_groups_count,
            "group_tracking": group_tracking_list,
            "summary": {  # Added summary field that analytics expects
                "total_groups": merged_groups_count,
                "original_unique_faces": original_groups_count,
                "merged_groups_count": merged_groups_count,
                "total_detections": total_detections,
                "frames_processed": frames_processed,
                "max_faces_per_frame": max_faces_per_frame,
                "grouping_algorithm": "percentage_based_tracking",
                "tolerance_percent": float(tolerance_percent),
                "tracked_faces": int(tracked_faces),
                "new_faces": int(new_faces),
                "merge_iterations": 0,  # Not applicable for this algorithm
            },
            "statistics": {
                "original_unique_faces": original_groups_count,
                "merged_groups_count": merged_groups_count,
                "total_detections": total_detections,
                "frames_processed": frames_processed,
                "max_faces_per_frame": max_faces_per_frame,
                "grouping_algorithm": "percentage_based_tracking",
                "tolerance_percent": float(tolerance_percent),
                "tracked_faces": int(tracked_faces),
                "new_faces": int(new_faces),
                "merge_iterations": 0,  # Not applicable for this algorithm
            },
            "regrouped_data": regrouped_data_records,
            "merge_history": [],  # Not applicable for this algorithm
            "id_mapping": {str(k): str(v) for k, v in id_mapping.items()},
            "classified_faces": convert_numpy_types(classified_faces),
        }

        # Add quality analysis and age detection if video_path is provided
        if video_path and group_tracking_list:
            print(
                "🔍 Analyzing image quality and detecting age for best faces in each group..."
            )
            try:
                best_quality_faces = self.find_best_quality_faces_per_group(
                    group_tracking_list, video_path
                )
                result["best_quality_faces"] = best_quality_faces
                print(
                    f"✅ Quality analysis complete for {len(best_quality_faces)} groups"
                )
            except Exception as e:
                print(f"⚠️ Quality analysis failed: {e}")
                result["best_quality_faces"] = {}
        else:
            result["best_quality_faces"] = {}

        return result

    def find_best_quality_faces_per_group(self, grouped_faces, video_path):
        """
        Find the best quality face image per group and perform age detection.

        Args:
            grouped_faces: List of group tracking data from apply_advanced_grouping
            video_path: Path to the video file for frame extraction

        Returns:
            Dict with best face per group including age detection results
        """
        try:
            # Try to import DeepFace for age detection
            from deepface import DeepFace

            deepface_available = True
        except ImportError:
            print("⚠️ DeepFace not available. Age detection will be skipped.")
            deepface_available = False

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Cannot open video file: {video_path}")
            return {}

        best_faces_per_group = {}

        try:
            # Process each group to find the best quality face
            for group in grouped_faces:
                group_id = group.get("Merged_Group_ID")
                original_ids = group.get("Original_Group_IDs", [])

                print(f"\n🔍 Analyzing group {group_id} with {len(original_ids)} faces")

                best_quality_score = 0.0
                best_face_info = None

                # Analyze each face in the group
                for original_id in original_ids:
                    # Find the face data to get frame number and bbox
                    face_data = self._find_face_data_by_id(original_id)
                    if not face_data:
                        continue

                    frame_number = face_data.get("frame_number")
                    bbox = face_data.get("bbox")

                    if frame_number is None or bbox is None:
                        continue

                    # Extract frame from video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    # Extract face region
                    x1, y1, x2, y2 = bbox
                    face_crop = frame[y1:y2, x1:x2]

                    if face_crop.size == 0:
                        continue

                    # Calculate quality score
                    quality_score = self.score_image(face_crop)

                    print(
                        f"  Face {original_id}: Frame {frame_number}, Quality: {quality_score}"
                    )

                    # Check if this is the best quality face so far
                    if quality_score > best_quality_score:
                        best_quality_score = quality_score
                        best_face_info = {
                            "face_id": original_id,
                            "frame_number": frame_number,
                            "quality_score": quality_score,
                            "bbox": bbox,
                            "face_crop": face_crop.copy(),
                        }

                # Perform age detection on the best quality face
                if best_face_info and deepface_available:
                    try:
                        face_crop = best_face_info["face_crop"]

                        # DeepFace expects RGB format
                        face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

                        # Perform age detection
                        analysis = DeepFace.analyze(
                            face_rgb, actions=["age"], enforce_detection=False
                        )

                        if isinstance(analysis, list):
                            analysis = analysis[0]

                        estimated_age = analysis["age"]

                        best_face_info["age_detection"] = {
                            "estimated_age": estimated_age,
                        }

                        print(f"  ✅ Age detected: {estimated_age} years")

                    except Exception as age_error:
                        print(f"  ⚠️ Age detection failed: {age_error}")
                        best_face_info["age_detection"] = {
                            "estimated_age": "Unknown",
                        }
                else:
                    if best_face_info:
                        best_face_info["age_detection"] = {
                            "estimated_age": "Unknown",
                        }

                # Calculate distance from camera based on face size (larger face = closer)
                if best_face_info:
                    bbox = best_face_info["bbox"]
                    face_width = bbox[2] - bbox[0]
                    face_height = bbox[3] - bbox[1]
                    face_area = face_width * face_height
                    # Use inverse of area as distance (larger area = smaller distance)
                    distance = 1000000 / max(face_area, 1)  # Prevent division by zero
                    best_face_info["distance"] = round(distance, 2)

                # Store the best face info (remove the actual image crop to save memory)
                if best_face_info:
                    best_face_info.pop("face_crop", None)  # Remove image data
                    best_faces_per_group[group_id] = best_face_info

                    print(
                        f"  🏆 Best face for group {group_id}: Face {best_face_info['face_id']} "
                        f"(Quality: {best_face_info['quality_score']}, "
                        f"Age: {best_face_info['age_detection']['estimated_age']}, "
                        f"Distance: {best_face_info['distance']})"
                    )

        finally:
            cap.release()

        # Sort by distance (closest to camera first - smallest distance values)
        sorted_faces = dict(
            sorted(
                best_faces_per_group.items(),
                key=lambda x: x[1].get("distance", float("inf")),
            )
        )

        return sorted_faces

    def _find_face_data_by_id(self, face_id):
        """
        Helper method to find face data by ID from stored face data.
        """
        if not hasattr(self, "stored_face_data"):
            return None

        for face_data in self.stored_face_data:
            if face_data.get("face_id") == face_id:
                return {
                    "frame_number": face_data.get("frame_number"),
                    "bbox": face_data.get("bbox"),
                }
        return None
