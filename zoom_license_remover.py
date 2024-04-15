"""
A script that takes a list of user email addresses based on an SQL query
from an Oracle database, compares it to the list of users in Zoom with
or without licenses, and determines what users to remove licenses from.

Users who are a member of ANY group within zoom are considered to be
allowlisted, and will not have their license removed.
"""
import requests
import json
import sys
import traceback
import base64
import oracledb
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_zoom_access_token():
	"""
	Gets an OAuth 2.0 access token for the Zoom API, prepended with "Bearer "

	This is used in the "Authorization" header in future API requests, and the
	returned string will be formatted such as "Bearer ABCDE12345"

	Access tokens are typically valid for 1 hour after the initial request.

	:return: Zoom API Access Token
	:rtype: str
	"""
	with open('./secrets/zoom.json', encoding='UTF-8') as zoom_credentials_file:
		zoom_credentials = json.load(zoom_credentials_file)

	base64_auth = base64.b64encode(
		f"{zoom_credentials['client_id']}:{zoom_credentials['client_secret']}"
		.encode("ascii")
		).decode("ascii")

	url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={zoom_credentials['account_id']}"
	payload = {}
	headers = {
		'Authorization': f"Basic {base64_auth}"
	}
	response = requests.request("POST", url, headers=headers, data=payload)
	access_token = f"Bearer {response.json()['access_token']}"

	return access_token

def get_zoom_user(userid, access_token):
	"""
	Look up a user by their email address. Requires access token.

	:param userid: Email address of user to look up
	:type userid: str
	:param access_token: Zoom API Access Token
	:type access_token: str
	:return: JSON object response from user lookup
	:rtype: json
	"""
	url = f"https://api.zoom.us/v2/users/{userid}"
	payload = {}
	headers = {
		'Authorization': access_token
	}
	response = requests.request("GET", url, headers=headers, data=payload)
	return response.json()

def get_zoom_users(access_token):
	"""
	Get all users' email address and license type.

	This paginates through every page of users returned in the GET request
	for all users. This function returns a dictionary of users, and the
	key is their email, while the value is their license type.

	License types:
		1 - Basic
		2 - Licensed
		99 - None (this can only be set with ssoCreate)

	:param access_token: Zoom API Access Token
	:type access_token: str
	:return: Dictionary of all users and their license types
	:rtype: dict(str:int)
	"""
	url = "https://api.zoom.us/v2/users?page_size=300&status=active"
	payload = {}
	headers = {
		'Authorization': access_token
	}
	response = requests.request("GET", url, headers=headers, data=payload).json()

	users = dict()
	for user in response["users"]:
		users[user["email"]] = user["type"]

	next_page_token = response["next_page_token"]
	for i in range(2, response["page_count"] + 1):
		next_page_url = url + "&next_page_token=" + next_page_token
		next_page_response = requests.request("GET", next_page_url,
			headers=headers, data=payload).json()
		
		next_page_token = next_page_response["next_page_token"]

		for user in next_page_response["users"]:
			users[user["email"]] = user["type"]

	return users

def get_oracle_users():
	"""
	Gets a list of users who should have Zoom licenses.
	
	Pulls information based on SQL query in
		./sql/licensed_zoom_users.sql

	:return: List of emails from Oracle database
	:rtype: list
	"""
	with open('./secrets/oracle_conn.json', encoding='UTF-8') as oracle_credentials_file:
		oracle_credentials = json.load(oracle_credentials_file)
	oracle_conn = oracledb.connect(
        user = oracle_credentials["username"],
        password = oracle_credentials["password"],
        dsn = oracle_credentials["connection string"]
    )
	with open('./sql/licensed_zoom_users.sql', encoding='UTF-8') as sql_file:
		sql = sql_file.read()
	with oracle_conn:
		with oracle_conn.cursor() as cursor:
			cursor.execute(sql)
			query = cursor.fetchall()

	users = [user[0] for user in query]
	return users

def get_zoom_groups(access_token):
	"""
	Gets every group in our account. Requires access token.

	:param access_token: Zoom API Access Token
	:type access_token: str
	:return: JSON object response from group lookup
	:rtype: json
	"""
	url = "https://api.zoom.us/v2/groups"
	payload = {}
	headers = {
		'Authorization': access_token
	}
	response = requests.request("GET", url, headers=headers, data=payload)
	return response.json()["groups"]

def get_zoom_group_members(id, access_token):
	"""
	Gets all the members of a given group in Zoom. Requires access token.

	:param id: ID of group in Zoom
	:type id: str
	:param access_token: Zoom API Access Token
	:type access_token: str
	:raises Exception: Errors out if a group has more than 300 members (can be updated to paginate)
	:return: JSON object response from member lookup
	:rtype: json
	"""
	url = f"https://api.zoom.us/v2/groups/{id}/members?page_size=300"
	payload = {}
	headers = {
		'Authorization': access_token
	}
	response = requests.request("GET", url, headers=headers, data=payload)

	# We can make this support groups of more than 300 members if we paginate
	# the response like we do in the get_zoom_users function
	if response.json()["page_count"] != 1:
		raise Exception("ERROR: Groups with >300 members not currently supported!")
	
	return response.json()["members"]

def remove_zoom_license(userid, access_token):
	"""
	Look up a user by their email address. Requires access token.

	:param userid: Email address of user to look up
	:type userid: str
	:param access_token: Zoom API Access Token
	:type access_token: str
	:return: Response from patch request
	:rtype: response
	"""
	url = f"https://api.zoom.us/v2/users/{userid}"

	payload = json.dumps({
		"type": 1
	})
	headers = {
		"Content-Type": "application/json",
		"Authorization": access_token
	}

	response = requests.request("PATCH", url, headers=headers, data=payload)

	return response

def send_email(subject, body_plaintext, body_html, sender, recipient):
    """
    Send an email via mail server

    :param subject: Subject line
    :type subject: str
    :param body_plaintext: Message body, in plain text
    :type body_plaintext: str
    :param body_html: Message body, optionally formatted with HTML
    :type body_html: str
    :param sender: Message sender
    :type sender: str
    :param recipient: Message recipient
    :type recipient: str
    :return: True if message was sent, False if there was an exception
    :rtype: bool
    """
    HOST = 'MAILSERVER.EXAMPLE.COM'
    PORT = 25

    # Build email
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.attach(MIMEText(body_plaintext, 'plain'))
    message.attach(MIMEText(body_html, 'html'))

    # Send email
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.sendmail(sender, recipient, message.as_string())
    except Exception as _:
        return False
    return True

def main():
	oracle_users = get_oracle_users()
	access_token = get_zoom_access_token()
	zoom_users = get_zoom_users(access_token)

	group_users = []
	for group in get_zoom_groups(access_token):
		for member in get_zoom_group_members(group["id"], access_token):
			group_users.append(member["email"])

	bad_users = []
	for user, license in zoom_users.items():
		if user not in oracle_users and \
		user not in group_users and \
		license == 2:
			bad_users.append(user)

	for user in bad_users:
		print(f'Removing Zoom license from userid: "{user}"')
		remove_zoom_license(user, access_token)
	print(f'number of bad users: {len(bad_users)}')

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		error_text = f"{traceback.format_exc()}"
		send_email("Zoom License Remover Error", error_text, error_text,
							"server@example.com", "it@example.com")
		sys.exit(-1)
