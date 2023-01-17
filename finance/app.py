import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

now = datetime.now()
date_time = now.strftime("%Y-%m-%d %H:%M:%S")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/calc", methods=["GET"])
def calc():
    return render_template("calc.html")


@app.route("/search")
def search():
    q = request.args.get("q")
    if q:
        info = lookup(q)
        if info:
            price = info["price"]
        else:
            price = []
    else:
        price = []
    return jsonify(price)


@app.route("/", methods=["GET"])
@login_required
def index():
    """Show portfolio of stocks"""
    # Extract current cash
    user_id = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id = ?", user_id)[0]["username"]
    cash_current = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])

    # Extract symbol and shares from portfolio table and store in a list of dict
    portfolio = db.execute("SELECT symbol, shares FROM portfolios WHERE user_id = ?", user_id)

    # Lookup company name and price by looping through this list using symbol in every dict. Then add this data to list of dict.
    any_shares = 0
    all_stocks_value = 0
    for i in portfolio:
        company_name = lookup(i["symbol"])["name"]
        price_current = float(lookup(i["symbol"])["price"])
        shares_current = i["shares"]
        any_shares += shares_current
        value = shares_current * price_current
        all_stocks_value += value
        i.update({"company_name": company_name, "price_current": price_current, "value": value})

    # Calculate total value of Stocks and Cash
    total_value = all_stocks_value + cash_current

    # Send data to html
    return render_template("index.html", cash_current=cash_current, portfolio=portfolio, total_value=total_value, username=username, any_shares=any_shares)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_id = session["user_id"]
    cash_before = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])
    if request.method == "GET":
        return render_template("buy.html", cash_before=cash_before)
    elif request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        info = lookup(request.form.get("symbol"))

        # Check for errors
        if not symbol:
            return apology("symbol required")
        elif not shares:
            return apology("number required")
        elif info == None:
            return apology("Stock symbol does not exist")
        elif not shares.isdigit() or int(shares) <= 0:
            return apology("Invalid number")
        else:
            price = float(info["price"])
            cash_spent = float(shares) * price
            cash_after = cash_before - cash_spent
            transaction_type = "BUY"
            if cash_after < 0:
                return apology("Not enough cash")

            # Storing transaction data
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price, cash_before, cash_spent, cash_after, date_time, transaction_type) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       user_id, symbol, shares, price, cash_before, cash_spent, cash_after, date_time, transaction_type)

            # Updating user's cash
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_after, user_id)

            # If user_id has no shares of this symbol
            if len(db.execute("SELECT shares FROM portfolios WHERE user_id = ? AND symbol = ?", user_id, symbol)) == 0:
                db.execute("INSERT INTO portfolios (user_id, symbol, shares) VALUES(?, ?, ?)", user_id, symbol, shares)

            # If user_id already owns shares of this symbol
            else:
                shares_before = int(db.execute("SELECT shares FROM portfolios WHERE user_id = ? AND symbol = ?",
                                    user_id, symbol)[0]["shares"])
                shares_after = shares_before + int(shares)
                db.execute("UPDATE portfolios SET shares = ? WHERE user_id = ? AND symbol = ?", shares_after, user_id, symbol)
            return redirect("/")


@app.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    history = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
    hl = len(history)
    return render_template("history.html", history=history, hl=hl)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        info = lookup(request.form.get("symbol").upper())
        if info == None:
            return apology("Stock symbol does not exist")
        else:
            return render_template("quoted.html", info=info)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        users = db.execute("SELECT username FROM users")
        # If username already exists
        for i in users:
            if username in i.values():
                return apology("username already exists")
        if not username:
            return apology("username required")
        elif not password:
            return apology("password required")
        elif not confirmation:
            return apology("repeat password required")
        elif password != confirmation:
            return apology("passwords do not match")
        # If all OK, hash the password and insert data into database and start session.
        else:
            hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
            session["user_id"] = db.execute("SELECT id FROM users WHERE username IS ?", username)[0]["id"]
            print(session["user_id"])
            return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    symbols = db.execute("SELECT symbol FROM portfolios WHERE user_id = ?", user_id)
    cash_before = float(db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"])
    if request.method == "GET":
        return render_template("sell.html", symbols=symbols, cash_before=cash_before)
    elif request.method == "POST":
        symbol_sell = request.form.get("symbol")
        shares_sell = request.form.get("shares")
        # Check for errors.
        if not symbol_sell:
            return apology("symbol required")
        # If symbol is not on users portfolio
        found = 0
        for i in symbols:
            if symbol_sell == i["symbol"]:
                found += 1
        if found <= 0:
            return apology("invalid stock symbol")

        if not shares_sell:
            return apology("number required")
        elif not shares_sell.isdigit() or int(shares_sell) <= 0:
            return apology("invalid number")
        # If not enough shares
        shares_owned = db.execute("SELECT shares FROM portfolios WHERE user_id = ? AND symbol = ?",
                                  session["user_id"], symbol_sell)[0]["shares"]
        if int(shares_sell) > int(shares_owned):
            return apology("Unable to sell more shares than owned")
        else:
            price_sell = float(lookup(symbol_sell)["price"])
            cash_earned = float(shares_sell) * price_sell
            cash_after = cash_before + cash_earned
            transaction_type = "SELL"

            # Storing transaction data
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price, cash_before, cash_earned, cash_after, date_time, transaction_type) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       user_id, symbol_sell, shares_sell, price_sell, cash_before, cash_earned, cash_after, date_time, transaction_type)

            # Updating user's cash
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_after, user_id)

            # Update portfolio
            shares_after = int(shares_owned) - int(shares_sell)
            db.execute("UPDATE portfolios SET shares = ? WHERE user_id = ? AND symbol = ?", shares_after, user_id, symbol_sell)
            if shares_after == 0:
                db.execute("DELETE FROM portfolios WHERE symbol = ?", symbol_sell)
            return redirect("/")