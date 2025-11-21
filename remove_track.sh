#!/bin/bash

# remove_track.sh - Remove one or more tracks (with ranges) from multiple MKV files

# ------------------------------
# Function: Expand comma/range list (1,3-5 → 1 3 4 5)
# ------------------------------
expand_list() {
    local input="$1"
    local result=()

    IFS=',' read -ra parts <<< "$input"
    for part in "${parts[@]}"; do
        part="${part//[[:space:]]/}"  # remove spaces
        if [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            start="${BASH_REMATCH[1]}"
            end="${BASH_REMATCH[2]}"
            for ((i=start; i<=end; i++)); do
                result+=("$i")
            done
        elif [[ "$part" =~ ^[0-9]+$ ]]; then
            result+=("$part")
        fi
    done

    echo "${result[@]}"
}

# ------------------------------
# Main Script
# ------------------------------

files=(*.mkv)

if [ ${#files[@]} -eq 0 ]; then
    echo "No MKV files found in the current directory."
    exit 1
fi

echo "Available MKV files:"
idx=1
for f in "${files[@]}"; do
    echo "$idx) $f"
    ((idx++))
done

echo
read -p "Select files (e.g. 1,3-4,7): " selection

selected_indexes=($(expand_list "$selection"))

# Validate selection
if [ ${#selected_indexes[@]} -eq 0 ]; then
    echo "No valid file selections."
    exit 1
fi

echo
echo "Files selected:"
selected_files=()
for idx in "${selected_indexes[@]}"; do
    real_index=$((idx-1))
    if [[ -n "${files[$real_index]}" ]]; then
        echo " - ${files[$real_index]}"
        selected_files+=("${files[$real_index]}")
    fi
done

if [ ${#selected_files[@]} -eq 0 ]; then
    echo "No valid files selected."
    exit 1
fi

echo

# ------------------------------
# Loop through files
# ------------------------------

for file in "${selected_files[@]}"; do
    echo "==========================================="
    echo "Processing: $file"
    echo "==========================================="

    tracks_json=$(mkvmerge -i -F json "$file")

    echo "Available tracks:"
    echo "$tracks_json" | jq -r '
        .tracks[] |
        "\(.id): [\(.type)] lang=\(.properties.language // "und") name=\"\(.properties.track_name // "")\""
    '

    echo
    read -p "Enter track IDs to remove (e.g. 1,3-5,7 / press Enter to skip): " track_input

    if [[ -z "$track_input" ]]; then
        echo "Skipping $file"
        echo
        continue
    fi

    expanded_ids=($(expand_list "$track_input"))
    if [ ${#expanded_ids[@]} -eq 0 ]; then
        echo "No valid track IDs parsed. Skipping $file."
        echo
        continue
    fi

    echo "Tracks to remove: ${expanded_ids[*]}"
    echo

    # Build a single comma-separated list for mkvmerge
    id_list=$(IFS=,; echo "${expanded_ids[*]}")

    temp_file="${file%.mkv}_modified.mkv"

    echo "Running mkvmerge..."
    mkvmerge -o "$temp_file" -T \
        -d "!$id_list" \
        -a "!$id_list" \
        -s "!$id_list" \
        "$file"

    if [[ $? -eq 0 ]]; then
        mv "$temp_file" "$file"
        echo "Updated: $file ✔"
    else
        echo "mkvmerge failed for $file ❌"
        rm -f "$temp_file"
    fi

    echo
done

echo "All selected files processed."
