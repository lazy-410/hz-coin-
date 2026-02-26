from flask import Flask, render_template, request, jsonify
from signin import run_signin

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        verbose = request.form.get("verbose") == "on"
        
        if username and password:
            result = run_signin(username, password, verbose)
            # 检查是否是 AJAX 请求（自动签到）
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
                return jsonify(result)
            return render_template("index.html", result=result)
    
    return render_template("index.html", result=None)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
