#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
apt install python3-mysqldb python3-pip
pip3 install python-magic bottle
echo "Mysql Login : "
read mylogin
mysql -u "$mylogin" -p < setup.sql
