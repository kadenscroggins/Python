"""
Functions for interfacing with Google API via GAM
"""
import subprocess

GOOGLE_GROUP_BLOCKLIST = [
    # Redacted
]
"""Group names or parts of names that should not be removed"""

def deprovision(username):
    """
    Deprovision a Google user via GAM
    
    This will clear a user's connected applications and sign-in cookies
    Command: gam user <username> deprovision

    :param str username: Username
    :returns: Shell output
    :rtype: str
    """
    output = subprocess.run(f'gam user {username} deprovision',
                            capture_output=True, check=True)
    return output.stdout.decode()

def suspend(username):
    """
    Suspend a Google user via GAM

    Command: gam update user <username> suspended on

    :param str username: Username
    :returns: Shell output
    :rtype: str
    """
    output = subprocess.run(f'gam update user {username} suspended on',
                            capture_output=True, check=True)
    return output.stdout.decode()

def get_google_groups(username):
    """
    Get a user's Google group memberships via GAM

    Command: gam print groups member <username>

    :param str username: Username
    :returns: List of groups
    :rtype: list[str]
    """
    output = subprocess.run(f'gam print groups member {username}',
                            capture_output=True, check=True)
    lines = output.stdout.decode().splitlines()

    # This fancy code just filters out all lines without the @ symbol in them
    return [line for line in lines if '@' in line]

def remove_google_group(username, group):
    """
    Removes a user from a group

    Command: gam update group <group> remove <username>

    :param str username: Username (username or username@example.com)
    :param str group: Google Group to remove user from (group@groups.example.com)
    :returns: Shell output, or info about skipping
    :rtype: str
    """
    for term in GOOGLE_GROUP_BLOCKLIST:
        if term in group:
            return f"Skipping {group} due to being present on blocklist"

    output = subprocess.run(f'gam update group {group} remove user {username}',
                            capture_output=True, check=True)
    return output.stdout.decode()
