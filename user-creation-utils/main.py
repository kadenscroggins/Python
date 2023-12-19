"""Main script to orchestrate other functions together for user provisioning"""
import sys
import getpass
from generate_userid import generate_userid, gen_username_file
from create_users import create_ad_users, create_ad_user, gen_rand_pass, create_google_user, create_google_users

ad_username = input("Enter AD username: ").strip()
ad_password = getpass.getpass("Enter AD password: ").strip()

user_input = input('Type "many" to create users in bulk, ' \
                   + '"one" to create one, or hit enter to abort: ').lower().strip()
if user_input == 'many':
    input_filename = input('Enter input file location: ').strip()
    output_filename = input('Enter output file location: ').strip()
    gen_username_file(input_filename, output_filename,
                      ad_username=ad_username, ad_password=ad_password)
    print('File created:', output_filename)
    create_ad_users(output_filename, ad_username, ad_password)
    create_google_users(output_filename)
elif user_input == 'one':
    first_name = input('Enter first name: ').strip()
    last_name = input('Enter last name: ').strip()
    employee_id = input('Enter employee ID: ').strip()
    uid = input('Enter UID: ').strip()
    user_id = generate_userid(first_name, last_name)
    print("User ID generated:", user_id)
    rand_pass = gen_rand_pass(30)
    create_ad_user(user_id, first_name, last_name, employee_id, rand_pass, uid,
                   ad_username, ad_password)
    create_google_user(user_id, first_name, last_name, rand_pass)
else:
    print('Aborting process')
    sys.exit(0)
