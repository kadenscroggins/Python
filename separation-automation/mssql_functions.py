"""
Functions for interfacing with the mssql server
"""
import json
import pymssql

def connect_to_mssql():
    """
        Connect to the mssql database and return the connection

        :returns: pymssql connection
        :rtype: Connection
    """
    with open('./secrets/mssql_conn.json', encoding='UTF-8') as credentials_file:
        credentials = json.load(credentials_file)

    connection = pymssql.connect(
        credentials["server"],
        credentials["user"],
        credentials["password"],
        credentials["database"]
    )

    return connection

def mssql_run_query(sql, username=None, message=None):
    """
    Runs a query on the mssql database with optional logging

    :param str sql: SQL to execute
    :param str username: Optional username for logging
    :param str message: Optional message to write to log
    """
    connection = connect_to_mssql()
    cursor = connection.cursor()

    cursor.execute(sql)
    connection.commit()

    if message is not None and username is not None:
        with open('./sql/update_mssql_log.sql', encoding='UTF-8') as sql_file:
            log_sql = sql_file.read()

        log_sql = log_sql.format(username, message)

        cursor.execute(log_sql)
        connection.commit()

    connection.close()

def mssql_disable(username, message=None):
    """
    Disables a user in mssql with optional logging

    :param str username: Username
    :param str message: Optional message to write to log
    """
    with open('./sql/disable_mssql.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()

    sql = sql.format(username)

    mssql_run_query(sql, username, message)

def mssql_set_student(username, message=None):
    """
    Changes a user's type to Student in mssql with optional logging

    Assumes that they were previously set as Faculty or Staff

    :param str username: Username
    :param str message: Optional message to write to log
    """
    with open('./sql/set_student_mssql.sql', encoding='UTF-8') as sql_file:
        sql = sql_file.read()

    sql = sql.format(username)

    mssql_run_query(sql, username, message)

def mssql_log(username, message):
    """
    Writes an entry to a user's mssql log

    :param str username: Username
    :param str message: Message to write to log
    """
    with open('./sql/update_mssql_log.sql', encoding='UTF-8') as sql_file:
        log_sql = sql_file.read()

    log_sql = log_sql.format(username, message)

    connection = connect_to_mssql()
    cursor = connection.cursor()
    cursor.execute(log_sql)
    connection.commit()
    connection.close()
