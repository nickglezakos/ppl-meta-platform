# Main flow

media service

arguments: file_path

Initiation variables:
from the settings module: frame_dir


Methods:
Empty the frames directory if it exists, otherwise create it
Re-encode the video to .mp4 if it's a .webm file
Open the video file
Check if video opened successfully
Get the total number of frames
Ensure the frames directory exists
Read until video is completed
When everything done, release the video capture object


