#!/bin/bash
set -e
/usr/bin/python3 -c "
import boto3
s3 = boto3.client('s3', region_name='us-east-1')
s3.download_file('chernovia-health-licitacion-213238636264', 'deploy/main.py', '/opt/chernovia/main.py')
print('main.py downloaded OK')
"
sed -i 's/--workers 2/--workers 1/g' /etc/systemd/system/chernovia.service
grep ExecStart /etc/systemd/system/chernovia.service
systemctl daemon-reload
systemctl restart chernovia
sleep 6
systemctl is-active chernovia
curl -s http://localhost:8000/health
