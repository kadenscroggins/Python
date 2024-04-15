# Python
A collection of Python scripts I've written.

---

### [reassign_tdx_tickets.py](https://github.com/kadenscroggins/Python/blob/main/reassign_tdx_ticket.py) - Reassigns TeamDynamix tickets from one requestor to another

---

### [separation-automation](https://github.com/kadenscroggins/Python/tree/main/separation-automation) - A mostly solo project which I was the primary developer of, that partially automates employee terminations in multiple systems
* [separation_automation.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/separation_automation.py) - Main file that orchestrates everything
* [ad_functions.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/ad_functions.py) - Functions for interfacing with Microsoft Active Directory
* [google_functions.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/google_functions.py) - Functions for interfacing with the Google API via the [GAM](https://github.com/GAM-team/GAM) utility
* [mssql_functions.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/mssql_functions.py) - Functions for interfacing with our MSSQL database
* [oracle_functions.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/oracle_functions.py) - Functions for interfacing with the Oracle database behind our ERP system
* [tdx_functions.py](https://github.com/kadenscroggins/Python/blob/main/separation-automation/tdx_functions.py) - Functions for interfacing with our TeamDynamix ticketing system

I could talk a lot about this code, as I spent dozens of hours on it. A lot of the systems have been renamed, and information has been redacted, so as to not expose any sensitive information for the organization this code was for. The basic work flow is as follows:
1. Gather user information and determine what access needs to be removed
2. Deactivate them on the MSSQL database (unless they are a student or retiree)
3. Deactivate them in Active Directory (unless they are a student or retiree) and remove any security groups
3. Deactivate and deprovision them in Google Workspace (unless they are a student or retiree) and remove any (non-student and non-retiree) mailing list access
4. Verify that their Oracle access is locked, as we have a separate process that is more strict about Oracle security
5. Comment steps taken in our ticketing system and advance ticket workflow so that separation tickets take significantly less time

---

### [user-creation-utils](https://github.com/kadenscroggins/Python/tree/main/user-creation-utils) - A complete re-write of my institution's user provisioning process from scratch that I did on my own. During an incident response, the old server that did this process had to be decomissioned, and none of the code on it was salvageable, so I had to modernize it.
* [create_users.py](https://github.com/kadenscroggins/Python/blob/main/user-creation-utils/create_users.py) - Functions for creating users in Active Directory
* [generate_userid.py](https://github.com/kadenscroggins/Python/blob/main/user-creation-utils/generate_userid.py) - Functions for generating unique usernames for Active Directory
* [main.py](https://github.com/kadenscroggins/Python/blob/main/user-creation-utils/main.py) - Main script to orchestrate other functions together for user provisioning
* [main_auto.py](https://github.com/kadenscroggins/Python/blob/main/user-creation-utils/main_auto.py) - A hands-off version of main.py that can be ran without input
* [send_email.py](https://github.com/kadenscroggins/Python/blob/main/user-creation-utils/send_email.py) - Functions for sending emails via an email server

  As with other scripts, a lot of systems have been renamed, and information has been redacted so as to not expose any sensitive information. I also did not include any of the SQL scripts or email templates, as some of the information in those could be considered proprietary.

---

### [zoom_license_remover.py](https://github.com/kadenscroggins/Python/blob/main/zoom_license_remover.py) - A script that automatically removes Zoom licenses for users who are no longer elibile for them based on a query output. Uses Zoom groups as an allowlist, so anyone in any group keeps their license.
