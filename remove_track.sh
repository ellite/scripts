#!/bin/bash
# remove_track.sh - A simple script to remove a specific track from MKV files
#
# This script loops through all MKV files in the current directory, lists their tracks,
# and allows the user to select a track (video, audio, or subtitle) to remove.
# After processing, the original MKV file is replaced with the updated version.
#
# Dependencies:
# - mkvmerge (from MKVToolNix)
#
# Usage:
# 1. Place this script in the folder containing your MKV files.
# 2. Run `chmod +x remove_track.sh` to make it executable.
# 3. Execute the script: `./remove_track.sh`
# 4. Follow the prompts to remove tracks as needed.
#
# Author: ellite
# License: MIT

# Loop through all MKV files in the current directory
for file in *.mkv; do
    echo "Processing: $file"
    
    # List tracks in the MKV file
    mkvmerge -i "$file"

    # Prompt user to enter the track ID to remove
    read -p "Enter the track ID you want to remove (or press Enter to skip): " track

    # Check if user provided a valid input
    if [[ -n "$track" ]]; then
        # Temporary output file
        temp_file="${file%.mkv}_modified.mkv"

        # Run mkvmerge to remove the selected track
        mkvmerge -o "$temp_file" -T -d "!$track" -a "!$track" -s "!$track" "$file"

        # Replace the original file
        mv "$temp_file" "$file"

        echo "Updated: $file (Track $track removed)"
    else
        echo "Skipping $file"
    fi

    echo "-----------------------------------"
done

echo "All files processed."
