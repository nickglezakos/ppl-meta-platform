"""
Visualization Engine for 3D trajectory and plotting capabilities.
"""

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class VisualizationEngine:
    """
    Visualization engine for creating interactive plots and charts.
    """

    def __init__(self):
        """Initialize the visualization engine."""
        pass

    def create_3d_trajectory(
        self,
        df: pd.DataFrame,
        x_axis: str = "Position_X",
        y_axis: str = "Position_Y",
        z_axis: str = "Frame_Number",
        reverse_z: bool = False,
    ) -> Dict[str, Any]:
        """
        Create 3D trajectory visualization.

        Args:
            df: DataFrame with face detection data
            x_axis: Column name for X-axis
            y_axis: Column name for Y-axis
            z_axis: Column name for Z-axis
            reverse_z: Whether to reverse Z-axis order

        Returns:
            Dictionary with HTML content and metadata
        """
        fig = go.Figure()

        # Group by Face_ID or Merged_Group_ID if available
        group_col = "Merged_Group_ID" if "Merged_Group_ID" in df.columns else "Face_ID"

        for group_id in df[group_col].unique():
            group_data = df[df[group_col] == group_id]

            # Apply Z-axis reversal if requested
            z_data = group_data[z_axis]
            if reverse_z:
                z_data = -z_data

            fig.add_trace(
                go.Scatter3d(
                    x=group_data[x_axis],
                    y=group_data[y_axis],
                    z=z_data,
                    mode="markers+lines",
                    name=f"{group_col} {group_id}",
                    text=[
                        f"Frame: {frame}<br>X: {x}<br>Y: {y}<br>ID: {face_id}"
                        for frame, x, y, face_id in zip(
                            group_data[z_axis],
                            group_data[x_axis],
                            group_data[y_axis],
                            group_data[group_col],
                        )
                    ],
                    hovertemplate="<b>%{fullData.name}</b><br>%{text}<extra></extra>",
                    marker=dict(size=8, opacity=0.8),
                    line=dict(width=4),
                )
            )

        # Update layout
        z_title = f"{z_axis} {'(Reversed)' if reverse_z else ''}"

        fig.update_layout(
            title=f"3D Trajectory: {x_axis} × {y_axis} × {z_axis}",
            scene=dict(
                xaxis_title=x_axis,
                yaxis_title=y_axis,
                zaxis_title=z_title,
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
            ),
            height=700,
            showlegend=True,
        )

        return {
            "html_content": fig.to_html(),
            "json_data": fig.to_dict(),
            "metadata": {
                "visualization_type": "3d_trajectory",
                "axes": {"x": x_axis, "y": y_axis, "z": z_axis},
                "reverse_z": reverse_z,
                "data_points": len(df),
                "groups": df[group_col].nunique(),
            },
        }

    def create_2d_scatter(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create 2D scatter plot of face positions."""
        group_col = "Merged_Group_ID" if "Merged_Group_ID" in df.columns else "Face_ID"

        fig = px.scatter(
            df,
            x="Position_X",
            y="Position_Y",
            color=group_col,
            hover_data=["Frame_Number"],
            title="2D Face Position Scatter Plot",
        )

        fig.update_layout(height=600)

        return {
            "html_content": fig.to_html(),
            "json_data": fig.to_dict(),
            "metadata": {
                "visualization_type": "2d_scatter",
                "data_points": len(df),
                "groups": df[group_col].nunique(),
            },
        }

    def create_timeline(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Create timeline visualization of face movements."""
        group_col = "Merged_Group_ID" if "Merged_Group_ID" in df.columns else "Face_ID"

        fig = px.line(
            df,
            x="Frame_Number",
            y="Position_Y",
            color=group_col,
            title="Face Movement Timeline",
            markers=True,
        )

        fig.update_layout(height=500)

        return {
            "html_content": fig.to_html(),
            "json_data": fig.to_dict(),
            "metadata": {
                "visualization_type": "timeline",
                "data_points": len(df),
                "groups": df[group_col].nunique(),
            },
        }
