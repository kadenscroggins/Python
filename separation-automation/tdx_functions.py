"""
Functions for interfacing with the TeamDynamix API
"""
import json
import requests

def get_tdx_headers():
    """
    Gets an authentication token from the TDX API

    Returns this token formatted appropriately as a JSON with fields of
    HTML headers for REST API calls including Content-Type and Authorization

    There needs to be a file in the same directory as this script named 'TDX_ATP.json' containing:
    {
        "BEID": "<TDX instance BEID>",
        "WebServicesKey": "<TDX instance WebServicesKey>"
    }

    :returns: TDX auth token with headers
    :rtype: dict
    """
    auth_url = "https://solutions.teamdynamix.com/TDWebApi/api/auth/loginadmin"

    with open('./secrets/TDX_ATP.json', encoding='UTF-8') as api_key_file:
        api_keys = json.load(api_key_file)

    token = requests.post(auth_url, api_keys, timeout=60)
    token = str(token.content)[2:-1] # Strip extra characters (b'<token>') from auth token
    token = 'Bearer ' + token # TDX API wants the token to be prefaced with 'Bearer '

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": token
    }

    return headers

def get_separation_ticket_ids(number=0, headers=get_tdx_headers()):
    """
    Calls the TDX API to get ticket IDs

    Only looks for "New" tickets - that way, the tickets can be updated
    to "In Process" or "Open" once the automation is done making changes,
    and this will not return any tickets that have already been processed

    :param int number: Max number of tickets to get, 0 disables limit
    :param dict headers: TDX API headers, including auth token
    :returns: List of Ticket IDs
    :rtype: list[int]
    """
    search_url = "https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/search"

    search_text = {
        'MaxResults': number,
        'TypeIDs': ['Redacted'], 
        'StatusIDs': ['Redacted'], # Only New tickets - ignore Open or In Process
    }

    tickets = requests.post(search_url, headers=headers, json=search_text, timeout=60)
    tickets = json.loads(tickets.content)
    ids = []
    for ticket in tickets:
        ids.append(int(ticket["ID"]))

    return ids

def get_ticket_oracle_id(ticket_id, headers=get_tdx_headers()):
    """
    Retrieves oracle ID attribute from supplied Ticket ID

    :param int ticket_id: Ticket ID
    :param dict headers: TDX API headers, including auth token
    :returns: oracle ID
    :rtype: str
    """
    ticket_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}'
    ticket = requests.get(ticket_url, headers=headers, timeout=60)
    ticket = json.loads(ticket.content)

    oracle_id = ""
    for attribute in ticket["Attributes"]:
        if attribute["ID"] == 'Redacted':
            oracle_id = attribute["Value"]
            break

    return oracle_id

def get_ticket_info(ticket_id, headers=get_tdx_headers()):
    """
    Gets the JSON output of a ticket's attributes

    :param int ticket_id: Ticket ID
    :param dict headers: TDX API headers, including auth token
    :returns: Ticket information
    :rtype: str
    """
    ticket_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}'
    ticket = requests.get(ticket_url, headers=headers, timeout=60)
    ticket = json.loads(ticket.content)

    ticket_str = json.dumps(ticket, indent=4)

    return ticket_str

def advance_workflow_status(ticket_id, status, headers=get_tdx_headers()):
    """
    Advances the workflow from stage 1 to stage 2

    Advances to the second step based on the status indicated.
    Sets ticket to "In Process" to indicate that the API has begun
    working on this ticket.

    Valid status codes:
        1 - Current or Recent Student
        2 - Retiree
        3 - Terminated
    
    :param int ticket: Ticket ID
    :param int status: Status code of separation type
    :param dict headers: TDX API headers, including auth token
    :returns: Message value from HTTP POST response
    :rtype: str
    :throws ValueError: Throws an error if status is not 1, 2, or 3
    """
    workflow_approve_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}/workflow/approve'
    ticket_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}'

    action_id = ""
    if status == 1:
        action_id = "Choice1" # Student
    elif status == 2:
        action_id = "Choice2" # Retiree
    elif status == 3:
        action_id = "Choice3" # Terminated
    else:
        raise ValueError(f"Invalid status code: {status}")

    approve_request = {
        "StepID": "redacted",
        "ActionID": action_id
    }

    response = requests.post(workflow_approve_url, headers=headers, json=approve_request, \
                             timeout=60)
    response = json.loads(response.content)

    patch = [{ # Set status to In Process
        "op": "replace",
        "path": "/StatusID",
        "value": 'redacted'
    }]
    requests.patch(ticket_url, headers=headers, json=patch, timeout=60)

    return response["Message"]

def advance_workflow_separation(ticket_id, status, comments, headers=get_tdx_headers()):
    """
    Advances the workflow from stage 2 to stage 3

    Valid status codes:
    1 - Current or Recent Student
    2 - Retiree
    3 - Terminated

    Gets Task ID, sets it to 100%, and comments on task feed

    Sets ticket to "Open" to indicate that the API has finished
    working on this ticket.
    
    :param int ticket: Ticket ID
    :param int status: Status code of separation type
    :param str comments: Comments to update workflow step with
    :param dict headers: TDX API headers, including auth token
    :throws ValueError: Throws an error if status is not 1, 2, or 3
    """
    if (status > 3 or status < 1):
        raise ValueError(f"Invalid status code: {status}")

    ticket_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}'
    ticket = json.loads(get_ticket_info(ticket_id, headers))

    task_id = ticket["Tasks"][0]["ID"]
    task_url = \
        f'https://solutions.teamdynamix.com/TDWebApi/api/<AppID>/tickets/{ticket_id}/tasks/{task_id}/feed'

    ticket_task_feed_entry = {
        "PercentComplete": 100,
        "Comments": comments,
        "IsPrivate": True,
        "IsRichHtml": False
    }

    response = requests.post(task_url, headers=headers, json=ticket_task_feed_entry, timeout=60)
    response = json.loads(response.content)

    patch = [{ # Set status to Open
        "op": "replace",
        "path": "/StatusID",
        "value": 'redacted'
    }]
    requests.patch(ticket_url, headers=headers, json=patch, timeout=60)

def get_uid(username, headers=get_tdx_headers()):
    """
    Gets UID from TDX via username

    :param str username: Username
    :param dict headers: TDX API headers, including auth token
    :returns: UID
    :rtype: str
    """
    search_url = 'https://solutions.teamdynamix.com/TDWebApi/api/people/search'
    user_search ={
        'UserName' : f'{username}@example.com'
    }

    results = requests.post(search_url, json=user_search, headers=headers, timeout=60)
    results = json.loads(results.content)

    return results[0]["UID"]

def remove_employee_group(username, headers=get_tdx_headers()):
    """
    Remove Employees group in TDX

    :param str username: Username
    :param dict headers: TDX API headers, including auth token
    """
    uid = get_uid(username)
    url = f'https://solutions.teamdynamix.com/TDWebApi/api/people/{uid}/groups/<GroupID>'

    requests.delete(url, headers=headers, timeout=60)
