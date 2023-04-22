"""
Functions for interfacing with oracle database
"""
import json
import oracledb


def connect_to_oracle() -> oracledb.Connection:
    """
    Connect to oracle and return the connection object

    :returns: Database connection
    :rtype: Connection
    """
    with open('./secrets/oracle_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)

    return oracledb.connect(
        user = credentials["username"],
        password = credentials["password"],
        dsn = credentials["connection string"]
    )

def get_username(uuid) -> str:
    """
    Gets username stored in the database for a given oracle ID

    :param str oracle_id: oracle ID
    :returns: Username
    :rtype: str
    :throws ValueError: Thrown if no user associated with oracle_id is found
    """
    with open('./sql/username.sql', encoding='UTF-8') as username_sql_file:
        username_sql = username_sql_file.read()

    username_sql = username_sql.format(uuid)

    result = run_query(username_sql)
    if len(result) == 0:
        raise ValueError(f"Invalid uuid: {uuid}")

    username = result[0][0]
    return username

def student_query(oracle_id) -> bool:
    """
    Determine if a user is a current or recent student

    "Current or Recent" means having been enrolled some time within
    the last two years, or admitted for an upcoming term up to one
    year in the future

    :param str oracle_id: oracle ID
    :returns: True if the user is a current or recent student, False otherwise
    :rtype: bool
    :throws RuntimeError: Thrown if query returns multiple rows
    """
    with open('./sql/students.sql', encoding='UTF-8') as students_sql_file:
        students_sql = students_sql_file.read()

    students_sql = students_sql.format(oracle_id)
    results = run_query(students_sql)

    # Query returns a list of tuples, we need to get it and verify there's 1 and only 1 result.
    if (len(results) == 1) and (len(results[0]) == 1):
        return True
    if (len(results) > 1) or (len(results) == 1 and len(results[0]) > 1):
        raise RuntimeError(f"students_sql returned too many rows for oracleID: {oracle_id}")
    return False

def admission_query(uuid) -> bool:
    """
    Determine if a user has any admission dates or course enrollments within 2 years

    This function is designed to be a more permissive version of the student_query
    function, since the student_query function will check to see if a student actually
    took classes for their admitted terms. This function also runs quicker than the
    student_query function, as it does not check historic student data tables.

    :param int uuid: uuid
    :returns: True if the user has any admission dates or enrollments within 2 years, else false
    :rtype: bool
    """
    with open('./sql/registration.sql', encoding='UTF-8') as registration_sql_file:
        registration_sql = registration_sql_file.read()
        registration_sql = registration_sql.format(uuid)
        registration = run_query(registration_sql)

    with open('./sql/admission.sql', encoding='UTF-8') as admission_sql_file:
        admission_sql = admission_sql_file.read()
        admission_sql = admission_sql.format(uuid)
        admission = run_query(admission_sql)

    if len(registration) > 0 or len(admission) > 0:
        return True
    return False

def employee_query(oracle_id) -> bool:
    """
    Figure out if the user has an active employment record.

    We want to exit the process if their employment record is active
    since they may have moved their last work date forwards or maybe have been
    re-hired or changed their mind about resigning by the time their
    ticket has begun being processed.

    :param str oracle_id: oracle ID
    :returns: True if the user's Employment Record is active, False otherwise
    :rtype: bool
    :throws RuntimeError: Thrown if query returns multiple rows
    """
    with open('./sql/employees.sql', encoding='UTF-8') as employees_sql_file:
        employees_sql = employees_sql_file.read()

    employees_sql = employees_sql.format(oracle_id)
    results = run_query(employees_sql)

    # Query returns a list of tuples, we need to get it and verify there's 1 and only 1 result.
    if (len(results) == 1) and (len(results[0]) == 1):
        return True
    if (len(results) > 1) or (len(results) == 1 and len(results[0]) > 1):
        raise RuntimeError(f"employees_sql returned too many rows for oracleID: {oracle_id}")
    return False

def retiree_query(oracle_id) -> bool:
    """
    Figure out if the user is retired

    :param str oracle_id: oracle ID
    :returns: True if the user is retired, False otherwise
    :rtype: bool
    :throws RuntimeError: Thrown if query returns multiple rows
    """
    with open('./sql/retirees.sql', encoding='UTF-8') as retirees_sql_file:
        retirees_sql = retirees_sql_file.read()

    retirees_sql = retirees_sql.format(oracle_id)
    results = run_query(retirees_sql)

    # Query returns a list of tuples, we need to get it and verify there's 1 and only 1 result.
    if (len(results) == 1) and (len(results[0]) == 1):
        return True
    if (len(results) > 1) or (len(results) == 1 and len(results[0]) > 1):
        raise RuntimeError(f"retirees_sql returned too many rows for oracleID: {oracle_id}")
    return False

def run_query(sql) -> list:
    """
    Returns the result of the SQL query passed to it

    :param str sql: SQL query
    :returns: List of rows (as tuples) returned from query
    :rtype: list[tuple]
    """
    with connect_to_oracle() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

def get_status(oracle_id) -> int:
    """
    Returns the separation status type for a user
    
    Checks if the user is a current or recent student,
    retiree, or recently terminated employee.

    1 = Current or Recent Student
    2 = Retiree
    3 = Terminated

    Check retiree first, because if they're retired they have a special case.
    Check students second, retirees may have taken classes for professional development.
    Check employment status third, as if they aren't a student or retiree, they could
        still have an active employment record, in which case we want to throw an exception.
    
    :param str oracle_id: oracle ID
    :returns: Status code of separation type
    :rtype: int
    :throws RuntimeError: Thrown if an active Employment Record is found
    """
    uuid = get_uuid(oracle_id)

    if retiree_query(oracle_id): # Retirees sometimes have active employment records
        return 2 # Retired
    if employee_query(oracle_id): # Throw exception if employment record is active
        raise RuntimeError("Separation status could not be determined!" \
            + " User may still have an active Employment Record!")
    if admission_query(uuid):
        return 1 # Current or Recent Student
    return 3 # Terminated

def get_uuid(oracle_id) -> int:
    """
    Returns uuid of associated oracle ID

    :param str oracle_id: oracle ID
    :returns: uuid
    :rtype: int
    """
    with open('./sql/uuid.sql', encoding='UTF-8') as uuid_sql_file:
        uuid_sql = uuid_sql_file.read()

    uuid_sql = uuid_sql.format(oracle_id)
    results = run_query(uuid_sql)

    return results[0][0]

def get_oracle_account_info(oracle_id) -> str:
    """
    Gets Oracle account status and oracle permissions as a big string

    Uses multiple SQL files to pull in:
    - Oracle account status (Open, Locked, Expired & Locked)
    - Business Profiles
    - Direct Object Grants
    - Security Classes
    - Security Groups

    :param str username: Username
    :returns: String of account information
    :rtype: str
    """
    uuid = get_uuid(oracle_id)
    username = get_username(uuid)

    with open('./sql/oracle_status.sql', encoding='UTF-8') as oracle_status_sql_file:
        oracle_status_sql = oracle_status_sql_file.read()
        oracle_status_sql = oracle_status_sql.format(username)
        oracle_status = run_query(oracle_status_sql)
        if len(oracle_status) == 0:
            return f'No oracle account found for userid: {username}'

    with open('./sql/business_profiles.sql', encoding='UTF-8') as business_profiles_sql_file:
        business_profiles_sql = business_profiles_sql_file.read()
        business_profiles_sql = business_profiles_sql.format(username)
        business_profiles = run_query(business_profiles_sql)

    with open('./sql/direct_object_grants.sql', encoding='UTF-8') as direct_object_grants_sql_file:
        direct_object_grants_sql = direct_object_grants_sql_file.read()
        direct_object_grants_sql = direct_object_grants_sql.format(username)
        direct_object_grants = run_query(direct_object_grants_sql)

    with open('./sql/security_classes.sql', encoding='UTF-8') as security_classes_sql_file:
        security_classes_sql = security_classes_sql_file.read()
        security_classes_sql = security_classes_sql.format(username)
        security_classes = run_query(security_classes_sql)

    with open('./sql/security_groups.sql', encoding='UTF-8') as security_groups_sql_file:
        security_groups_sql = security_groups_sql_file.read()
        security_groups_sql = security_groups_sql.format(username)
        security_groups = run_query(security_groups_sql)

    info = ''
    info += f'Account "{oracle_status[0][0]}" is currently "{oracle_status[0][1]}"'
    info += '\n\nDirect Object Grants:'
    for grant in direct_object_grants:
        info += f'\n- {grant[0]} - {grant[1]}'
    info +='\n\nBusiness Profiles:'
    for profile in business_profiles:
        info += f'\n- {profile[0]}'
    info += '\n\nSecurity Classes:'
    for security_class in security_classes:
        info += f'\n- {security_class[0]}'
    info += '\n\nSecurity Groups:'
    for group in security_groups:
        info += f'\n- {group[0]}'

    return info
