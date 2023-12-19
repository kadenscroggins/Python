"""Provision users auto-magically"""
import json
import logging
from datetime import datetime
import os
import oracledb
from generate_userid import generate_userid
from send_email import send_welcome_email
from create_users import create_ad_user, create_google_user, gen_rand_pass, push_db_user

def pull_db_users():
    """
    Query database for users that need accounts

    :return: List of multiple dictionaries containing single user info
    :rtype: list
    """
    logging.debug('Opening ./secrets/db_conn.json')
    with open('./secrets/db_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)
    connection = oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

    logging.debug('Opening ./sql/pull-users.sql')
    with open('./sql/pull-users.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()

    logging.debug('Querying database for users that need to be provisioned')
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            query = cursor.fetchall()
    logging.debug('database query complete! Loading data from results.')

    users = []
    for row in query:
        if row[3] is None:
            logging.warning('%s - %s %s has no date of birth in the database,' \
                            + ' they will not be provisioned (PIDM: %d)',
                            row[0], row[1], row[2], row[4])
            continue
        users.append({ # Strip all strings - PIDM is an Int
            'employee_id': row[0].strip(),
            'first_name': row[1].strip(),
            'last_name': row[2].strip(),
            'uid': row[3].strip(),
            'database_pidm': row[4],
            'birth_date': row[5].strip()
        })
        logging.debug('%s - %s %s will be provisioned (PIDM: %d)', row[0], row[1], row[2], row[4])

    return users

def pull_database_personal_email(pidm):
    logging.debug('Opening ./secrets/db_conn.json')
    with open('./secrets/db_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)
    connection = oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

    logging.debug('Opening ./sql/personal_email.sql')
    with open('./sql/personal_email.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()
    sql = sql.format(pidm)

    logging.debug('Querying database for personal email of PIDM: %s', pidm)
    query = None
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            query = cursor.fetchall()

    if len(query) == 0:
        logging.warning('No personal email found for PIDM: %s', pidm)
        return None
    personal_email = query[0][0]
    logging.debug('Most recent personal email: %s', personal_email)

    return personal_email

def main():
    """Provision users"""

    logging.debug('Opening ./secrets/ad_conn.json')
    with open('./secrets/ad_conn.json', encoding='UTF-8') as ad_credentials_file:
        ad_credentials = json.load(ad_credentials_file)
        ad_username = ad_credentials['username']
        ad_password = ad_credentials['password']
    logging.debug('AD credentials loaded')

    logging.info('Pulling database users to provision')
    users = pull_db_users()

    if len(users) == 0:
        logging.info('No users to provision, exiting program.')
        exit(0)

    logging.info('Generating usernames')
    current_run_usernames = []
    for user in users:
        user_id = generate_userid(
            user['first_name'],
            user['last_name'],
            ad_username,
            ad_password,
            current_run_usernames)

        current_run_usernames.append(user_id)
        user['user_id'] = user_id
        logging.info('Generated user ID: "%s" for %s - %s %s',
                     user_id, user['employee_id'], user['first_name'], user['last_name'])

    # Provision
    for user in users:
        user['personal_email'] = pull_database_personal_email(user['database_pidm'])
        logging.info("Provisioning the following account: '%s' for %s %s %s UID %s PERS %s DOB %s",
                     user['user_id'],
                     user['employee_id'],
                     user['first_name'],
                     user['last_name'],
                     user['uid'],
                     user['personal_email'],
                     user['birth_date'])

        logging.debug("Pushing %s into new user table", user['user_id'])
        push_db_user(user['user_id'],
                         user['database_pidm'],
                         user['employee_id'],
                         user['birth_date'])

        logging.debug("Pushing %s into AD", user['user_id'])
        create_ad_user(user['user_id'],
                       user['first_name'],
                       user['last_name'],
                       user['employee_id'],
                       gen_rand_pass(26),
                       user['uid'],
                       ad_username,
                       ad_password)

        logging.debug("Pushing %s into Google", user['user_id'])
        create_google_user(user['user_id'],
                           user['first_name'],
                           user['last_name'],
                           gen_rand_pass(26))

        if user['personal_email'] is not None:
            logging.debug('Sending welcome email to %s', user['personal_email'])
            send_welcome_email(user['personal_email'], user['user_id'])
        else:
            logging.warning('No welcome email sent to %s', user['personal_email'])

    logging.info('User provisioning process finished')

    # Output users provisioned to file
    with open(f'./logs/provisioned_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv',
              'w', encoding='UTF-8') as file:
        for i, user in enumerate(users):
            file.write(user['user_id']
                       + ',' + user['employee_id']
                       + ',' + user['first_name']
                       + ',' + user['last_name']
                       + ',' + datetime.now().strftime('%B %d')
                       + ',Yes,Yes')
            if i < len(users) - 1:
                file.write('\n')

if __name__ == '__main__':
    # Set up logging
    start_time = datetime.now()
    if not os.path.exists('./logs/'):
        os.makedirs('./logs/')
    logging.basicConfig(format='[%(levelname)s][%(asctime)s]: %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p',
            filename=f'./logs/provision_log_{start_time.strftime("%Y-%m-%d_%H-%M-%S")}.log',
            encoding='utf-8',
            level=logging.DEBUG)
    logging.info('User provisioning process started')

    try:
        main()
    except Exception as e:
        logging.critical('Unhandled exception thrown! Dumping stack trace', exc_info=True)
        exit(-1)
