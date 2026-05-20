#!/usr/bin/env python3
"""Script de deploy ejecutado en EC2 via SSM. Descarga archivos desde S3 y reinicia el servicio."""
import os
import subprocess
import sys

import boto3

BUCKET = "chernovia-health-licitacion-213238636264"
REGION = "us-east-1"
APP = "/opt/chernovia"
DEPLOY_PREFIX = "deploy"

s3 = boto3.client("s3", region_name=REGION)


def download(key, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    s3.download_file(BUCKET, key, dest)
    print(f"  ok: {os.path.basename(dest)}")


def sync_static():
    static_dir = f"{APP}/static"
    os.makedirs(f"{static_dir}/assets", exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{DEPLOY_PREFIX}/static/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local = key.replace(f"{DEPLOY_PREFIX}/static/", f"{static_dir}/", 1)
            os.makedirs(os.path.dirname(local), exist_ok=True)
            s3.download_file(BUCKET, key, local)
            print(f"  ok: {os.path.basename(local)}")
    print("  static sync done")


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f"STDERR: {result.stderr.strip()}", file=sys.stderr)
    return result.returncode


print("=== [1] Descargando backend ===")
backend_files = [
    "main.py", "clasificador.py", "clasificador_ml.py",
    "detector_anomalias.py", "generador_reporte.py", "requirements.txt",
]
for f in backend_files:
    download(f"{DEPLOY_PREFIX}/{f}", f"{APP}/{f}")

print("\n=== [2] Sincronizando frontend ===")
sync_static()

print("\n=== [3] Instalando dependencias ===")
rc = run(f"cd {APP} && /usr/bin/python3 -m pip install -q reportlab==4.1.0")
print("  ok: reportlab" if rc == 0 else "  WARN: pip reportlab")

print("\n=== [4] Reiniciando servicio ===")
run("systemctl daemon-reload")
run("systemctl restart chernovia")
run("sleep 4")
rc = run("systemctl is-active chernovia")
if rc != 0:
    print("ERROR: servicio no arrancó", file=sys.stderr)
    run("journalctl -u chernovia -n 30 --no-pager")
    sys.exit(1)

print("\n=== [5] Health check ===")
import urllib.request, json
try:
    with urllib.request.urlopen("http://localhost:8000/health", timeout=10) as r:
        data = json.loads(r.read())
        print(f"  status: {data['status']}")
        print(f"  ml_model: {data['ml_model']}")
        print(f"  version: {data['version']}")
except Exception as e:
    print(f"  WARN health check: {e}")

print("\n=== Deploy completado ===")
