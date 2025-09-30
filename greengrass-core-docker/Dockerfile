FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências mínimas
RUN apt update && apt install -y \
    python3 python3-pip python3-dev \
    default-jre wget unzip sudo ca-certificates \
    libsndfile1 ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

# Atualiza pip e instala pacotes Python necessários
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install torch transformers librosa joblib numpy boto3 awsiotsdk

# Cria usuário e grupo do Greengrass
RUN adduser --system ggc_user && addgroup --system ggc_group

# Diretório de instalação do Greengrass
ENV GGC_INSTALL_DIR=/greengrass/v2
RUN mkdir -p ${GGC_INSTALL_DIR}

WORKDIR /tmp

# Baixa e descompacta o Greengrass Nucleus
RUN wget -O greengrass-nucleus-latest.zip \
    https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip && \
    unzip greengrass-nucleus-latest.zip -d ${GGC_INSTALL_DIR} && \
    rm greengrass-nucleus-latest.zip

# Copia certificados do Core Device
COPY thing-certs/ ${GGC_INSTALL_DIR}/thing-certs/

# Copia componentes do ML
COPY components/ ${GGC_INSTALL_DIR}/components/

# Copia script de startup
COPY start-greengrass.sh /usr/local/bin/start-greengrass.sh
RUN chmod +x /usr/local/bin/start-greengrass.sh

ENTRYPOINT ["/usr/local/bin/start-greengrass.sh"]
