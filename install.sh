#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
pip3 install python-magic bottle
apt install python3-mysqldb
echo "Mysql Login : "
read mylogin
mysql -u "$mylogin" -p < setup.sql