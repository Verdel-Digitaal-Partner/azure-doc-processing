import re


def get_latest_version(versions: list) -> str:
    """
    Get the latest version from a list of versions based on major.minor.patch principle.

    Args
        versions: list of version strings (e.g., ['1.2.0', '2.0.1', '1.3.4'])

    Returns
        latest_version: latest version in the list
    """

    def version_key(version):
        # Split the version into major, minor, patch and return as a tuple of integers
        return tuple(map(int, version.split(".")))

    # Sort the versions using the key, highest version will be last
    sorted_versions = sorted(versions, key=version_key)

    # Return the last (highest) version
    latest_version = sorted_versions[-1]

    return latest_version


def find_latest_version_file(file_paths: list):
    """
    Find the file with the latest version from a list of file paths.

    Args
        file_paths: list of file paths (e.g., ['prompts/messages/v1.2.0/prompt.json'])
    Returns
        result: file path with the latest version
    """
    version_pattern = re.compile(
        r"v(\d+\.\d+\.\d+)"
    )  # Regex to extract the version (e.g., v1.2.0)

    versions = []
    version_to_file = {}

    for file_path in file_paths:
        match = version_pattern.search(file_path)
        if match:
            version = match.group(1)  # Extract the version (e.g., '1.2.0')
            versions.append(version)
            version_to_file[version] = file_path  # Map version to its file path

    if not versions:
        raise ValueError("No valid versions found in the file paths.")

    # Get the latest version
    latest_version = get_latest_version(versions)

    # Return the corresponding file path
    return version_to_file[latest_version]
