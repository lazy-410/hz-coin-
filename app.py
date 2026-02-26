from flask import Flask, render_template, request
from signin import run_signin

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        verbose = request.form.get("verbose") == "on"
        
        if username and password:
            result = run_signin(username, password, verbose)
    
    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
