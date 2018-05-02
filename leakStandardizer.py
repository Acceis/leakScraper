import threading
import shutil
import string
import time
import sys
import os
import re

'''__            _     __ _                  _               _ _
  / /  ___  __ _| | __/ _\ |_ __ _ _ __   __| | __ _ _ __ __| (_)_______ _ __
 / /  / _ \/ _` | |/ /\ \| __/ _` | '_ \ / _` |/ _` | '__/ _` | |_  / _ \ '__|
/ /__|  __/ (_| |   < _\ \ || (_| | | | | (_| | (_| | | | (_| | |/ /  __/ |
\____/\___|\__,_|_|\_\\__/\__\__,_|_| |_|\__,_|\__,_|_|  \__,_|_/___\___|_|



'''

# terminal colors
ENDC = '\033[0m'
GREEN = '\033[32;1m'
YELLOW = '\033[33;1m'
RED = '\033[31;1m'
BLUE = '\033[34;1m'
CLEAR_LINE = "\033[K"


def parse_line(regex, i, readlock, stdoutlock, stderrlock, stdoutfd, stderrfd, buffsize):
    global stats
    global inputfd
    while True:
        lines = []
        stdout = []
        stderr = []
        with readlock:
            for _ in range(buffsize):
                line = inputfd.readline()
                if len(line) > 0:
                    lines.append(line[:-1] if line[-1] == "\n" else line)
        for line in lines:
            try:
                tmp_line = line.decode("utf-8")
                if "@" in tmp_line:
                    res = regex.match(tmp_line)
                    if res:
                        stats[i]["matching"] += 1
                        email = res.group("email")
                        try:
                            hashed = res.group("hash")
                        except IndexError:
                            hashed = ""
                        try:
                            plain = res.group("plain")
                        except IndexError:
                            plain = ""
                        splitEmail = email.split("@")
                        if len(splitEmail) == 2 and len(splitEmail[1].split(".")) > 1:
                            email = email.lower()
                            hashed = hashed.lower()
                            if hashed == plain == "":
                                stderr.append(line)
                                stats[i]["no_creds"] += 1
                            else:
                                stdout.append("%s:%s:%s\n" % (email, hashed, plain))
                                stats[i]["nb_creds"] += 1
                        else:
                            stderr.append(line)
                            stats[i]["invalid_mail"] += 1
                    else:
                        stderr.append(line)
                        stats[i]["not_matching"] += 1
                else:
                    stderr.append(line)
                    stats[i]["no_mail"] += 1
            except UnicodeDecodeError:
                stderr.append(line)
                stats[i]["not_utf8"] += 1
            finally:
                stats[i]["parsed_lines"] += 1
        with stdoutlock:
            for l in stdout:
                stdoutfd.write(l)
        with stderrlock:
            for l in stderr:
                stderrfd.write(l)
        del stdout
        del stderr
        if len(lines) < buffsize:
            break
        del lines


def display_stats(nb_parsers):
    global stats
    parsed_lines = 0
    nb_lines = 1
    time.sleep(0.3)
    while parsed_lines < nb_lines:
        parsed_lines = sum(stats[i]["parsed_lines"] for i in range(nb_parsers))
        nb_lines = stats[0]["nb_lines"]
        not_utf8 = sum(stats[i]["not_utf8"] for i in range(nb_parsers))
        no_mail = sum(stats[i]["no_mail"] for i in range(nb_parsers))
        no_creds = sum(stats[i]["no_creds"] for i in range(nb_parsers))
        not_matching = sum(stats[i]["not_matching"] for i in range(nb_parsers))
        matching = sum(stats[i]["matching"] for i in range(nb_parsers))
        invalid_mail = sum(stats[i]["invalid_mail"] for i in range(nb_parsers))
        nb_creds = sum(stats[i]["nb_creds"] for i in range(nb_parsers))
        percent_parsed = round(parsed_lines * 100 / nb_lines, 2)
        try:
            percent_matching = round(matching * 100 / parsed_lines, 2)
            percent_creds = round(nb_creds * 100 / parsed_lines, 2)
            percent_nomail = round((no_mail + invalid_mail) * 100 / parsed_lines, 2)
            percent_notutf8 = round(not_utf8 * 100 / parsed_lines, 2)
        except ZeroDivisionError:
            percent_matching = 0.00
            percent_creds = 0.00
            percent_nomail = 0.00
            percent_notutf8 = 0.00

        print("%s\tparsed : %s " % (CLEAR_LINE, parsed_lines), end="")
        print("(%s%s%%%s)" % (BLUE, percent_parsed, ENDC), end="")
        print(" - matching : %s " % matching, end="")
        print("(%s%s%%%s)" % (GREEN, percent_matching, ENDC), end="")
        print(" - creds : %s (%s%s" % (nb_creds, GREEN, percent_creds), end="")
        print("%%%s)" % ENDC, end="")
        print(" - no/invalid mails : %s " % (invalid_mail + no_mail,), end="")
        print("(%s%s%%%s)" % (RED, percent_nomail, ENDC), end="")
        print(" - not utf8 : %s (%s%s%%%s)" % (not_utf8, RED, percent_notutf8, ENDC), end="\r")
        time.sleep(0.5)
    print()


def validate_regex(_string):
    try:
        regex = re.compile(_string)
        named_groups = list(regex.groupindex)
        if "email" in named_groups and ("hash" in named_groups or "plain" in named_groups):
            return regex
        else:
            return False
    except re.error:
        return False
    return False


def count_lines(filename):
    size = os.path.getsize(filename)
    current_size = 0
    ratio = 0.0
    nb_lines = 0
    with open(filename, "rb") as file_descriptor:
        print(YELLOW + "Counting lines" + ENDC)
        while True:
            block = file_descriptor.read(4096)
            if not block:
                break
            nb_lines += block.count(b"\n")
            current_size += len(block)
            print("\t%s lines - %s%%" % (nb_lines, round(current_size / size * 100, 2)), end="\r")
        print()
    return nb_lines


def main():
    posix_email_regex = r'(?P<email>(?:[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'\.*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")\.?@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-zA-Z0-9-]*[a-zA-Z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\]))'
    fast_email_regex = r'(?P<email>[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
    sha1_regex = '(?P<hash>[0-9a-fA-F]{40})'
    md5_regex = '(?P<hash>[0-9a-fA-F]{32})'
    print(GREEN + r'''
   __            _      __ _                  _               _ _
  / /  ___  __ _| | __ / _\ |_ __ _ _ __   __| | __ _ _ __ __| (_)_______ _ __
 / /  / _ \/ _` | |/ / \ \| __/ _` | '_ \ / _` |/ _` | '__/ _` | |_  / _ \ '__|
/ /__|  __/ (_| |   <  _\ \ || (_| | | | | (_| | (_| | | | (_| | |/ /  __/ |
\____/\___|\__,_|_|\_\ \__/\__\__,_|_| |_|\__,_|\__,_|_|  \__,_|_/___\___|_|
        ''' + ENDC)
    if len(sys.argv) < 4 or len(sys.argv) > 6:
        print("use : leakStandardizer <inputLeakFile> <outputFile>", end="")
        print(" <errorFile> [nbThreads=1] [buffsize=4096]")
        exit()
    input_file = sys.argv[1]
    output_result = sys.argv[2]
    errfile = sys.argv[3]

    if len(sys.argv) > 4:
        nb_threads = int(sys.argv[4])
    else:
        nb_threads = 1

    if len(sys.argv) > 5:
        buffsize = int(sys.argv[5])
    else:
        buffsize = 4096

    print("Perf. tunning : %s threads / %s buffered lines" % (nb_threads, buffsize))

    print("File containing junk : %s%s%s" % (YELLOW, input_file, ENDC))
    print("Output will be sent to : %s%s%s" % (YELLOW, output_result, ENDC))
    print("Invalid lines will be sent to : %s%s%s" % (YELLOW, errfile, ENDC))
    reg = False
    while not reg:
        print("Regex for " + input_file + " : \n\t", end="")
        print("Mandatory capturing groups : (?P<email>) and ( (?P<hash>) or (?P<plain>) )\n\t", end="")
        print("(Shortcuts : '$fast_email$','$sha1$','$md5$', '$posix_email$')\n\t", end="")
        print("$posix_email$ is RFC 5322 compliant (slow but accurate), $fast_email$ is 99.99\% accurate but 10x faster.")
        reg = input("> ")
        reg = reg.replace('$posix_email$', posix_email_regex)
        reg = reg.replace('$fast_email$', fast_email_regex)
        reg = reg.replace('$sha1$', sha1_regex)
        reg = reg.replace('$md5$', md5_regex)
        reg = validate_regex(reg)
        if not reg:
            print("\tThis regex does not meet some random criteria, try again")

    print()
    print(shutil.get_terminal_size().columns * "=")
    print()
    nb_lines = count_lines(input_file)
    readlock = threading.Lock()
    stdoutlock = threading.Lock()
    stderrlock = threading.Lock()

    global stats
    stats = []
    global inputfd
    inputfd = open(input_file, "rb")
    stdoutfd = open(output_result, "a")
    stderrfd = open(errfile, "ab")
    threads = []
    for i in range(nb_threads):
        args = (reg, i, readlock, stdoutlock, stderrlock, stdoutfd, stderrfd, buffsize)
        worker = threading.Thread(target=parse_line, args=args)
        stats.append({"parsed_lines": 0, "nb_lines": nb_lines, "not_utf8": 0,
                      "no_mail": 0, "no_creds": 0, "not_matching": 0, "matching": 0,
                      "invalid_mail": 0, "nb_creds": 0})
        threads.append(worker)

    print(YELLOW + "Parsing file" + ENDC)
    display_stats_job = threading.Thread(target=display_stats, args=(nb_threads,))
    display_stats_job.start()
    t0 = time.time()
    for t in threads:
        t.start()

    for t in threads:
        t.join()
    inputfd.close()
    stdoutfd.close()
    stderrfd.close()
    t1 = time.time()
    display_stats_job.join()

    print("File parsed in %s secs" % (round(t1 - t0, 3)) + " secs")
    print("Finished, bye.")


if __name__ == "__main__":
    main()
