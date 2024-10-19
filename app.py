import os
import math
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd, check_number
from datetime import datetime

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

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
# db = SQLAlchemy(app)


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
    name = db.execute("select username from users where id = ?",
                      session["user_id"])[0]["username"]
    cash = db.execute("select cash from users where id = ?",
                      session["user_id"])[0]["cash"]
    data = db.execute(
        "select * from status where username=?;", name)
    total = cash
    for d in data:
        p = lookup(d["symbol"])
        d.update({"price": p["price"],
                 "total": d["quantity"]*p["price"]})
        total += d["quantity"]*p["price"]
    print(len(data), cash, total)
    return render_template("/index.html", data=data, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")

        if not check_number(shares):
            return apology("Enter a valid number of shares ",400)

        if not symbol:
            return apology("Must Give Symbol")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Symbol Does Not Exist")

        shares = float(shares)

        if shares <= 0:
            return apology("Share Not Allowed")

        transaction_value = shares * stock["price"]

        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        name=db.execute("select username from users where id = ?",user_id)[0]["username"]
        user_cash = user_cash_db[0]["cash"]

        if user_cash < transaction_value:
            return apology("Not Enough Money")
        uptd_cash = user_cash - transaction_value

        db.execute("UPDATE users SET cash = ? WHERE id = ?", uptd_cash, user_id)

        date = datetime.now().strftime('%Y-%m-%d')

        db.execute("INSERT INTO history (username, symbol, quantity, price, date,total,status) VALUES (?, ?, ?, ?, ?, ?,?)", name, stock["symbol"], shares, stock["price"], date, transaction_value,"buy")




        quantity = shares
        total = transaction_value
        if db.execute("select * from status where username = ? and symbol = ?", name, symbol):
            i = float(db.execute("select quantity from status where username = ? and symbol = ?",name, symbol)[0]["quantity"])
            # m = float(db.execute("select total from status where username = ? and symbol = ?",name, symbol)[0]["total"])

            m= i*stock["price"]
            print(i,m)
            total=total+m
            quantity += i
            db.execute("update status set quantity = ?,price = ?,total= ? where username =? and symbol =?",
                       quantity,stock["price"],total, name, symbol)
        else:
            db.execute("insert into status(username,symbol,quantity,price,total) values(?,?,?,?,?) ",
                       name, symbol, quantity,stock["price"],total)



        # net=float(db.execute("select sum(total) as net from status where username =? group by username",name)[0]["net"])
        # print(net)
        # net=net+uptd_cash
        # print(net)


        net=0
        list = db.execute("select * from status where username=?",name)
        for l in list:
            print(net)
            price = lookup(l["symbol"])["price"]
            net= net+(l["quantity"]* price)
        net= net+ uptd_cash
        print(net)




        data ={"symbol":symbol,
               "shares":shares,
               "price": stock["price"],
               "total": transaction_value,
               "cash":uptd_cash,
               "net":net}




        flash(f"Bought! {int(shares)} shares of {symbol} each ${stock["price"]} total: ${transaction_value}")
        return render_template("bought.html",data=data)



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    name = db.execute(
        "select username from users where id = ?", session["user_id"])[0]["username"]
    data = db.execute(
        "select * from history where username= ? order by id desc", name)
    return render_template("/history.html", data=data)


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get(
                "username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/setting", methods=["GET", "POST"])
def setting():
    pas = db.execute("Select * from users where id =?", session["user_id"])
    if request.method == "POST":
        if not check_password_hash(request.form.get("oldPass"), pas[0]["hash"]):
            return apology("InCorrect Password")
        elif not request.form.get("newPass") == request.form.get("confirmPass"):
            return apology("Both Password Does Not Match", 403)
        db.execute("update users set hash=? where id =?", generate_password_hash(
            request.form.get("newPass")), session["user_id"])
    return render_template("setting.html")


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
    if request.method == 'POST':
        if not request.form.get("symbol"):
            return apology("symbol field is empty", 400)
        else:
            res = lookup(request.form.get("symbol"))
            if not res:
                return apology("something went wrong", 400)
            return render_template("/quoted.html", res=res)
    else:
        return render_template("/quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == 'POST':
        if not request.form.get("username"):
            return apology("Must Enter Your Username", 400)
        elif not request.form.get("password"):
            return apology("Must Enter Your Password", 400)
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("Your Password does not match to each others ", 400)
        elif db.execute("select * from users where username = ?", request.form.get("username")):
            return apology("username already exist.", 400)

        db.execute("insert into users (username,hash) values(?,?)", request.form.get(
            "username"), generate_password_hash(request.form.get("password")))

        # Remember which user has logged in
        user = db.execute(
            "select id from users where username = ?", request.form.get("username"))

        session["user_id"] = user[0]["id"]
        return redirect("/")

    else:
        return render_template("/register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    name = db.execute(
            "select username from users where id = ?", session["user_id"])

    if request.method == "POST":
        res = lookup(request.form.get("symbol"))
        quantity = float(request.form.get("shares"))
        if not check_number(quantity):
            return apology("Enter a valid number of shares ",400)

        # name = db.execute(
        #     "select username from users where id = ?", session["user_id"])
        cash = db.execute(
            "select cash from users where id = ?", session["user_id"])
        price = res["price"]
        date = datetime.now().strftime('%Y-%m-%d')
        total = price * quantity
        left = cash[0]["cash"] + total
        status = "sell"
        db.execute("update users set cash = ? where id = ?",
                   left, session["user_id"])
        print(cash[0]["cash"])
        symbol = res["symbol"]

        if not db.execute("select * from status where username = ? and symbol = ?", name[0]["username"], symbol):
            return apology("you don`t have this stocks")
        i = float(db.execute("select quantity from status where username = ? and symbol = ?",
                  name[0]["username"], symbol)[0]["quantity"])
        q = quantity
        print(i)
        if q > i:
            return apology("not enough stocks")
        elif q <= 0:
            return apology("you can`t sell negative or zero number of stocks")
        else:
            i = i-q

        if i <= 0:
            db.execute("delete from status where symbol=?", symbol)

        db.execute("update status set quantity = ? where username = ? and symbol = ?",
                   i, name[0]["username"], symbol)

        data = {"symbol": res["symbol"],
                "name": name,
                "price": price,
                "quantity": quantity,
                "cash": cash[0]["cash"],
                "total": total,
                "left": left,
                "status": "sell",
                "date": date}
        db.execute("insert into history(username,symbol,date,quantity,price,total,status) values(?,?,?,?,?,?,?)",
                   name[0]["username"], symbol, date, quantity, price, total, status)
        flash("Soled")
        return render_template("/sell.html", data=data)

    list = db.execute("select symbol from status where username=?",name[0]["username"])
    print(list)
    return render_template("/sell.html",list=list)
