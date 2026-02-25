from flask import Flask, render_template, request, redirect, url_for
import json
import os
from signin import run_signin

app = Flask(__name__)

# 账号存储文件
ACCOUNTS_FILE = "accounts.json"

# 初始化账号存储
def init_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

# 加载账号
def load_accounts():
    init_accounts()
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 保存账号
def save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)

# 添加账号
def add_account(username, password, nickname=""):
    accounts = load_accounts()
    # 检查账号是否已存在
    for account in accounts:
        if account["username"] == username:
            return False, "账号已存在"
    # 添加新账号
    accounts.append({
        "username": username,
        "password": password,
        "nickname": nickname or username.split("@")[0]
    })
    save_accounts(accounts)
    return True, "账号添加成功"

# 删除账号
def delete_account(username):
    accounts = load_accounts()
    new_accounts = [acc for acc in accounts if acc["username"] != username]
    if len(new_accounts) == len(accounts):
        return False, "账号不存在"
    save_accounts(new_accounts)
    return True, "账号删除成功"

# 获取所有账号
def get_all_accounts():
    return load_accounts()

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    accounts = get_all_accounts()
    
    if request.method == "POST":
        # 处理签到请求
        if "username" in request.form and "password" in request.form:
            username = request.form.get("username")
            password = request.form.get("password")
            verbose = request.form.get("verbose") == "on"
            
            if username and password:
                result = run_signin(username, password, verbose)
        
        # 处理添加账号请求
        elif "add_username" in request.form and "add_password" in request.form:
            username = request.form.get("add_username")
            password = request.form.get("add_password")
            nickname = request.form.get("add_nickname")
            
            if username and password:
                success, message = add_account(username, password, nickname)
                result = {
                    "success": success,
                    "message": message
                }
        
        # 处理删除账号请求
        elif "delete_username" in request.form:
            username = request.form.get("delete_username")
            success, message = delete_account(username)
            result = {
                "success": success,
                "message": message
            }
        
        # 处理从保存的账号中选择签到
        elif "account_username" in request.form:
            username = request.form.get("account_username")
            accounts_list = get_all_accounts()
            account = next((acc for acc in accounts_list if acc["username"] == username), None)
            if account:
                verbose = request.form.get("verbose") == "on"
                result = run_signin(account["username"], account["password"], verbose)
    
    return render_template("index.html", result=result, accounts=accounts)

if __name__ == "__main__":
    init_accounts()
    app.run(debug=True, host="0.0.0.0", port=5000)
