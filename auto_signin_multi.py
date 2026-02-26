#!/usr/bin/env python3
"""
Auto sign in to NUEDC training website for multiple accounts.
"""

import json
import os
from signin import run_signin

def main():
    # Get accounts from environment variable
    accounts_json = os.environ.get('NUEDC_ACCOUNTS')
    if not accounts_json:
        print('Error: NUEDC_ACCOUNTS environment variable not set')
        return
    
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
            except Exception as e:
                print(f'Error signing in for {username}: {str(e)}')
                
    except json.JSONDecodeError as e:
        print(f'Error parsing NUEDC_ACCOUNTS: {str(e)}')
    except Exception as e:
        print(f'Unexpected error: {str(e)}')

if __name__ == '__main__':
    main()
