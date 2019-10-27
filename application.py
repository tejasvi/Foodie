import os
from cs50 import SQL
from flask import Flask, redirect, render_template, request, make_response
from helpers import *
from uuid import uuid1
from hashlib import md5
import smtplib
import random
import datetime

app = Flask(__name__)
app.config['DEBUG'] = True

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure CS50 Library to use SQLite database
if 'DATABASE_URL' not in os.environ:
    os.environ['DATABASE_URL'] = 'postgres://wfgsdjtquzwfjk:12337c00cf6508ef19f3a2233bd465dcf353c2a79f55465bb179daa03c992020@ec2-54-83-33-14.compute-1.amazonaws.com:5432/d99mg44bt7uoar'

foodie = SQL(os.environ['DATABASE_URL'])
foodie.execute("SET SESSION idle_in_transaction_session_timeout = 30000")
@app.route("/")
@login_required
def index():
    """Show items"""
    key = request.cookies.get('key')
    week, phase, tidnow = time()
    tid = foodie.execute("SELECT tid FROM users WHERE key=:key",
    key=key)[0]["tid"]
    # if tid == tidnow:
    #     return redirect ("/stats")

    fid = listitems(key)

    items = {}
    for id in fid:
        items[id] = foodie.execute("SELECT fname FROM fname WHERE fid=:id",
        id=id)[0]["fname"]

    foodie.conn.close()
    return render_template("index.html", items=items)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        foodie.conn.close()
        return render_template("login.html")

    email = request.form.get("email")
    otp = request.form.get("otp")

    if email:
        email = email.lower()
        if '@' not in email:
            email += '@iitg.ac.in'
        uid = md5(email.encode()).hexdigest()
        key = str(uuid1())
        otp = random.randint(100, 999)
        foodie.execute("INSERT INTO verification (uid, otp, key, attempts) VALUES (:uid, :otp, :key, 0)",
        uid=uid, otp=otp, key=key)
        print(otp)
        sendotp(email, otp)
        hostels = foodie.execute("SELECT * FROM hname")

        resp = make_response(render_template("login.html", next=1, hostels=hostels))
        resp.set_cookie('key', key, expires=datetime.datetime.now() + datetime.timedelta(days=999))
        foodie.conn.close()
        return resp

    elif otp:
        key = request.cookies.get('key')
        hid = request.form.get("hid")
        if not hid:
            hostels = foodie.execute("SELECT * FROM hname")
            foodie.conn.close()
            return render_template("login.html", next=1, hostels=hostels, flash="Enter the hostel!")

        data = foodie.execute("SELECT otp, uid, attempts FROM verification WHERE key=:key",
        key=key)


        if len(data) == 1:
            if data[0]["attempts"] > 5:
                foodie.conn.close()
                return redirect("/login")
            stored_otp = data[0]["otp"]
            uid = data[0]["uid"]
            hid = int(float(hid))
            if otp == str(stored_otp):
                exist = foodie.execute("SELECT * FROM users WHERE uid=:uid",
                uid=uid)
                if len(exist) == 1:
                    foodie.execute("UPDATE users SET key=:key WHERE uid=:uid",
                    key=key, uid=uid)
                else:
                    foodie.execute("INSERT INTO users (uid, key, hid) VALUES (:uid, :key, :hid)",
                uid=uid, key=key, hid=hid)
            else:
                hostels = foodie.execute("SELECT * FROM hname")
                foodie.execute("UPDATE verification SET attempts = (attempts+1) WHERE key=:key",
                key=key)
                foodie.conn.close()
                return render_template("login.html", key=key, hostels=hostels, flash="Wrong OTP!")

        foodie.conn.close()
        return render_template("tip.html")

@app.route("/rate", methods=["GET", "POST"])
@login_required
def rate():
    if request.method == "GET":
        foodie.conn.close()
        return redirect("/")

    key  = request.cookies.get('key')
    fid = listitems(key)

    for id in fid:
        react = request.form.get(str(id))
        if not react:
            react = 0
        react = int(float(react))
        response = request.form.get('response' + str(id))
        if not response:
            response = 'none'
        foodie.execute("INSERT INTO ratings (fid, react, response) VALUES (:fid, :react, :response)",
        fid=id, react=react, response=response)

    _, _, tid = time()
    foodie.execute("UPDATE users SET tid=:tid WHERE key=:key",
    tid=tid, key=key)
    foodie.conn.close()
    return redirect("/stats")

@app.route("/stats")
@login_required
def stats():
    key = request.cookies.get('key')
    fid = listitems(key)
    items = {}
    for id in fid:
        rating = foodie.execute("SELECT SUM(react) AS s FROM ratings WHERE fid=:id",
        id=id)[0]["s"]
        count = foodie.execute("SELECT COUNT(react) AS n FROM ratings WHERE (fid=:id AND react != 0)",
        id=id)[0]["n"]
        if not count:
            rating = random.randint(0,10)
        else:
            rating = float(rating)/float(count)
        name = foodie.execute("SELECT fname FROM fname WHERE fid=:id",
        id=id)[0]["fname"]
        items[name] = rating

    items, ranking = scale(items)


    foodie.conn.close()
    return render_template("stats.html", items=items, ranking=ranking)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    return apology("Unauthorized access")
    key = request.cookies.get('key')
    uid = foodie.execute("SELECT uid FROM users WHERE key=:key",
    key=key)[0]["uid"]
    hid = foodie.execute("SELECT hid FROM admin WHERE uid=:uid",
    uid=uid)

    if len(hid) == 0:
        foodie.conn.close()
        return apology("Unauthorized access")


    if request.method == "GET":
        foodie.conn.close()
        return render_template("admin.html")

    option = request.form.get("option")
    command = request.form.get("command")
    if option == "query":
        data = foodie.execute(command)
        foodie.conn.close()
        if len(data) > 0:
            return render_template("view.html", data=data, reversed=reversed)
        else:
            return apology(data)
    elif option == "execute":
        foodie.execute(command)
        foodie.conn.close()
        return render_template("admin.html", hname=hname, hid=hid, flash="Done")

    else:
        foodie.conn.close()
        return render_template("admin.html", flash="Enter the query after choosing the type!")


@app.route("/comments", methods=["GET", "POST"])
@login_required
def comments():
    if request.method == "GET":
        foodie.conn.close()
        return redirect("/stats")

    fname = request.form.get("fname").rstrip()
    fid = foodie.execute("SELECT fid FROM fname WHERE fname=:fname",
    fname=fname)[0]["fid"]
    data = foodie.execute("SELECT DISTINCT ON (response) response FROM ratings WHERE (response != 'none' AND fid=:fid) ORDER BY response, moment DESC LIMIT 50",
    fid=fid)
    if len(data) == 0:
        data = [{ 'response':'The world is so quiet here. After all, if there’s nothing out there, what was that noise?' }]
    foodie.conn.close()
    return render_template("view.html", data=data, comments=1, reversed=reversed)


@app.route("/tip", methods=["GET", "POST"])
def tip():
    return render_template("tip.html")
if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)