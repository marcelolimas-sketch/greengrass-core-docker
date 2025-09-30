# PSI5120-TCN-Trabalho-Final
Trabalho final da matéria PSI5120 - Tópicos de Computação em Nuvem de pós-graduação oferecida na Escola Politécnica da USP.

_Produzido pelos alunos:_  
**João Vilar de Souza Junior e Marcelo Lima dos Santos**

## Edge Computing com AWS Greengrass V2 para Reconhecimento de Fala
Este projeto implementa uma solução de **computação em borda** utilizando o **AWS Greengrass V2** para realizar **reconhecimento de fala baseado em comandos curtos de voz**.  
O sistema emprega o modelo **wav2vec2** para extração de embeddings, seguido de **PCA** para redução de dimensionalidade e um **classificador MLP** para a tarefa de detecção.  
Os resultados das inferências são publicados em tópicos **MQTT** no **AWS IoT Core**, permitindo integração com aplicações em nuvem.

## Pré-requisitos
- Conta AWS ativa
- Windows 10/11 com **WSL 2** e distribuição **Ubuntu 22.04 LTS** instalada
- **Docker Engine** instalado no WSL
- **AWS CLI** configurada (`aws configure`)
- **Python 3.8+**, `pip` e bibliotecas (`torch`, `transformers`, `librosa`, `joblib`, etc.)
- Java JRE instalado (`default-jre`)

## Roteiro

### Passo A — Preparar e validar o ambiente local
```bash
sudo apt update
sudo apt install -y python3 python3-pip docker.io unzip default-jre
docker --version
python3 --version
sudo usermod -aG docker $USER
# reabra o terminal para aplicar a mudança de grupo
sudo adduser --system ggc_user || true
sudo addgroup --system ggc_group || true
```

### Passo B — Gerenciar os componentes no container (resolvendo problema de diretórios ausentes)
Quando se monta um volume em `/greengrass/v2`, ele **sobrescreve** o conteúdo copiado no build da imagem.  
Duas opções seguras:

**Opção 1 (recomendada): povoar o volume após o build**
```bash
docker build -t greengrass-v2-core .

docker run -d --name greengrass-core-device \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... -e AWS_DEFAULT_REGION=... \
  -e THING_NAME=MeuThing \
  -v greengrass-v2-data:/greengrass/v2 \
  -v /tmp/greengrass-ipc:/tmp/greengrass-ipc \
  -v /var/run/docker.sock:/var/run/docker.sock \
  greengrass-v2-core

# copiar componentes para o volume
docker run --rm -v $(pwd)/components:/src -v greengrass-v2-data:/data alpine \
  sh -c "mkdir -p /data/greengrass/v2/components && cp -r /src/* /data/greengrass/v2/components/"
```

**Opção 2: bind-mount do diretório de componentes (bom para desenvolvimento)**
```bash
docker run -it --rm --name greengrass-core-device \
  -v $(pwd)/components:/greengrass/v2/components \
  greengrass-v2-core
```

### Passo C — Provisionamento e verificação do Greengrass Core
1. Baixar o **connection kit** e o **installer** no console AWS IoT.  
2. Dentro do container ou no WSL, descompactar:
```bash
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller
sudo mkdir -p /greengrass/v2
sudo unzip MeuCore-connectionKit.zip -d /greengrass/v2
```
3. Instalar o Nucleus:
```bash
sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --init-config /greengrass/v2/config.yaml \
  --component-default-user ggc_user:ggc_group \
  --setup-system-service true
```
4. Verificar se está rodando:
```bash
sudo tail -f /greengrass/v2/logs/greengrass.log
```

### Passo D — Criar o componente de ML (inference)
1. Organizar diretórios:
```
components/
├── modelos/    (PCA e MLP treinados)
├── audio/      (amostras para teste)
└── inference.py
```
2. Empacotar artefatos e enviar para S3:
```bash
zip -r model_and_code.zip inference.py modelos/ audio/
aws s3 cp model_and_code.zip s3://<SEU_BUCKET>/artifacts/com.projeto.ml-inference/1.0.0/
```
3. Criar `recipe.json` com `accessControl` para `mqttproxy`:
```json
"ComponentConfiguration": {
  "DefaultConfiguration": {
    "accessControl": {
      "aws.greengrass.ipc.mqttproxy": {
        "com.projeto.ml-inference:mqttproxy:1": {
          "operations": [ "aws.greengrass.ipc.mqttproxy:PublishToIoTCore" ],
          "resources": ["*"]
        }
      }
    }
  }
}
```
4. Registrar no Greengrass:
```bash
aws greengrassv2 create-component-version --inline-recipe file://recipe.json
```

### Passo E — Implantar e testar
1. Criar *deployment* no console AWS IoT Greengrass, selecionando o Core Device e o componente.  
2. Verificar logs:
```bash
docker exec -it greengrass-core-device tail -f /greengrass/v2/logs/com.projeto.ml-inference.log
```
3. Testar publicação no console AWS IoT → Test → MQTT client → assine `ml/inference`.

### Passo F — Diagnóstico para falhas de publicação
- Verificar se o socket IPC existe em `/tmp/greengrass-ipc`.  
- Confirmar se a role IAM do Core Device possui permissões `iot:Publish` para o tópico usado.  
- Rodar teste manual de publicação dentro do container para validar o IPC.  
- Conferir se o recipe contém `accessControl` corretamente configurado.

## Métricas
- Dataset: **Google Speech Commands** (8 palavras, ~4000 áudios).  
- Pipeline: wav2vec2 + PCA + MLP.  
- Resultados de teste:  
  - **Acurácia sem PCA:** 89,25%  
  - **Acurácia com PCA:** 90,38%  
- PCA reduziu dimensionalidade (768 → 116) e acelerou convergência.  
- Publicação MQTT validada no AWS IoT Core.

## Limpeza
Para remover os recursos criados:
```bash
aws greengrassv2 delete-deployment --deployment-id <id>
aws iot delete-thing --thing-name MeuCoreWSLV2
docker rm -f greengrass-core-device
docker volume rm greengrass-v2-data
```
docker volume rm greengrass-v2-data
```
