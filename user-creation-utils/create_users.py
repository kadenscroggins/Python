"""Functions for creating users in Active Directory"""
import secrets
import string
import os
import logging
import json
import oracledb
import pyad
from pyad import aduser
from pyad import adcontainer
from pyad import addomain
from pyad import adgroup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

def create_ad_user(samaccountname, givenName, sn, employeeNumber, password, uid,
                   ad_username, ad_password):
    """
    Create a user in Active Directory given account info and AD admin account credentials

    :param samaccountname: username
    :type samaccountname: str
    :param givenName: first name
    :type givenName: str
    :param sn: last name
    :type sn: str
    :param employeeNumber: employee ID
    :type employeeNumber: str
    :param password: initial password for user
    :type password: str
    :param uid: uid
    :type uid: int
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    """
    pyad.pyad_setdefaults(ldap_server='defaultldapserver.example.com',
                          username=ad_username,
                          password=ad_password)
    ou = pyad.adcontainer.ADContainer.from_dn("ou=users, dc=example, dc=com")
    user_exists = True
    try:
        user = aduser.ADUser.from_cn(samaccountname)
        print("User found, skipping user creation:", user)
    except pyad.pyadexceptions.invalidResults as _:
        user_exists = False
    if not user_exists:
        pyad.aduser.ADUser.create(samaccountname, ou, password=password, optional_attributes={
            "sn": sn,
            "givenName": givenName,
            "employeeNumber": employeeNumber,
            "mail": samaccountname + "@example.com",
            "displayName": givenName + " " + sn,
            "uidNumber": uid,
            "scriptPath": "user.bat"
        })

def create_ad_users(filepath, ad_username, ad_password):
    """
    Create multiple AD users from a given CSV file

    This expects a plain text (not excel) .csv file with five columns in this order:
    - samaccountname (AD username)
    - employeeNumber (Employee ID)
    - givenName (First name)
    - sn (Last name)
    - uidNumber
    There should be no header row and no blank line at the end, just content.

    :param filepath: path to input file
    :type filepath: str
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    """
    pyad.pyad_setdefaults(ldap_server='defaultldapserver.example.com',
                          username=ad_username,
                          password=ad_password)
    users = load_users_csv_noheaders(filepath)
    for user in users:
        create_ad_user(
            user['samaccountname'],
            user['givenName'],
            user['sn'],
            user['employeeNumber'],
            gen_rand_pass(30),
            user['uidNumber'],
            ad_username,
            ad_password
        )

def gen_rand_pass(length):
    """
    Generate a random password.

    :param length: Length of password desired
    :type length: int
    :return: Randomly generated password
    :rtype: str
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = 'Aa1!' # forcibly meet password requirements
    for _ in range(length):
        password += ''.join(secrets.choice(alphabet))
    return password

def load_users_csv_noheaders(filepath):
    """
    Loads a CSV file into a list

    This expects a plain text (not excel) .csv file with five columns in this order:
    - samaccountname (AD username)
    - employeeNumber (Employee ID)
    - givenName (First name)
    - sn (Last name)
    - uidNumber
    There should be no header row and no blank line at the end, just content.

    :param filepath: Path to input CSV file
    :type filepath: str
    :return: List of dictionaries containing keys: samaccountname, employeeNumber, givenName, sn
    :rtype: List[Dict]
    """
    users = []
    with open(filepath, encoding='UTF-8') as file:
        for line in file:
            columns = line.split(',')
            users.append({
                'samaccountname': columns[0].strip(),
                'employeeNumber': columns[1].strip(),
                'givenName': columns[2].strip(),
                'sn': columns[3].strip(),
                'uidNumber': columns[4].strip()
                })
    return users

def create_google_user(user_id, first_name, last_name, password):
    """
    Inserts a new user into Google Workspace

    :param user_id: username
    :type user_id: str
    :param first_name: first name
    :type first_name: str
    :param last_name: last name
    :type last_name: str
    :param password: randomly generated password
    :type password: str
    """
    SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('./secrets/token.json'):
        creds = Credentials.from_authorized_user_file('./secrets/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                './secrets/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('./secrets/token.json', 'w', encoding='UTF-8') as token:
            token.write(creds.to_json())

    service = build('admin', 'directory_v1', credentials=creds)

    user_info = {
        'primaryEmail': user_id + '@example.com',
        'name': {
            'givenName': first_name,
            'familyName': last_name
        },
        'password': password
    }

    service.users().insert(body = user_info).execute()

def create_google_users(filepath):
    """
    Create multiple Google users from a given CSV file

    This expects a plain text (not excel) .csv file with four columns in this order:
    - samaccountname
    - employeeNumber
    - givenName
    - sn
    There should be no header row and no blank line at the end, just content.

    :param filepath: path to input file
    :type filepath: str
    """
    users = load_users_csv_noheaders(filepath)
    for user in users:
        create_google_user(
            user['samaccountname'],
            user['givenName'],
            user['sn'],
            gen_rand_pass(30)
        )

def push_db_user(user_id, pidm, employee_id, birth_date):
    """
    Insert user information into database

    :param user_id: username
    :type user_id: str
    :param pidm: pidm
    :type pidm: int
    :param employee_id: employee ID
    :type employee_id: str
    :param birth_date: birthday
    :type birth_date: str
    """
    logging.debug('Opening ./secrets/db_conn.json')
    with open('./secrets/db_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)
    connection = oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

    logging.debug('Opening ./sql/push_new_users.sql')
    with open('./sql/push_new_users.sql', encoding='UTF-8') as new_user_sql_file:
        new_user_sql = new_user_sql_file.read()
        new_user_sql = new_user_sql.format(employee_id, birth_date, user_id)

    logging.debug('Opening ./sql/insert_email.sql')
    with open('./sql/insert_email.sql', encoding='UTF-8') as email_sql_file:
        email_sql = email_sql_file.read()
        email_sql = email_sql.format(user_id + '@example.com', pidm)

    logging.debug('Inserting %s into email table and new user table on PIDM %s', user_id, pidm)
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(email_sql)
            cursor.execute(new_user_sql)
            connection.commit()
    logging.debug('Database insertion committed!')
