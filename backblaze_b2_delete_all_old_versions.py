# This script lists file versions in a Backblaze B2 bucket and deletes old versions, while keeping the most recent version.
# The script also supports a dry-run mode to preview the deletions before they happen.

# 1. First, install the Backblaze B2 CLI tool:
#    pip install b2

# 2. Then, authenticate to Backblaze B2 by running the following command:
#    b2 authorize-account
#    (You will need your Account ID and Application Key to complete this step.)

# 3. Once authenticated, you can execute the script.

# 4. For a dry run to see which files would be deleted (no actual deletion will happen):
#    python3 backblaze_b2_delete_all_old_versions.py <bucket_name> --dry-run

# 5. For actually deleting the old versions and keeping only the latest version:
#    python3 backblaze_b2_delete_all_old_versions.py <bucket_name>

#    Note: The script will ask for confirmation before proceeding with the deletions.

import subprocess
import json
import sys
from collections import defaultdict

# Function to run a command and return the output
def run_command(command):
    try:
        # Runs the provided shell command and captures output
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

# Function to list all file versions in the given B2 bucket
def get_file_versions(bucket_name):
    # Runs the `b2 ls --json --recursive --versions` command to get versions of all files in the bucket
    command = ["b2", "ls", "--json", "--recursive", "--versions", f"b2://{bucket_name}"]
    output = run_command(command)
    
    # Parses the JSON output into a Python list
    try:
        return [json.loads(line) for line in output.splitlines() if line.strip()]
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print("Attempting to parse output as a single JSON object...")
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            print("Failed to parse output as JSON. Please check the B2 CLI version and output format.")
            sys.exit(1)

# Function to delete all but the latest version of each file in the B2 bucket
def delete_old_versions(bucket_name, dry_run=False):
    file_versions = get_file_versions(bucket_name)
    
    if not file_versions:
        print(f"No files found in bucket: {bucket_name}")
        return

    # Organize versions by filename
    if isinstance(file_versions, list):
        files = defaultdict(list)
        for file in file_versions:
            files[file['fileName']].append(file)
    elif isinstance(file_versions, dict):
        files = {file_versions['fileName']: [file_versions]}
    else:
        print(f"Unexpected data type for file_versions: {type(file_versions)}")
        return

    deleted_count = 0
    for filename, versions in files.items():
        # Sort versions by upload timestamp, keeping the most recent
        sorted_versions = sorted(versions, key=lambda x: x['uploadTimestamp'], reverse=True)
        
        # Delete all but the latest version
        for version in sorted_versions[1:]:
            if dry_run:
                print(f"Would delete: {filename} (Version: {version['fileId']})")
            else:
                print(f"Deleting: {filename} (Version: {version['fileId']})")
                delete_command = ["b2", "delete-file-version", filename, version['fileId']]
                run_command(delete_command)
            deleted_count += 1

    # Print summary
    if dry_run:
        print(f"\nTotal versions that would be deleted: {deleted_count}")
    else:
        print(f"\nTotal versions deleted: {deleted_count}")

# Entry point of the script
if __name__ == "__main__":
    # Ensure the correct number of arguments are passed
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python3 delete.py <bucket_name> [--dry-run]")
        sys.exit(1)

    # Get bucket name and whether it's a dry run
    bucket_name = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    # Confirm before proceeding with deletion (unless dry-run is enabled)
    if dry_run:
        print("Running in dry run mode. No files will be actually deleted.")
    else:
        print("WARNING: This will actually delete file versions. Are you sure? (y/n)")
        confirmation = input().lower()
        if confirmation != 'y':
            print("Operation cancelled.")
            sys.exit(0)

    # Execute the delete operation
    delete_old_versions(bucket_name, dry_run)

