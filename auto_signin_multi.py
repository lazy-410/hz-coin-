#!/usr/bin/env python3
"""
Auto sign in to NUEDC training website for multiple accounts.
"""

import json
import os
import sys
from signin import run_signin

def main():
    print('Starting auto signin process...')
    print(f'Current directory: {os.getcwd()}')
    print(f'Files in current directory: {os.listdir(".")}')
    
    # Get accounts from environment variable
    accounts_json = os.environ.get('NUEDC_ACCOUNTS')
    if not accounts_json:
        print('Error: NUEDC_ACCOUNTS environment variable not set')
        return
    
    # Check if notify.py exists
    if os.path.exists('notify.py'):
        print('notify.py file found')
    else:
        print('ERROR: notify.py file not found!')
    
    signin_results = {}
    
    try:
        accounts = json.loads(accounts_json)
        print(f'Found {len(accounts)} accounts')
        
        for account in accounts:
            username = account.get('username')
            password = account.get('password')
            
            if not username or not password:
                print(f'Skipping invalid account: {account}')
                continue
            
            print(f'\nSigning in for: {username}')
            try:
                result = run_signin(username, password, True)
                print(f'Signin result: {result}')
                signin_results[username] = result
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                print(f'Error signing in for {username}: {str(e)}')
                signin_results[username] = error_result
        
        # Send notification
        if signin_results:
            print('\nPreparing to send notification...')
            print(f'Number of signin results: {len(signin_results)}')
            
            # Try to import notify module
            try:
                # Add current directory to path
                sys.path.insert(0, '.')
                print(f'System path: {sys.path}')
                
                import notify
                print('Successfully imported notify module')
                
                # Test notification function
                print('Calling send_notification function...')
                notify.send_notification(signin_results)
                print('Notification function called successfully')
            except ImportError as e:
                print(f'Error importing notify module: {str(e)}')
                import traceback
                traceback.print_exc()
            except Exception as e:
                print(f'Error sending notification: {str(e)}')
                import traceback
                traceback.print_exc()
        else:
            print('No signin results to send notification for')
                
    except json.JSONDecodeError as e:
        print(f'Error parsing NUEDC_ACCOUNTS: {str(e)}')
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
