import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# zip filter
app.jinja_env.filters['zip'] = zip

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"  # Session store at local "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Create "purchase" & "history" table in "finance.db" database
    db.execute("CREATE TABLE IF NOT EXISTS purchase (id INTEGER NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, shares NUMERIC NOT NULL, FOREIGN KEY(id) REFERENCES users(id))")
    db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER NOT NULL, symbol TEXT NOT NULL, shares NUMERIC NOT NULL, transacted_price NUMERIC NOT NULL, transacted_date TEXT NOT NULL, FOREIGN KEY(id) REFERENCES users(id))")

    # Determine which page directed to the current page
        #referrer_url = request.referrer

        #if referrer_url is not None:
            #referrer_path = referrer_url.split('/', 3)[-1]

    # Query for symbol, name, share
    # SQL command "GROUP BY", "HAVING", "SUM", "WHERE"
    symbol_name_share = db.execute("SELECT symbol, name, shares FROM purchase WHERE id = ?", session.get("user_id"))


    symbol_market_price = []
    # Query for current market price
    for row in symbol_name_share:
        lookup_return = lookup(row["symbol"])
        symbol_market_price.append(lookup_return["price"])


    # Total price calculation
    j = 0
    each_share_total_amount = []
    for row in symbol_name_share:
        if j < len(symbol_name_share):
            share_amount = float(row["shares"]) * float(symbol_market_price[j])
            each_share_total_amount.append(share_amount)
            j += 1

    # Cash Remain
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session.get("user_id"))

    # Total value of share
    sum_of_share = 0
    for i in range(len(each_share_total_amount)):
        sum_of_share = sum_of_share + each_share_total_amount[i]

    # NAV
    net_asset_value = sum_of_share + cash[0]["cash"]

    return render_template("index.html", symbol_name_share=symbol_name_share, symbol_market_price=symbol_market_price, each_share_total_amount=each_share_total_amount, cash=cash, net_asset_value=net_asset_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Invalid_symbol", 400)
        elif not request.form.get("shares").isdigit():
            return apology("Please insert a numeric number", 400)
        elif (float(request.form.get("shares")) < 0):
            return apology("Please insert a positive number", 400)


        ticker_symbol = request.form.get("symbol")
        input_quantity = float(request.form.get("shares"))
        symbol_return = lookup(ticker_symbol)

        if symbol_return == None:
            return apology("Invalid symbol", 400)
        else:
            s_name = symbol_return["name"]
            s_price = float(symbol_return["price"])
            s_symbol = symbol_return["symbol"]

            cash_list = db.execute("SELECT cash FROM users WHERE id = ?", session.get("user_id"))
            cash = float(cash_list[0]['cash'])

            if cash <= 0:
                return apology("Insufficient funds, please reload.", 400)
            else:
                buy_amount = input_quantity * s_price
                if (cash - buy_amount) < 0:
                    return apology("Insufficient funds, please reload.", 400)
                else:
                    validate_return = db.execute("SELECT shares FROM purchase WHERE id = ? AND symbol = ?", session.get("user_id"), s_symbol)

                    if validate_return == []:
                        current_datetime = datetime.now()
                        db.execute("INSERT INTO purchase (id, symbol, name, shares) VALUES (?, ?, ?, ?)", session.get("user_id"), s_symbol, s_name, input_quantity)
                        db.execute("INSERT INTO history (id, symbol, shares, transacted_price, transacted_date) VALUES (?, ?, ?, ?, ?)", session.get("user_id"), s_symbol, input_quantity, s_price, current_datetime)

                        cash_remain = cash - buy_amount
                        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_remain, session.get("user_id"))
                        return redirect("/")

                    elif len(validate_return) == 1:
                        no_of_share_before = float(validate_return[0]["shares"])
                        no_of_share_after = no_of_share_before + input_quantity
                        current_datetime = datetime.now()
                        db.execute("UPDATE purchase SET shares = ? WHERE id = ? AND symbol = ?", no_of_share_after, session.get("user_id"), s_symbol)
                        db.execute("INSERT INTO history (id, symbol, shares, transacted_price, transacted_date) VALUES (?, ?, ?, ?, ?)", session.get("user_id"), s_symbol, input_quantity, s_price, current_datetime)

                        cash_remain = cash - buy_amount
                        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_remain, session.get("user_id"))
                        return redirect("/")

                    # validate = db.execute("SELECT symbol FROM purchase WHERE id = ?", session.get("user_id"))
                    #if validate == {}:
                    #    total_sum1 = s_price * input_quantity
                    #    db.execute("INSERT INTO purchase (id, symbol, name, shares, transacted_price, transacted_date) VALUES (?, ?, ?, ?, ?, ?)", session.get("user_id"), s_symbol, s_name, input_quantity, s_price, XXXXXXXX)
                    #    return redirect("/")
                    #else:
                    #    previous_purchase_price = db.execute("SELECT price FROM purchase WHERE id =?", session.get("user_id"))
                    #    previous_quantity = db.execute("SELECT shares FROM purchase WHERE id =?", session.get("user_id"))

                    #    new_quantity = previous_quantity + input_quantity
                    #    average_price = (previous_purchase_price + s_price) / new_quantity
                    #    total_sum2 = new_quantity * average_price
                    #    db.execute("UPDATE purchase SET shares = ?, price = ?, total = ? WHERE id = ? AND symbol = ?", new_quantity, average_price, total_sum2, session.get("user_id"), s_symbol)
                    #    return redirect("/")
    else:
        return render_template("buy.html")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    transaction_history = db.execute("SELECT symbol, shares, transacted_price, transacted_date FROM history WHERE id = ?", session.get("user_id"))
    return render_template("history.html", transaction_history=transaction_history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

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
    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Invalid_symbol", 400)

        ticker_symbol = request.form.get("symbol")
        symbol_return = lookup(ticker_symbol)

        if symbol_return == None:
            return apology("Invalid symbol", 400)
        else:
            s_name = symbol_return["name"]
            s_price = symbol_return["price"]
            s_symbol = symbol_return["symbol"]
            return render_template("quoted.html", s_name=s_name, s_price=s_price, s_symbol=s_symbol)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        if not request.form.get("username"):
            return apology("Please input username", 400)
        elif not request.form.get("password"):
            return apology("Please input password", 400)
        elif not request.form.get("confirmation"):
            return apology("Please input confirmation password", 400)

        """Register user"""
        name = request.form.get("username")
        password = request.form.get("password")
        pass_confirm = request.form.get("confirmation")

        name_validation = db.execute("SELECT * FROM users WHERE username = ?", name)
        if name_validation == []:
            if pass_confirm == password:
                hash_password = generate_password_hash(password)
                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", name, hash_password)
                rows = db.execute("SELECT id FROM users WHERE username = ?", name)
                session["user_id"] = rows[0]["id"]
                return redirect("/")
            else:
                return apology("Password does not match", 400)
        else:
            return apology("Username is already taken", 400)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Invalid_symbol", 400)
        elif not request.form.get("shares").isdigit():
            return apology("Please insert a numeric number", 400)
        elif (float(request.form.get("shares")) < 0):
            return apology("Please insert a positive number", 400)

        s_symbol = request.form.get("symbol")
        input_quantity = float(request.form.get("shares"))

        symbol_return = lookup(s_symbol)
        s_price = float(symbol_return["price"])

        validation = db.execute("SELECT shares FROM purchase WHERE id = ? AND symbol = ?", session.get("user_id"), s_symbol)
        no_of_shares = float(validation[0]["shares"])

        if (no_of_shares >= input_quantity):
            quantity_after_sell = no_of_shares - input_quantity

            cash_remain_before_sell = db.execute("SELECT cash FROM users WHERE id = ?", session.get("user_id"))
            cash_return = float(s_price) * input_quantity
            cash_remain_after_sell = float(cash_remain_before_sell[0]["cash"]) + cash_return

            if quantity_after_sell == 0:
                # Scenario when there is only 1 share purhcased in the history, then delete the records from the "purchase" table
                current_datetime = datetime.now()
                db.execute("DELETE FROM purchase WHERE id = ? AND symbol = ?", session.get("user_id"), s_symbol)
                db.execute("INSERT INTO history (id, symbol, shares, transacted_price, transacted_date) VALUES (?, ?, ?, ?, ?)", session.get("user_id"), s_symbol, -abs(input_quantity), s_price, current_datetime)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_remain_after_sell, session.get("user_id"))
                return redirect("/")
            else:
                # Scenario when the there is already record of the purchased stock, then updated the stock.
                current_datetime = datetime.now()
                db.execute("UPDATE purchase SET shares = ? WHERE id = ? AND symbol = ?", quantity_after_sell, session.get("user_id"), s_symbol)
                db.execute("INSERT INTO history (id, symbol, shares, transacted_price, transacted_date) VALUES (?, ?, ?, ?, ?)", session.get("user_id"), s_symbol, -abs(input_quantity), s_price, current_datetime)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_remain_after_sell, session.get("user_id"))
                return redirect("/")
        else:
            return apology("Portfolio does not have enough quantity of the selected share to sell.", 400)
    else:
        symbol_list = db.execute("SELECT symbol FROM purchase WHERE id = ?", session.get("user_id"))
        return render_template("sell.html", symbol_list=symbol_list)