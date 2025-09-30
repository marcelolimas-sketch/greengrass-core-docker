#!/bin/bash
set -e

# -------------------------------
# Variáveis padrão
# -------------------------------
export AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
export THING_NAME=${THING_NAME:-<YOUR_THING_NAME>}
GGC_DIR=/greengrass/v2
COMPONENTS_DIR=$GGC_DIR/components
THING_CERTS=$GGC_DIR/thing-certs

# -------------------------------
# Provisionamento se necessário
# -------------------------------
if [ ! -d "$THING_CERTS/$THING_NAME-connectionKit" ]; then
    echo "[INFO] Provisionando Core Device..."
    java -Droot="$GGC_DIR" -Dlog.store=FILE \
        -jar $GGC_DIR/lib/Greengrass.jar \
        --provision true \
        --thing-name "$THING_NAME" \
        --aws-region "$AWS_REGION" \
        --component-default-user ggc_user:ggc_group \
        --setup-system-service false
else
    echo "[INFO] Core Device já provisionado."
fi

# -------------------------------
# Inicia Greengrass Nucleus
# -------------------------------
echo "[INFO] Iniciando Greengrass Nucleus..."
java -Droot="$GGC_DIR" -Dlog.store=FILE \
    -jar $GGC_DIR/lib/Greengrass.jar \
    --setup-system-service false \
    --deploy-dev-tools true &

# -------------------------------
# Espera Nucleus subir
# -------------------------------
sleep 15
echo "[INFO] Nucleus iniciado. Componentes ML serão executados automaticamente via recipe.yaml."

# -------------------------------
# Mantém o container ativo
# -------------------------------
tail -f /dev/null
