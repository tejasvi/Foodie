import os
import requests
import urllib.parse

from flask import redirect, render_template, request
from functools import wraps
from datetime import datetime, date
from pytz import timezone
import smtplib
from cs50 import SQL
import sqlalchemy
from sqlalchemy.pool import NullPool


# start
# added the below as part of Heroku post on Medium
class SQL(object):
    def __init__(self, url):
        try:
            self.engine = sqlalchemy.create_engine(url, poolclass=NullPool)
        except Exception as e:
            raise RuntimeError(e)
    def execute(self, text, *multiparams, **params):
        try:
            self.conn = self.engine.connect(close_with_result=True)
            statement = sqlalchemy.text(text).bindparams(*multiparams, **params)
            result = self.conn.execute(str(statement.compile(compile_kwargs={"literal_binds": True})))
            # SELECT
            if result.returns_rows:
                rows = result.fetchall()
                return [dict(row) for row in rows]
            # INSERT
            elif result.lastrowid is not None:
                return result.lastrowid
            # DELETE, UPDATE
            else:
                return result.rowcount
        except sqlalchemy.exc.IntegrityError:
            return None
        except Exception as e:
            raise RuntimeError(e)
# end


def apology(message, code=400):
    """Render message as an apology to user."""
    message = str(message)
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.cookies.get('key')
        if key is None:
            return redirect("/login")
        foodie = SQL(os.environ['DATABASE_URL'])
        exists = foodie.execute("SELECT COUNT(*) AS c FROM users WHERE key=:key",
        key=key)[0]["c"]
        foodie.conn.close()
        if not exists:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def time():
    week = date.today().weekday() # monday is 0
    phase = 1

    time = datetime.now(timezone('Asia/Kolkata'))
    bfast = time.replace(hour=7, minute=0, second=0, microsecond=0)
    lunch = time.replace(hour=12, minute=0, second=0, microsecond=0)
    dinner = time.replace(hour=20, minute=0, second=0, microsecond=0)

    if time < lunch:
        phase = 0
    elif time > dinner:
        phase = 2

    tid = int(float("".join(str(x) for x in [time.day, time.month, time.year, phase])))

    return week, phase, tid

def sendotp(email, otp):
    fromaddr = @@@@
    toaddrs  = email
    username = fromaddr
    password = ****
    server = smtplib.SMTP('smtp.office365.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, f"Subject: Foodie Login\n\nYour OTP is {otp}")
    server.quit()

def listitems(key):
    """return fid list"""

    week, phase, _ = time()
    foodie = SQL(os.environ['DATABASE_URL'])
    hid = foodie.execute("SELECT hid FROM users WHERE key=:key",
    key=key)[0]["hid"]
    fid = [x["fid"] for x in foodie.execute("SELECT fid FROM mess WHERE (hid=:hid AND (phase=:phase AND week=:week))",
    hid=hid, phase=phase, week=week)]

    foodie.conn.close()
    return fid

def scale(items):
    ranking = [x[0] for x in sorted(items.items(), key=lambda kv: kv[1])]
    lowest = items[ranking[0]]
    if lowest < 0:
        for i in items.keys():
            items[i]  -= lowest
    if items[ranking[-1]] != 0:
        factor = 10/float(items[ranking[-1]])
        for key in items.keys():
            items[key] *= factor
            items[key] = round(items[key])
    return items, ranking
