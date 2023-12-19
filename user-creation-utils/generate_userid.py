"""Functions for generating unique usernames for Active Directory"""
import os.path
import json
import pyad
import logging
from pyad import aduser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import oracledb

def ad_user_id_exists(samaccountname, ad_username=None, ad_password=None):
    """
    Check if user ID exists in AD

    :param samaccountname: user id
    :type samaccountname: str
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    :raises e: raises up all pyad exceptions other than invalidResults
    :return: True if user id exists, False if it does not
    :rtype: bool
    """
    if ad_username is not None and ad_password is not None:
        logging.debug('Connecting to AD with user ID: %s', ad_username)
        pyad.pyad_setdefaults(ldap_server='defaultldapserver.example.com',
                              username=ad_username,
                              password=ad_password)
    try:
        _ = aduser.ADUser.from_cn(samaccountname)
        logging.debug('%s found in AD', samaccountname)
        return True
    except pyad.pyadexceptions.invalidResults as _:
        logging.debug('%s not found in AD', samaccountname)
        return False
    except Exception as e:
        logging.debug('An unexpected exception occured: %s', str(e))
        raise e

def db_user_id_exists(db_user_id):
    """
    Check if user ID is already in the database

    :param db_user_id: user id
    :type db_user_id: str
    :return: True if user id exists, False if it does not
    :rtype: bool
    """
    logging.debug('Opening ./secrets/db_conn.json')
    with open('./secrets/db_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)
    connection = oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

    logging.debug('Opening ./sql/external_username.sql')
    with open('./sql/external_username.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()
    sql = sql.format(db_user_id)

    logging.debug('Querying database for records containing %s', db_user_id)
    query = None
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            query = cursor.fetchall()
    query = query[0][0]

    if query == 0:
        logging.debug('%s not found in database', db_user_id)
        return False
    logging.debug('%s found in database', db_user_id)
    return True

def lms_user_id_exists(db_external_user):
    """
    Check if user ID is already in use in database

    :param db_user_id: user id
    :type db_user_id: str
    :return: True if user id exists, False if it does not
    :rtype: bool
    """
    logging.debug('Opening ./secrets/db_conn.json')
    with open('./secrets/db_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)
    connection = oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

    logging.debug('Opening ./sql/lms.sql')
    with open('./sql/lms.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()
    sql = sql.format(db_external_user)

    logging.debug('Querying database for LMS records containing %s', db_external_user)
    query = None
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            query = cursor.fetchall()
    query = query[0][0]

    if query == 0:
        logging.debug('%s not found in LMS', db_external_user)
        return False
    logging.debug('%s found in LMS', db_external_user)
    return True

def google_user_id_exists(user_id):
    """
    Queries the Google API to see if a user has an account in our workspace

    :param user_id: user id
    :type user_id: str
    :return: True if user id exists, False if it does not
    :rtype: bool
    """
    logging.debug('Building Google API connection')
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

    service = build('admin', 'directory_v1', credentials=creds, cache_discovery=False)

    logging.debug('Searching Google API for %s', user_id)

    results = service.users().list(customer='my_customer', maxResults=10,
                                   orderBy='email', query=(user_id + '@example.com')
                              ).execute()
    users = results.get('users', [])

    if users:
        logging.debug('%s found found in Google', user_id)
        return True
    logging.debug('%s not found in Google', user_id)
    return False

def user_id_exists(user_id, ad_username=None, ad_password=None, current_run=[]):
    """
    Coodrinate other functions to ensure username is unique in all systems

    :param user_id: user id
    :type user_id: str
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    :param current_run: list of usernames generated in the same run to prevent overlap
    :type current_run: list
    :return: user id
    :rtype: str
    """
    logging.debug('Checking uniqueness of User ID: %s', user_id)
    if not user_id in current_run and \
       not ad_user_id_exists(user_id, ad_username, ad_password) and \
       not db_user_id_exists(user_id) and \
       not lms_user_id_exists(user_id) and \
       not google_user_id_exists(user_id):
        return False
    return True

def generate_userid(first_name, last_name, ad_username=None, ad_password=None, current_run=[]):
    """
    Generate username based on our naming conventions.
    - First, try the first 8 characters of the user's last name
    - Second, try the first 7 characters of last name and first character of first name
    - Third, try the first 6 characters of last name and add a number from 01 to 99
    - Fourth, try the first 5 characters of last name and add a number from 100 to 999
    A fifth step to go from 1000 to 9999 was added since we are nearing 999 on some last names

    :param first_name: First name
    :type first_name: str
    :param last_name: Last name
    :type last_name: str
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    :param current_run: list of usernames generated in the same run to prevent overlap
    :type current_run: list
    :raises Exception: Thrown if for some reason a user ID could not be generated
    :return: generated user id
    :rtype: str
    """
    logging.debug('Generating User ID for user: %s %s', first_name, last_name)

    # Strip special characters and set to lowercase
    last_name = ''.join([character for character in last_name if character.isalpha()]).lower()
    first_name = ''.join([character for character in first_name if character.isalpha()]).lower()

    # Make sure bad data is not passed
    assert len(last_name) > 0
    assert len(first_name) > 0

    # Shorten if necessary
    last_name_eight = last_name[:min(8, len(last_name))]
    last_name_seven = last_name[:min(7, len(last_name))]
    last_name_six = last_name[:min(6, len(last_name))]
    last_name_five = last_name[:min(5, len(last_name))]
    last_name_four = last_name[:min(4, len(last_name))]

    if not user_id_exists(last_name_eight, ad_username=ad_username,
                          ad_password=ad_password, current_run=current_run):
        return last_name_eight
    if not user_id_exists(last_name_seven + first_name[0], ad_username=ad_username,
                            ad_password=ad_password, current_run=current_run):
        return last_name_seven + first_name[0]
    for i in range(1, 10): # 1-9
        if not user_id_exists(last_name_six + '0' + str(i), ad_username=ad_username,
                                ad_password=ad_password, current_run=current_run):
            return last_name_six + '0' + str(i)
    for i in range(10, 100): # 10-99
        if not user_id_exists(last_name_six + str(i), ad_username=ad_username,
                                ad_password=ad_password, current_run=current_run):
            return last_name_six + str(i)
    for i in range(100, 1000): # 100-999
        if not user_id_exists(last_name_five + str(i), ad_username=ad_username,
                                ad_password=ad_password, current_run=current_run):
            return last_name_five + str(i)
    for i in range(1000, 10000): # 1000-9999
        if not user_id_exists(last_name_four + str(i), ad_username=ad_username,
                                ad_password=ad_password, current_run=current_run):
            return last_name_four + str(i)
    logging.error('Username could not be generated for %s %s', first_name, last_name)
    raise Exception("Username could not be generated")

def gen_username_file(filepath, outfilepath, ad_username=None, ad_password=None):
    """
    Takes an input .csv of users' names and generates usernames

    This expects a plain text (not excel) .csv file with four columns in this order:
    - employeeNumber (employee ID)
    - givenName (First name)
    - sn (Last name)
    - uidNumber 
    There should be no header row and no blank line at the end, just content.

    This creates a .csv file with five columns in this order:
    - samaccountname (AD username)
    - employeeNumber (employee ID)
    - givenName (First name)
    - sn (Last name)
    - uidNumber 

    :param filepath: path to input file
    :type filepath: str
    :param outfilepath: path to output file
    :type outfilepath: str
    :param ad_username: active directory admin account username
    :type ad_username: str
    :param ad_password: active directory admin account password
    :type ad_password: str
    """
    users = []
    with open(filepath, encoding='UTF-8') as file:
        for line in file:
            columns = line.split(',')
            users.append({
                'employeeNumber': columns[0].strip(),
                'givenName': columns[1].strip(),
                'sn': columns[2].strip(),
                'uidNumber': columns[3].strip()
                })
    with open(outfilepath, 'w', encoding='UTF-8') as file:
        usernames = []
        for i, user in enumerate(users):
            username = generate_userid(
                user['givenName'],
                user['sn'],
                ad_username=ad_username,
                ad_password=ad_password,
                current_run=usernames
            )
            usernames.append(username)
            print(
                username
                + ',' + user['employeeNumber']
                + ',' + user['givenName']
                + ',' + user['sn']
                + ',' + user['uidNumber']
            )
            file.write(
                username
                + ',' + user['employeeNumber']
                + ',' + user['givenName']
                + ',' + user['sn']
                + ',' + user['uidNumber']
            )
            if i < len(users) - 1:
                file.write('\n')
