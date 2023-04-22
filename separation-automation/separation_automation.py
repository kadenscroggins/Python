"""
Script to automatically process a separation notice ticket and take action on it in multiple systems

Author: Kaden Scroggins
"""
import time
from subprocess import \
    CalledProcessError
from ad_functions import \
    disable_ad_user, \
    get_group_names, \
    remove_ad_group
from oracle_functions import \
    get_uuid, \
    get_username, \
    get_status, \
    get_oracle_account_info
from tdx_functions import \
    get_tdx_headers, \
    get_ticket_oracle_id, \
    advance_workflow_status, \
    advance_workflow_separation, \
    remove_employee_group, \
    get_separation_ticket_ids
from mssql_functions import \
    mssql_set_student, \
    mssql_disable
from google_functions import \
    deprovision, \
    suspend, \
    get_google_groups, \
    remove_google_group

def process_ticket(ticket_id):
    """
    Processes a separation ticket

    Workflow:
        1. Get user information from ticket
        2. Determine separation type (Student, Retiree, Termination)
        3. Deactivate or set to student in mssql and write to mssql log
        4. Disable in AD if separation type is Termination
        5. Remote AD groups
        6. Suspend and Deprovision in Google if separation type is Termination
        7. Remove non-student Google groups
        8. Remove Employees group in TDX
        9. Log oracle access on ticket
        10. Comment info on ticket task and update workflow
    
    :param int ticket_id: TDX Ticket ID
    :returns: String of log update
    :rtype: str
    """
    print("Collecting user information...")
    tdx_headers = get_tdx_headers()
    oracle_id = get_ticket_oracle_id(ticket_id, tdx_headers)
    uuid = get_uuid(oracle_id)
    username = get_username(uuid)
    status = get_status(oracle_id)
    ticket_update = ''
    print(f'oracle ID: {oracle_id}\nuuid: {uuid}\nUsername: {username}\nStatus: {status}')

    print("Validating status...")
    if status not in (1, 2, 3):
        raise ValueError(f"WARNING: Unexpected status code ({status}) for {username}")

    print("Checking oracle account...")
    oracle_info = get_oracle_account_info(oracle_id)
    if '"OPEN"' in oracle_info: # Throw exception if oracle account is still active
        raise RuntimeError(f"WARNING: oracle account still active for {username}!")

    advance_workflow_status(ticket_id, status, tdx_headers)
    print("Advanced workflow from step 1 to step 2")

    print("Processing mssql and AD...")
    if status == 1:
        ticket_update += f"Leaving current/recent student account active: {username}"
        mssql_set_student(username, message=f"Account actions taken per TDX#{ticket_id}")
        ticket_update += "\n\nSet to Student in mssql"
    elif status == 2:
        ticket_update += f"Leaving retiree account active: {username}"
    elif status == 3:
        ticket_update = f"Automatically deactivating terminated user account: {username}"
        mssql_disable(username, message=f"Account actions taken per TDX#{ticket_id}")
        ticket_update += "\n\nDisabled in mssql"
        disable_ad_user(username)
        ticket_update += "\n\nDisabled in AD"

    print("Removing AD groups...")
    ticket_update += "\n\nRemoving the following AD groups:"
    ad_groups = get_group_names(username)
    if len(ad_groups) > 0:
        for group in ad_groups:
            remove_ad_group(username, group)
            print(f"Removed AD group: {group}")
            ticket_update += f"\n{group}"

    print("Processing Google account...")
    try:
        google_groups = get_google_groups(username)
        if status in (1, 2):
            ticket_update += "\n\nLeaving account active in Google. Removing groups:"
        elif status == 3:
            deprovision(username)
            suspend(username)
            ticket_update += "\n\nSuspended in Google. Removing groups:"

        for group in google_groups:
            group_update = remove_google_group(username, group)
            print(group_update)
            ticket_update += f"\n{group_update}"
    except CalledProcessError as exception:
        ticket_update += "\n\nGoogle account may not exist, an error occurred."
        print("Google account may not exist, continuing script. Error:", str(exception))

    print("Removing Employees group in TDX...")
    try:
        remove_employee_group(username, tdx_headers)
        ticket_update += "\n\nEmployees group removed in TDX (if it was present)"
    except IndexError as exception:
        ticket_update += "\n\nNo TDX account found"
        print("TDX account not found, continuing script. Error:", exception)

    ticket_update += "\n\noracle account information:\n"
    ticket_update += oracle_info

    advance_workflow_separation(ticket_id, status, ticket_update, tdx_headers)
    print("Advanced workflow from step 2 to step 3")
    return ticket_update

print("Getting tickets...")
ticket_ids = get_separation_ticket_ids()
print(f'There are currently {len(ticket_ids)} "New" tickets')

for ticket in ticket_ids:
    print(f"Processing ticket: TDX#{ticket}")
    print("----------------------------")
    feed_entry = process_ticket(ticket)
    print("---------Feed Entry---------\n\n")
    print(feed_entry)
    print("\n\n----------------------------")

    print("Sleeping for 5 seconds...")
    time.sleep(5)
