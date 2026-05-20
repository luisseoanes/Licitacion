#!/usr/bin/env bash
# deploy_v2.sh — DataHealth Cloud Solutions
# Sube backend + frontend a S3 y recarga la instancia EC2 vía SSM.
# USO: bash deploy_v2.sh

set -euo pipefail

BUCKET="chernovia-health-licitacion-213238636264"
REGION="us-east-1"
DEPLOY_PREFIX="deploy"

echo "=== [1/4] Subiendo archivos de backend a S3 ==="
BACKEND_FILES=(
  "main.py"
  "clasificador.py"
  "clasificador_ml.py"
  "detector_anomalias.py"
  "generador_reporte.py"
  "requirements.txt"
)
for f in "${BACKEND_FILES[@]}"; do
  aws s3 cp "backend/$f" "s3://$BUCKET/$DEPLOY_PREFIX/$f" --region "$REGION"
  echo "  ✓ $f"
done

echo ""
echo "=== [2/4] Subiendo frontend compilado a S3 ==="
aws s3 sync frontend/dist "s3://$BUCKET/$DEPLOY_PREFIX/static/" \
  --region "$REGION" \
  --delete \
  --cache-control "no-cache"
echo "  ✓ dist/ sincronizado"

echo ""
echo "=== [3/4] Buscando instancia EC2 ==="
INSTANCE_ID=$(aws ec2 describe-instances \
  --region "$REGION" \
  --filters "Name=ip-address,Values=184.72.124.136" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)

if [ "$INSTANCE_ID" = "None" ] || [ -z "$INSTANCE_ID" ]; then
  echo "ERROR: No se encontró la instancia en 184.72.124.136"
  exit 1
fi
echo "  ✓ Instance ID: $INSTANCE_ID"

echo ""
echo "=== [4/4] Ejecutando deploy en EC2 vía SSM ==="
CMD=$(cat <<'SSMEOF'
set -e
BUCKET="chernovia-health-licitacion-213238636264"
REGION="us-east-1"
APP_DIR="/opt/chernovia"

echo "--- Descargando backend ---"
for f in main.py clasificador.py clasificador_ml.py detector_anomalias.py generador_reporte.py requirements.txt; do
  aws s3 cp "s3://$BUCKET/deploy/$f" "$APP_DIR/$f" --region "$REGION"
  echo "  ✓ $f"
done

echo "--- Descargando frontend ---"
aws s3 sync "s3://$BUCKET/deploy/static/" "$APP_DIR/static/" --region "$REGION" --delete
echo "  ✓ static/ sincronizado"

echo "--- Instalando dependencias ---"
cd "$APP_DIR"
/usr/bin/python3 -m pip install -q -r requirements.txt
echo "  ✓ pip install OK"

echo "--- Reiniciando servicio ---"
systemctl daemon-reload
systemctl restart chernovia
sleep 5
systemctl is-active chernovia && echo "  ✓ chernovia activo"

echo "--- Health check ---"
curl -sf http://localhost:8000/health && echo ""
echo "=== Deploy completado ==="
SSMEOF
)

COMMAND_ID=$(aws ssm send-command \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[\"$CMD\"]" \
  --comment "deploy_v2 DataHealth" \
  --query "Command.CommandId" \
  --output text)

echo "  SSM Command ID: $COMMAND_ID"
echo "  Esperando resultado..."

for i in $(seq 1 24); do
  sleep 5
  STATUS=$(aws ssm get-command-invocation \
    --region "$REGION" \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query "Status" \
    --output text 2>/dev/null || echo "Pending")
  echo "  [$((i*5))s] $STATUS"
  if [ "$STATUS" = "Success" ]; then
    echo ""
    echo "✅ Deploy exitoso."
    aws ssm get-command-invocation \
      --region "$REGION" \
      --command-id "$COMMAND_ID" \
      --instance-id "$INSTANCE_ID" \
      --query "StandardOutputContent" \
      --output text
    break
  elif [ "$STATUS" = "Failed" ] || [ "$STATUS" = "TimedOut" ]; then
    echo "❌ Deploy falló ($STATUS):"
    aws ssm get-command-invocation \
      --region "$REGION" \
      --command-id "$COMMAND_ID" \
      --instance-id "$INSTANCE_ID" \
      --query "StandardErrorContent" \
      --output text
    exit 1
  fi
done

echo ""
echo "🌐 Sistema disponible en: http://184.72.124.136:8000"
