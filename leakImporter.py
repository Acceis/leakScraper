from itertools import (takewhile, repeat)
import threading
import settings
import datetime
import MySQLdb
import magic
import time
import uuid
import sys
import os

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

A correct database to use along with this tool must have the following tables :
CREATE DATABASE leakScraper;
USE leakScraper;
CREATE TABLE leaks (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name varchar(255) NOT NULL,
    imported BIGINT,
    filename varchar(255) NOT NULL);

CREATE TABLE credentials (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    prefix VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    hash VARCHAR(512) NOT NULL,
    plain VARCHAR(512) NOT NULL,
    leak INT NOT NULL,
    FOREIGN KEY (leak) REFERENCES leaks(id) ON DELETE CASCADE) ENGINE=INNODB;

    CREATE INDEX leak_index ON credentials (leak) USING HASH;
    CREATE INDEX domain_index ON credentials (domain) USING HASH;
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
mysql_login = settings.mysql_login
mysql_password = settings.mysql_password
mysql_database = settings.mysql_database
mysql_host = settings.mysql_host


def count_lines(filename, buffsize=1024 * 1024):
    with open(filename, 'rb') as f:
        bufgen = takewhile(lambda x: x, (f.raw.read(buffsize) for _ in repeat(None)))
        return sum(buf.count(b'\n') for buf in bufgen)


def importer(filepath, n, total_lines, nb_parsed, nbThreads, leak_id, not_imported, nb_err, e):
    delimiter = ';'
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
                    s = line.strip().split(":")
                    em = s[0].split("@")
                    prefix = em[0].replace(";", "\\;")
                    domain = em[1].replace(";", "\\;")
                    plain = "".join(s[2:]).replace(";", "\\;")
                    hashed = s[1].replace(";", "\\;")
                    fd2.write(str(leak_id) + delimiter + prefix + delimiter + domain + delimiter + hashed + delimiter + plain + "\n")
                    nb += 1
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
    db = MySQLdb.connect(host=mysql_host, passwd=mysql_password, user=mysql_login, db=mysql_database)
    c = db.cursor()
    c.execute("LOAD DATA LOCAL INFILE %s INTO TABLE credentials FIELDS TERMINATED BY '" + delimiter + "' LINES TERMINATED BY '\n' (leak,prefix,domain,hash,plain);", (filename,))
    db.commit()
    e.set()
    c.close()
    c = db.cursor()
    c.execute("SELECT COUNT(1) FROM credentials WHERE leak = %s", (leak_id,))
    n = c.fetchone()
    n = n[0]
    c.execute("UPDATE leaks SET imported = %s WHERE id=%s", (sum(nb_parsed.values()), leak_id))
    db.commit()
    c.close()
    db.close()
    os.remove(filename)


def stats(nb_parsed, total_lines, leak_id, nb_err, e):
    '''
    Thread dedicated to printing statistics when processing things.
    '''
    t0 = time.time()
    ok = sum(nb_parsed.values())
    errs = sum(nb_err.values())
    parsed = errs + ok

    db = MySQLdb.connect(host=mysql_host, passwd=mysql_password, user=mysql_login, db=mysql_database)
    c = db.cursor()
    c.execute("""SELECT imported FROM leaks WHERE id = %s""", (leak_id,))
    start = c.fetchone()[0]
    c.execute("""ANALYZE TABLE credentials""")
    initial_number_of_rows = c.execute("""SELECT TABLE_ROWS FROM information_schema.tables WHERE table_name = 'credentials'""")
    initial_number_of_rows = c.fetchone()[0]
    c.close()
    c = db.cursor()
    while parsed < total_lines:
        time.sleep(1)
        ok = sum(nb_parsed.values())
        errs = sum(nb_err.values())
        parsed = errs + ok
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
        output = CLEAR + "\t" + BLUE + "%s/%s - %s%% - %s/s" + ENDC + ", " + GREEN + "ok : %s - %s%%" + ENDC + ", " + RED + "errors : %s - %s%%" + ENDC + " - %s"
        print(output % ("{:,}".format(parsed), "{:,}".format(total_lines), ratio_total, speed, "{:,}".format(ok), ratio_ok, "{:,}".format(errs), ratio_errs, eta), end="\r")
        c.close()
    print()
    c = db.cursor()
    i = 0
    while not e.is_set():
        i += 1
        c.execute("""SELECT TABLE_ROWS FROM information_schema.tables WHERE table_name = 'credentials'""")
        nb = c.fetchone()[0]
        imported = nb - initial_number_of_rows
        remaining = ok - imported
        speed = int(imported / i)
        ratio_imported = round(imported / ok * 100, 2)
        try:
            eta = datetime.timedelta(seconds=remaining / speed)
        except ZeroDivisionError:
            eta = "--:--:--"
        print(CLEAR + GREEN + "\tMySQL 'LOA DATA' Import : " + str(ratio_imported) + "%" + ENDC + " - " + str(speed) + "/s (approximation) - " + str(eta), end="\r")
        e.wait(1)
    print()
    c.close()


def main():
    if mysql_login == "changeme" and mysql_password == "changeme":
        print("Please, configure me by setting a mysql username and password !")
        print("Change variables 'mysql_login' and 'mysql_password' on top of this current file.")
        exit()
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
            db = MySQLdb.connect(host=mysql_host, passwd=mysql_password, user=mysql_login, db=mysql_database)
            c = db.cursor()
            c.execute("""SELECT * FROM leaks WHERE name = %s""", (leakName,))
            if c.rowcount == 0:
                added = str(datetime.datetime.now()).split(".")[0]
                c.execute("""INSERT INTO leaks (name,filename,imported) VALUES (%s,%s,%s)""", (leakName, os.path.basename(filename), 0))
                db.commit()
                c.execute("""SELECT id FROM leaks WHERE name = %s""", (leakName,))
                leak_id = c.fetchone()[0]
            else:
                leak_id = c.fetchone()[0]
            c.close()
            nb_parsed = {}
            nb_err = {}
            e = threading.Event()
            threads = [threading.Thread(target=importer, args=(filename, x, total_lines, nb_parsed, nbThreads, leak_id, not_imported, nb_err, e)) for x in range(1, nbThreads + 1)]
            statsT = threading.Thread(target=stats, args=(nb_parsed, total_lines, leak_id, nb_err, e))
            print("Processing started ...")
            t0 = time.time()
            for t in threads:
                nb_parsed[t._args[1]] = 0
                nb_err[t._args[1]] = 0
                t.start()
            statsT.start()
            for t in threads:
                t.join()
            t1 = time.time()
            statsT.join()
            print()
            print("Import finished in", round(t1 - t0, 4), "secs")
    not_imported[0].close()
    db.commit()


if __name__ == "__main__":
    main()

