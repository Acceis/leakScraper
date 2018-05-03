from bottle import *
import settings
import datetime
import MySQLdb
import hashlib
import urllib
import magic
import math
import time
import os
import re


@route('/', method='GET')
@view('views/index_mysql')
def index():
    db = MySQLdb.connect(host=settings.mysql_host, passwd=settings.mysql_password,
                         user=settings.mysql_login, db=settings.mysql_database)
    c = db.cursor()
    display_more = False
    display_less = False
    default_step = 500
    max_pages = 20
    if request.query.search:
        query = request.query.search
        page = request.query.page if request.query.page else 1
        step = request.query.step if request.query.step else default_step
        numPage = request.query.numPage if request.query.numPage else 1

        try:
            page = int(page)
        except ValueError:
            page = 1
        try:
            step = int(step)
        except ValueError:
            step = default_step
        try:
            numPage = int(numPage)
        except ValueError:
            numPage = 1
        start = max(0, (page - 1) * step)
        end = start + step
        ta = time.time()
        c.execute("SELECT prefix,domain,hash,plain FROM credentials WHERE domain = %s LIMIT %s,%s", (query, start, step))
        tb = time.time()
        creds = [list(x) for x in c.fetchall()]
        tc = time.time()
        nbRes = c.execute("SELECT COUNT(1) FROM (SELECT 1 FROM credentials WHERE domain = %s LIMIT %s,%s) AS a",
                          (query, ((int(numPage) - 1) * max_pages * step), max_pages * step))
        td = time.time()
        nbRes = c.fetchone()
        nbRes = nbRes[0]
        nbPages = int(math.ceil(nbRes / step))
        page = max(1,min(((numPage - 1) * max_pages) + nbPages, page))
        if request.query.page and int(request.query.page) > page:
            redirect("/?search=" + query + "&page=" + str(page) + "&numPage=" + str(numPage))
        if nbRes == max_pages * step:
            display_more = True
        if numPage > 1:
            display_less = True
        first_page = ((numPage - 1) * max_pages) + 1
    else:
        creds = None
        query = ""
        nbRes = 0
        page = 0
        nbPages = 0
        step = default_step
        numPage = 0
        first_page = 1
    count = c.execute("SELECT SUM(imported) FROM leaks")
    count = c.fetchone()
    count = count[0] if count[0] else 0
    count = '{:,}'.format(count).replace(',', ' ')
    c.close()
    return dict(creds=creds, count=count, query=query, nbRes=nbRes, page=page, nbPages=nbPages, step=step,
                first_page=first_page, display_more=display_more, display_less=display_less,
                numPage=numPage, max_pages=max_pages)


@route('/leaks', method="GET")
@view('views/leaks_mysql')
def getLeaks():
    db = MySQLdb.connect(host=settings.mysql_host, passwd=settings.mysql_password,
                         user=settings.mysql_login, db=settings.mysql_database)
    c = db.cursor()
    count = c.execute("SELECT SUM(imported) FROM leaks")
    count = c.fetchone()
    count = count[0] if count[0] else 0
    count = '{:,}'.format(count).replace(',', ' ')
    c.execute("SELECT id,imported,filename,name FROM leaks")
    leaksa = [list(x) for x in c.fetchall()]
    nbLeaks = c.execute("SELECT COUNT(1) FROM leaks")
    nbLeaks = c.fetchone()
    nbLeaks = nbLeaks[0]
    leaksb = []
    for leak in leaksa:
        tmpleak = leak
        tmpleak[1] = '{:,}'.format(int(tmpleak[1])).replace(',', ' ')
        leaksb.append(leak)
    c.close()
    return dict(count=count, nbLeaks=nbLeaks, leaks=leaksb)


@route('/export', method='GET')
def export():
    if request.query.search:
        db = MySQLdb.connect(host=settings.mysql_host, passwd=settings.mysql_password,
                         user=settings.mysql_login, db=settings.mysql_database)
        c = db.cursor()
        what = request.query.what
        if what not in ["all", "left", "cracked"]:
            what = "all"
        query = request.query.search
        response.content_type = 'application/force-download; UTF-8'
        response.set_header("content-Disposition", "inline;filename=creds-" + query + ".txt")

        if what == "all":
            c.execute("SELECT prefix,domain,hash,plain FROM credentials WHERE domain=%s", (query,))
        elif what == "left":
            c.execute("SELECT prefix,domain,hash FROM credentials WHERE domain=%s AND plain=''", (query,))
        elif what == "cracked":
            c.execute("SELECT prefix,domain,hash,plain FROM credentials WHERE domain=%s AND plain != ''", (query,))

        res = "\n".join([x[0] + "@" + x[1] + ":" + ":".join(x[2:]) for x in c.fetchall()])
        c.close()

    else:
        redirect("/")

    return res


@route('/removeLeak', method="GET")
def removeLeak():
    if request.query.id:
        db = MySQLdb.connect(host=settings.mysql_host, passwd=settings.mysql_password,
                         user=settings.mysql_login, db=settings.mysql_database)
        c = db.cursor()
        print("\tRemoving credentials for leak " + str(request.query.id) + " ...")
        c.execute("DELETE FROM leaks WHERE id=%s", (request.query.id,))
        c.execute("ANALYZE TABLE credentials")
        db.commit()
        c.close()
        print("\tdone.")
    redirect("/leaks")


# ###### STATIC RESOURCES
@get("/static/css/<filepath:re:.*\.css>")
def css(filepath):
    return static_file(filepath, root="./views/css")


@get("/static/js/<filepath:re:.*\.js>")
def js(filepath):
    return static_file(filepath, root="./views/js")


run(host="127.0.0.1", port=8080, debug=False, reloader=False)
