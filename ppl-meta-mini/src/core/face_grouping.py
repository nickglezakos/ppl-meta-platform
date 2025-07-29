"""
Advanced Face Grouping Engine - Core algorithm implementation.
"""

import math
from typing import Any, Dict, List

import pandas as pd


class FaceGroupingEngine:
    """
    Advanced face grouping engine that merges face groups when
    unique face IDs exceed maximum faces per frame.
    """

    def __init__(self):
        """Initialize the face grouping engine."""
        pass

    def apply_advanced_grouping(
        self,
        df: pd.DataFrame,
        max_faces_per_frame: int = None,  # Accept parameter but calculate dynamically
        proximity_threshold: float = 50.0,  # Accept but not used in notebook algorithm
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

        print(f"🔍 === FACE CLASSIFICATION AND TRACKING ===")
        print(f"📊 Assigning unique IDs and tracking faces across frames")
        print(f"=" * 70)

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
                    "grouping_algorithm": "no_faces_found",
                    "merge_iterations": 0,
                },
                "statistics": {
                    "original_unique_faces": 0,
                    "merged_groups_count": 0,
                    "total_detections": 0,
                    "frames_processed": 0,
                    "max_faces_per_frame": 0,
                    "grouping_algorithm": "no_faces_found",
                    "merge_iterations": 0,
                },
                "regrouped_data": [],
                "merge_history": [],
                "id_mapping": {},
            }

        print(f"📋 Processing {len(frames_with_faces)} frames with faces")
        print(f"🎯 Tolerance: 20% for coordinate matching")

        # Initialize classification system
        next_classification_id = 100  # Start with 3-digit numbers
        classified_faces = []
        active_tracks = {}  # Track ID -> last known position

        tolerance_percent = 20.0  # Hardcoded 20% as requested
        tolerance_ratio = tolerance_percent / 100.0

        print(f"\n🔄 Processing frames chronologically...")
        print("-" * 70)

        for frame_idx, frame_result in enumerate(frames_with_faces):
            frame_number = frame_result["frame_number"]
            faces = frame_result["faces"]

            print(f"\n📸 Frame {frame_number}: {len(faces)} face(s)")

            # For the first frame, assign unique IDs to all faces
            if frame_idx == 0:
                print(
                    f"   🆕 First frame - assigning new IDs to all {len(faces)} faces"
                )

                for face_idx, face in enumerate(faces):
                    classification_id = next_classification_id
                    next_classification_id += 1

                    # Extract coordinates
                    x = face["Position_X"]
                    y = face["Position_Y"]
                    distance = (
                        (x**2) + (y**2)
                    ) ** 0.5  # Calculate distance from origin

                    classified_face = {
                        "classification_id": classification_id,
                        "frame_number": frame_number,
                        "original_face": face,
                        "position": {"x": x, "y": y, "distance": distance},
                        "match_type": "new",
                        "match_confidence": 1.0,
                    }

                    classified_faces.append(classified_face)

                    # Add to active tracks
                    active_tracks[classification_id] = {
                        "x": x,
                        "y": y,
                        "distance": distance,
                        "frame_number": frame_number,
                    }

                    print(
                        f"     Face {face_idx + 1}: ID {classification_id} at ({x:.0f}, {y:.0f}, {distance:.0f})"
                    )

            else:
                # For subsequent frames, try to match faces to existing tracks
                print(
                    f"   🔍 Matching {len(faces)} faces to {len(active_tracks)} active tracks"
                )

                frame_matches = []
                unmatched_faces = list(faces)

                # For each face in current frame, find best matching active track
                for face_idx, face in enumerate(faces):
                    x = face["Position_X"]
                    y = face["Position_Y"]
                    distance = ((x**2) + (y**2)) ** 0.5

                    position = {"x": x, "y": y, "distance": distance}

                    best_match = None
                    best_distance = float("inf")

                    # Check against all active tracks
                    for track_id, track_pos in active_tracks.items():
                        # Calculate percentage differences for each coordinate
                        x_diff = abs(x - track_pos["x"]) / max(track_pos["x"], 1)
                        y_diff = abs(y - track_pos["y"]) / max(track_pos["y"], 1)
                        dist_diff = abs(distance - track_pos["distance"]) / max(
                            track_pos["distance"], 1
                        )

                        # Check if all coordinates are within tolerance
                        if (
                            x_diff <= tolerance_ratio
                            and y_diff <= tolerance_ratio
                            and dist_diff <= tolerance_ratio
                        ):
                            # Calculate combined distance metric for ranking matches
                            combined_distance = (x_diff + y_diff + dist_diff) / 3

                            if combined_distance < best_distance:
                                best_distance = combined_distance
                                best_match = {
                                    "track_id": track_id,
                                    "distance": combined_distance,
                                    "x_diff": x_diff,
                                    "y_diff": y_diff,
                                    "dist_diff": dist_diff,
                                }

                    frame_matches.append(
                        {
                            "face_idx": face_idx,
                            "face": face,
                            "position": position,
                            "best_match": best_match,
                        }
                    )

                # Assign faces to tracks, handling conflicts
                assigned_tracks = set()

                # Sort matches by quality (best matches first)
                frame_matches.sort(
                    key=lambda x: (
                        x["best_match"]["distance"] if x["best_match"] else float("inf")
                    )
                )

                for match_info in frame_matches:
                    face = match_info["face"]
                    position = match_info["position"]
                    best_match = match_info["best_match"]

                    if best_match and best_match["track_id"] not in assigned_tracks:
                        # Assign to existing track
                        classification_id = best_match["track_id"]
                        assigned_tracks.add(classification_id)

                        classified_face = {
                            "classification_id": classification_id,
                            "frame_number": frame_number,
                            "original_face": face,
                            "position": position,
                            "match_type": "tracked",
                            "match_confidence": 1.0 - best_match["distance"],
                            "match_details": {
                                "x_diff_percent": best_match["x_diff"] * 100,
                                "y_diff_percent": best_match["y_diff"] * 100,
                                "distance_diff_percent": best_match["dist_diff"] * 100,
                                "combined_distance": best_match["distance"],
                            },
                        }

                        # Update active track position
                        active_tracks[classification_id] = {
                            "x": position["x"],
                            "y": position["y"],
                            "distance": position["distance"],
                            "frame_number": frame_number,
                        }

                        print(
                            f"     Face {match_info['face_idx'] + 1}: Matched to ID {classification_id}"
                        )
                        print(
                            f"       Δ: X:{best_match['x_diff']*100:.1f}% Y:{best_match['y_diff']*100:.1f}% D:{best_match['dist_diff']*100:.1f}%"
                        )

                    else:
                        # Create new track for unmatched face
                        classification_id = next_classification_id
                        next_classification_id += 1

                        classified_face = {
                            "classification_id": classification_id,
                            "frame_number": frame_number,
                            "original_face": face,
                            "position": position,
                            "match_type": "new",
                            "match_confidence": 1.0,
                        }

                        # Add to active tracks
                        active_tracks[classification_id] = {
                            "x": position["x"],
                            "y": position["y"],
                            "distance": position["distance"],
                            "frame_number": frame_number,
                        }

                        print(
                            f"     Face {match_info['face_idx'] + 1}: New ID {classification_id} (no close match)"
                        )

                    classified_faces.append(classified_face)

        # Create summary statistics
        unique_ids = set(face["classification_id"] for face in classified_faces)
        tracked_faces = sum(
            1 for face in classified_faces if face["match_type"] == "tracked"
        )
        new_faces = sum(1 for face in classified_faces if face["match_type"] == "new")

        print(f"\n" + "=" * 70)
        print(f"🎯 FACE CLASSIFICATION COMPLETED")
        print(f"✅ Total faces classified: {len(classified_faces)}")
        print(f"👥 Unique individuals detected: {len(unique_ids)}")
        print(f"🔄 Successfully tracked: {tracked_faces}")
        print(f"🆕 New appearances: {new_faces}")
        print(f"📊 Frames processed: {len(frames_with_faces)}")
        print(f"🎯 ID range: {min(unique_ids)} - {max(unique_ids)}")

        # Create regrouped dataframe
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

        return {
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
            "classified_faces": convert_numpy_types(
                classified_faces
            ),  # Convert classified_faces too
        }
