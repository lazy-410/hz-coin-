#!/usr/bin/env python3
"""
Send notification about signin results to Feishu or other platforms.
"""

import os
import json
import requests

def send_feishu_notification(webhook, title, content):
    """
    Send notification to Feishu (Lark) using webhook.
    """
    if not webhook:
        print('Feishu webhook not set, skipping notification')
        return False
    
    try:
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }
        
        response = requests.post(
            webhook,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print('Feishu notification sent successfully')
            return True
        else:
            print(f'Failed to send Feishu notification: {response.text}')
            return False
    except Exception as e:
        print(f'Error sending Feishu notification: {str(e)}')
        return False

def send_email_notification(to_email, subject, content):
    """
    Send notification via email.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Get email configuration from environment variables
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_email = os.environ.get('FROM_EMAIL', smtp_username)
    
    if not all([smtp_server, smtp_username, smtp_password, from_email]):
        print('Email configuration not set, skipping notification')
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'markdown'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        print('Email notification sent successfully')
        return True
    except Exception as e:
        print(f'Error sending email notification: {str(e)}')
        return False

def format_signin_result(result, username):
    """
    Format signin result as markdown content.
    """
    content = f"### 账号: {username}\n"
    
    if result.get('success'):
        content += f"✅ **签到成功**\n"
        content += f"- 状态: {result.get('info', '未知')}\n"
        if result.get('sign_count'):
            content += f"- 连续签到: {result['sign_count']} 天\n"
        if result.get('user_info'):
            user_info = result['user_info']
            if user_info.get('username'):
                content += f"- 当前账户: {user_info['username']}\n"
            if user_info.get('hz_coins'):
                content += f"- 赫兹币余额: {user_info['hz_coins']}\n"
    else:
        content += f"❌ **签到失败**\n"
        content += f"- 错误信息: {result.get('error', '未知错误')}\n"
    
    return content

def send_notification(signin_results):
    """
    Send notification for signin results.
    """
    print('Starting notification process...')
    
    # Get webhook from environment variable
    feishu_webhook = os.environ.get('FEISHU_WEBHOOK')
    email = os.environ.get('NOTIFICATION_EMAIL')
    
    print(f'Feishu webhook set: {bool(feishu_webhook)}')
    print(f'Email set: {bool(email)}')
    
    if not feishu_webhook and not email:
        print('No notification channels configured, skipping')
        return
    
    # Format content
    title = "NUEDC 自动签到结果"
    content = ""
    
    print(f'Preparing notification for {len(signin_results)} accounts...')
    
    for username, result in signin_results.items():
        content += format_signin_result(result, username)
        content += "\n---\n"
    
    print(f'Notification content prepared: {len(content)} characters')
    
    # Send notifications
    if feishu_webhook:
        print('Sending Feishu notification...')
        success = send_feishu_notification(feishu_webhook, title, content)
        print(f'Feishu notification sent: {success}')
    
    if email:
        print('Sending email notification...')
        success = send_email_notification(email, title, content)
        print(f'Email notification sent: {success}')
    
    print('Notification process completed')

if __name__ == '__main__':
    # Test notification
    test_results = {
        "user1@example.com": {
            "success": True,
            "info": "已签到",
            "sign_count": 5,
            "user_info": {
                "username": "user1",
                "hz_coins": 100
            }
        },
        "user2@example.com": {
            "success": False,
            "error": "账号密码错误"
        }
    }
    send_notification(test_results)
