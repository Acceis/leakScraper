from itertools import (takewhile, repeat)
from pymongo import MongoClient
import subprocess
import threading
import datetime
import magic
import time
import uuid
import sys
import os
import re

'''
   __            _     _____                            _
  / /  ___  __ _| | __ \_   \_ __ ___  _ __   ___  _ __| |_ ___ _ __
 / /  / _ \/ _` | |/ /  / /\/ '_ ` _ \| '_ \ / _ \| '__| __/ _ \ '__|
/ /__|  __/ (_| |   </\/ /_ | | | | | | |_) | (_) | |  | ||  __/ |
\____/\___|\__,_|_|\_\____/ |_| |_| |_| .__/ \___/|_|   \__\___|_|
                                      |_|

usage : leakImporter.py <leakName> <leak_file>
    leakName :  name of the leak to import (ex : "3kDBLeak")
    leak_file : path to the file containing the data leak
        The file must contain one credential per line
        Each line must follow the following format : email:hash:plain
        Email must be present, hash AND plain can be missing (but one must be present)

        This tool does NOT handle duplicates as it would be much (much) slower.

A correct database to use along with this tool must have the following collections:
credentials:
    p  (test)
    d  (gmail.com)
    P   (p4ssw0rd)
    h    (e731a7b612ab389fcb7f973c452f33df3eb69c99)
    l    (3)
leaks
    name    (tumblr)
    imported(60 550 000)
    filename(tumblr_leak.txt)
    id      (3)

Indexes should be created : db.credentials.createIndex({"d":"hashed"}), db.credentials.createIndex({"l":"hashed"})
'''
# terminal colors
ENDC = '\033[0m'
GREEN = '\033[38;5;118;1m'
YELLOW = '\033[38;5;227;1m'
RED = '\033[38;5;196;1m'
BLUE = '\033[38;5;39;1m'
ORANGE = '\033[38;5;208;1m'
CLEAR = '\033[2K'
############################
# database parameters
mongo_database = "leakScraperTest"
mail_providers = ["gmail.com","msn.com","yahoo.com","mail.ru","comcast.net","hotmail.com","outlook.com","live.com"]

def count_lines(filename, buffsize=1024 * 1024):
    with open(filename, 'rb') as f:
        bufgen = takewhile(lambda x: x, (f.raw.read(buffsize) for _ in repeat(None)))
        return sum(buf.count(b'\n') for buf in bufgen)


def importer(filepath, n, total_lines, nb_parsed, nbThreads, leak_id, not_imported, nb_err, e, mail_providers, nb_mail_providers):
    delimiter = ','
    with open(filepath, "r") as fd:
        line = [fd.readline() for _ in range(nbThreads)][n - 1]
        i = n - 1
        errs = 0
        nb = 0
        filename = "/tmp/tmp_" + str(uuid.uuid4())
        fd2 = open(filename, "w")
        while i < total_lines:
            if line:
                try:
                    s = line.strip().replace('"', '""').split(":")
                    if len(s) >= 3:
                        em = s[0].split("@")
                        prefix = em[0]
                        domain = em[1]
                        if domain.lower() not in mail_providers:
                            plain = "".join(s[2:])
                            hashed = s[1]
                            fd2.write('"' + str(leak_id) + '"' + delimiter + '"' + prefix + '"' + delimiter + '"' + domain + '"' + delimiter + '"' + hashed + '"' + delimiter + '"' + plain + '"'+"\n")
                            nb += 1
                        else:
                            nb_mail_providers["nb_mail_providers"] += 1
                    else:
                        raise Exception("An attribute is missing")
                except Exception as ex:
                    print(line, ":", ex)
                    not_imported[1].acquire()
                    not_imported[0].write(line)
                    not_imported[1].release()
                    errs += 1
            line = [fd.readline() for _ in range(nbThreads)][n - 1]
            i += nbThreads
            nb_parsed[n] = nb
            nb_err[n] = errs
    fd2.close()
    cmd = ["mongoimport","-d",mongo_database,"-c","credentials","--type","csv","--file",filename,"--fields","l,p,d,h,P", "--numInsertionWorkers","8"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()
    e.set()
    os.remove(filename)
    client = MongoClient()
    db = client[mongo_database]
    credentials = db["credentials"]
    leaks = db["leaks"]
    imported = credentials.find({"l":leak_id}).count()
    leaks.update_one({"id":leak_id},{"$set":{"imported":imported}})

def stats(nb_parsed, total_lines, leak_id, nb_err, e, nb_mail_providers):
    '''
    Thread dedicated to printing statistics when processing things.
    '''
    ok = sum(nb_parsed.values())
    errs = sum(nb_err.values())
    parsed = errs + ok + nb_mail_providers["nb_mail_providers"]
    client = MongoClient()
    db = client[mongo_database]
    credentials = db["credentials"]
    initial_number_of_rows = credentials.count()
    t0 = time.time()
    while parsed < total_lines:
        time.sleep(1)
        ok = sum(nb_parsed.values())
        errs = sum(nb_err.values())
        parsed = errs + ok + nb_mail_providers["nb_mail_providers"]
        t1 = time.time()
        remaining = total_lines - (parsed)
        speed = int(parsed / (t1 - t0))
        try:
            eta = datetime.timedelta(seconds=remaining / speed)
        except ZeroDivisionError:
            eta = "--:--:--"

        ratio_total = round((parsed) / total_lines * 100, 2)
        ratio_errs = round(errs / parsed * 100, 2)
        ratio_ok = round(ok / parsed * 100, 2)
        ratio_individuals = round(nb_mail_providers["nb_mail_providers"] / parsed * 100, 2)
        output = CLEAR + "\t" + BLUE + "%s/%s - %s%% - %s/s" + ENDC + ", " + GREEN + "ok : %s - %s%%" + ENDC + ", " + YELLOW + "private individuals : %s - %s%%" + ENDC + ", " + RED + "errors : %s - %s%%" + ENDC + " - %s"
        print(output % ("{:,}".format(parsed), "{:,}".format(total_lines), ratio_total, speed, "{:,}".format(ok), ratio_ok, "{:,}".format(nb_mail_providers["nb_mail_providers"]), ratio_individuals, "{:,}".format(errs), ratio_errs, eta), end="\r")
    print()
    i = 0
    while not e.is_set():
        e.wait(1)
        i += 1
        nb = credentials.count()
        imported = nb - initial_number_of_rows
        remaining = ok - imported
        speed = int(imported / i)
        ratio_imported = round(imported / ok * 100, 2)
        try:
            eta = datetime.timedelta(seconds=remaining / speed)
        except ZeroDivisionError:
            eta = "--:--:--"
        print(CLEAR + GREEN + "\t'mongoimport' Import : " + str(ratio_imported) + "%" + ENDC + " - " + str(speed) + "/s - " + str(eta), end="\r", flush=True)
    print()

def main():
    if len(sys.argv) != 3:
        print("Usage : importer.py leakName <creds.txt>")
        print("Example : importer.py tumblr tumblr.txt")
        exit()

    filename = sys.argv[2]
    leakName = sys.argv[1]
    upload = open(filename, "rb")
    nbThreads = 1
    not_imported_file = open(filename + "_not_imported.txt", "w")
    not_imported_lock = threading.Lock()
    not_imported = (not_imported_file, not_imported_lock)
    print("##################################")
    print("Import requested for file " + filename)
    if upload and leakName != "":
        filetype = magic.from_buffer(upload.read(1024)).lower()
        upload.seek(0)
        validTypes = ["ascii", "utf-8", "text"]
        isreadable = True in [v in filetype for v in validTypes]
        if isreadable:
            print("Counting lines ...")
            total_lines = count_lines(filename)
            client = MongoClient()
            db = client[mongo_database]
            leaks = db["leaks"]
            nbLeaks = leaks.find({"name":leakName}).count()
            if nbLeaks == 0:
                newid = leaks.find()
                try:
                    newid = max([x["id"] for x in newid]) + 1
                except ValueError:
                    newid = 1
                leaks.insert_one({"name":leakName,"filename":os.path.basename(filename), "imported":0, "id":newid})
                leak_id = newid
            else:
                leak_id = leaks.find_one({"name":leakName})["id"]
            nb_parsed = {}
            nb_err = {}
            nb_mail_providers = {}
            e = threading.Event()
            threads = [threading.Thread(target=importer, args=(filename, x, total_lines, nb_parsed, nbThreads, leak_id, not_imported, nb_err, e, mail_providers, nb_mail_providers)) for x in range(1, nbThreads + 1)]
            statsT = threading.Thread(target=stats, args=(nb_parsed, total_lines, leak_id, nb_err, e, nb_mail_providers))
            print("Processing started ...")
            t0 = time.time()
            for t in threads:
                nb_parsed[t._args[1]] = 0
                nb_err[t._args[1]] = 0
                nb_mail_providers["nb_mail_providers"] = 0
                t.start()
            statsT.start()
            for t in threads:
                t.join()
            t1 = time.time()
            statsT.join()
            print()
            print("Import finished in", round(t1 - t0, 4), "secs")
    not_imported[0].close()


if __name__ == "__main__":
    main()

