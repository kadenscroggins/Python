"""
Functions for interfacing with Active Directory

Must be ran as a user on the domain who has Domain Admin credentials
"""
import pyad.adquery
import pyad.aduser
import pyad.adgroup

AD_GROUP_BLOCKLIST = [
    # Redacted
]
"""Groups that need not / should not be removed"""

def get_query_object():
    """
    Connect to AD and return ADQuery object

    May not need to be in its own function, but putting it in one for now
    in case we want to update this to use a service account in the future

    :returns: ADQuery object
    :rtype: ADQuery
    """
    return pyad.adquery.ADQuery()

def print_user_info(samaccountname):
    """
    Prints username, first name, and last name to console

    :param str samaccountname: Username
    """
    conn = get_query_object()

    conn.execute_query(
    attributes = ["samaccountname", "givenName", "sn"],
    where_clause = f"objectClass = 'user' and sAMAccountName = '{samaccountname}'",
    base_dn = "OU = All_Users, DC = nsuok, DC = edu"
    )

    for user in conn.get_results():
        print("Username:", user["samaccountname"])
        print("User's Name:", user["givenName"], user["sn"])

def get_group_names(samaccountname):
    """
    Gets a list of AD groups that a user is a member of

    Does not return any groups that shouldn't be removed.
    These groups are listed in the AD_GROUP_BLOCKLIST constant.

    :param str samaccountname: Username
    :returns: List of AD groups the user is a member of
    :rtype: list[str]
    :throws RuntimeError: Thrown if a group has more than one entry for 'name' attribute
    """
    user = pyad.aduser.ADUser.from_cn(samaccountname)
    groups = user.get_memberOfs()

    group_names = []
    for group in groups:
        name = group.get_attribute("name")

        # get_attribute returns a list, so we error if the length is not 1
        # otherwise just return the single item in the list
        if len(name) != 1:
            raise RuntimeError(f"ADGroup has multiple entries for 'name' attribute: {str(group)}")
        group_names.append(name[0])

    # Remove duplicates, filter blocklist, and re-alphabetize.
    group_names = list(set(group_names))
    group_names = [name for name in group_names if name not in AD_GROUP_BLOCKLIST]
    group_names.sort()

    return group_names

def disable_ad_user(samaccountname):
    """
    Deactivates a user with a given username

    :param str samaccountname: Username
    """
    user = pyad.aduser.ADUser.from_cn(samaccountname)
    user.disable()

def remove_ad_group(samaccountname, group_name):
    """
    Removes a user from a group

    Checks against AD_GROUP_BLOCKLIST to determine if the group should
    not be removed.

    :param str samaccountname: Username
    :param str group_name: Group name
    """
    if group_name not in AD_GROUP_BLOCKLIST:
        user = pyad.aduser.ADUser.from_cn(samaccountname)
        group = pyad.adgroup.ADGroup.from_cn(group_name)
        group.remove_members(user)
