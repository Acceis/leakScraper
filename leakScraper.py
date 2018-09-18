from pymongo import MongoClient
from bottle import *
import math

mongo_database = "leakScraper"


@route('/', method='GET')
@view('views/index')
def index():
    client = MongoClient()
    db = client[mongo_database]
    credentials = db["credentials"]
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
        # end = start + step
        creds = [document for document in credentials.find({"d": query}).skip(start).limit(step)]
        nbRes = credentials.find({"d": query}).skip(((int(numPage) - 1) * max_pages * step)).limit(max_pages * step).count(with_limit_and_skip=True)
        nbPages = int(math.ceil(nbRes / step))
        page = max(1, min(((numPage - 1) * max_pages) + nbPages, page))
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
    count = credentials.count()
    count = '{:,}'.format(count).replace(',', ' ')
    return dict(creds=creds, count=count, query=query, nbRes=nbRes, page=page, nbPages=nbPages, step=step,
                first_page=first_page, display_more=display_more, display_less=display_less,
                numPage=numPage, max_pages=max_pages)


@route('/leaks', method="GET")
@view('views/leaks')
def getLeaks():
    client = MongoClient()
    db = client[mongo_database]
    credentials = db["credentials"]
    leaks = db["leaks"]
    count = credentials.count()
    count = '{:,}'.format(count).replace(',', ' ')
    nbLeaks = leaks.count()
    leaksa = []
    if nbLeaks > 0:
        leaksa = [{"id": leak["id"], "imported": '{:,}'.format(int(leak["imported"])).replace(',', ' '), "name": leak["name"], "filename": leak["filename"]} for leak in leaks.find()]
    return dict(count=count, nbLeaks=nbLeaks, leaks=leaksa)


@route('/export', method='GET')
def export():
    if request.query.search:
        client = MongoClient()
        db = client[mongo_database]
        credentials = db["credentials"]
        what = request.query.what
        if what not in ["all", "left", "cracked"]:
            what = "all"
        query = request.query.search
        response.content_type = 'application/force-download; UTF-8'
        response.set_header("content-Disposition", "inline;filename=creds-" + query + ".txt")

        if what == "all":
            r = credentials.find({"d": query})
        elif what == "left":
            r = credentials.find({"d": query, "P": {"$eq": ""}})
        elif what == "cracked":
            r = credentials.find({"d": query, "P": {"$ne": ""}})

        if len(r) > 0:
            res = "\n".join([str(x["p"]) + "@" + str(x["d"]) + ":" + str(x["h"]) + ":" + str(x["P"]) for x in r])
        else:
            res = ""

    else:
        redirect("/")

    return res


@route('/removeLeak', method="GET")
def removeLeak():
    if request.query.id:
        client = MongoClient()
        db = client[mongo_database]
        credentials = db["credentials"]
        leaks = db["leaks"]
        print("\tRemoving credentials for leak " + str(request.query.id) + " ...")
        credentials.delete_many({"l": int(request.query.id)})
        leaks.delete_one({"id": int(request.query.id)})
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
