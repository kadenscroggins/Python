# Python
A collection of Python scripts I've written.

---

### [reassign_tdx_tickets.py](https://github.com/kadenscroggins/Python/blob/main/reassign_tdx_ticket.py) - Reassigns TeamDynamix tickets from one requestor to another

---

### [separation-automation](https://github.com/kadenscroggins/Python/tree/main/separation-automation) - A large project that partially automates employee terminations in multiple systems
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
