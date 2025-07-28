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
        self.proximity_threshold = 50.0

    def calculate_distance(self, face1: Dict, face2: Dict) -> float:
        """
        Calculate Euclidean distance between two face positions.

        Args:
            face1: Dictionary with Position_X and Position_Y
            face2: Dictionary with Position_X and Position_Y

        Returns:
            Euclidean distance between the two face positions
        """
        dx = face1["Position_X"] - face2["Position_X"]
        dy = face1["Position_Y"] - face2["Position_Y"]
        return math.sqrt(dx * dx + dy * dy)

    def apply_proximity_clustering(
        self, df: pd.DataFrame, proximity_threshold: float
    ) -> Dict[str, List[str]]:
        """
        Apply proximity-based clustering to group nearby faces.

        Args:
            df: DataFrame with face detection data
            proximity_threshold: Maximum distance for faces to be grouped together

        Returns:
            Dictionary mapping group IDs to lists of face IDs
        """
        # Convert DataFrame to list of dictionaries for easier processing
        faces = df.to_dict("records")
        groups = {}
        group_counter = 1
        processed_faces = set()

        for i, face in enumerate(faces):
            if face["Face_ID"] in processed_faces:
                continue

            # Start a new group with this face
            current_group = f"Group_{group_counter}"
            groups[current_group] = [face["Face_ID"]]
            processed_faces.add(face["Face_ID"])

            # Find all faces within proximity threshold
            for j, other_face in enumerate(faces):
                if (
                    i != j
                    and other_face["Face_ID"] not in processed_faces
                    and self.calculate_distance(face, other_face) <= proximity_threshold
                ):
                    groups[current_group].append(other_face["Face_ID"])
                    processed_faces.add(other_face["Face_ID"])

            group_counter += 1

        return groups

    def apply_advanced_grouping(
        self,
        df: pd.DataFrame,
        max_faces_per_frame: int = 2,
        proximity_threshold: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Apply advanced face grouping algorithm with proximity-based clustering.

        The proximity_threshold determines how close faces need to be
        (in pixels) to be considered the same person across frames.
        """
        self.proximity_threshold = proximity_threshold

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

        # Apply proximity-based clustering first
        proximity_groups = self.apply_proximity_clustering(df, proximity_threshold)

        # If we have too many groups, merge using max_faces_per_frame constraint
        if len(proximity_groups) > max_faces_per_frame:
            # Merge groups to fit within max_faces_per_frame limit
            group_mapping = {}
            group_counter = 1

            for group_name, face_ids in proximity_groups.items():
                target_group = ((group_counter - 1) % max_faces_per_frame) + 1
                for face_id in face_ids:
                    group_mapping[face_id] = str(target_group)
                group_counter += 1
        else:
            # Use proximity groups as-is
            group_mapping = {}
            for i, (group_name, face_ids) in enumerate(proximity_groups.items(), 1):
                for face_id in face_ids:
                    group_mapping[face_id] = str(i)

        # Create regrouped dataframe
        df_regrouped = df.copy()
        df_regrouped["Merged_Group_ID"] = df_regrouped["Face_ID"].map(group_mapping)

        # Generate group tracking with proximity information
        group_tracking = []
        for group_id in df_regrouped["Merged_Group_ID"].unique():
            faces = df_regrouped[df_regrouped["Merged_Group_ID"] == group_id][
                "Face_ID"
            ].unique()

            # Calculate average position for this group
            group_faces = df_regrouped[df_regrouped["Merged_Group_ID"] == group_id]
            avg_x = group_faces["Position_X"].mean()
            avg_y = group_faces["Position_Y"].mean()

            group_tracking.append(
                {
                    "Merged_Group_ID": group_id,
                    "Original_Group_IDs": faces.tolist(),
                    "Face_Count": len(faces),
                    "Average_Position": {"x": avg_x, "y": avg_y},
                    "Proximity_Threshold_Used": proximity_threshold,
                }
            )

        return {
            "original_groups": df["Face_ID"].nunique(),
            "merged_groups": len(df_regrouped["Merged_Group_ID"].unique()),
            "group_tracking": group_tracking,
            "statistics": {
                "original_unique_faces": df["Face_ID"].nunique(),
                "merged_groups_count": len(df_regrouped["Merged_Group_ID"].unique()),
                "total_detections": len(df),
                "frames_processed": df["Frame_Number"].nunique(),
                "proximity_threshold": proximity_threshold,
                "max_faces_per_frame": max_faces_per_frame,
            },
            "regrouped_data": df_regrouped.to_dict("records"),
        }
