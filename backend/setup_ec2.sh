#!/bin/bash
set -e
exec >> /var/log/chernovia-setup.log 2>&1

echo "=== Reinstalando Chernovia Health API $(date) ==="

mkdir -p /opt/chernovia/resultados
cd /opt/chernovia

# Descargar backend usando Python/boto3 (awscli puede estar roto)
python3 -c "
import boto3
s3 = boto3.client('s3')
s3.download_file(
    'chernovia-health-licitacion-213238636264',
    'deploy/backend.zip',
    '/opt/chernovia/backend.zip'
)
print('Descarga OK')
"

unzip -o backend.zip

# Instalar dependencias
pip3 install \
  "fastapi==0.111.0" \
  "uvicorn[standard]==0.29.0" \
  "pandas==2.2.2" \
  "pyarrow==16.0.0" \
  "boto3==1.34.101" \
  -q

# Escribir service file
python3 -c "
content = '''[Unit]
Description=Chernovia Health API
After=network.target

[Service]
User=root
WorkingDirectory=/opt/chernovia
Environment=S3_BUCKET=chernovia-health-licitacion-213238636264
Environment=TMP_DIR=/opt/chernovia/resultados
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''
open('/etc/systemd/system/chernovia.service', 'w').write(content)
print('Service file escrito OK')
"

systemctl daemon-reload
systemctl enable chernovia
systemctl restart chernovia

sleep 5
echo "=== Test API ==="
curl -s http://localhost:8000/health && echo "" || echo "API no responde aun"
echo "=== Setup completado ==="
