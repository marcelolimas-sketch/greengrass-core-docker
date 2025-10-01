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
- Windows 10/11 com **WSL 2** e distribuição **Ubuntu 22.04 LTS**
- **Docker Engine** instalado no WSL
- **AWS CLI** configurada (`aws configure`)
- **Python 3.8+**, `pip` e bibliotecas (`torch`, `transformers`, `librosa`, `joblib`, etc.)
- Java JRE instalado (`default-jre`)

## Roteiro Passo a Passo

### 1 - Treinamento do modelo wav2vec2
- Criar ambiente virtual Python, instalar dependências (`torch`, `transformers`, `datasets`, `librosa`).
- Carregar dataset (ex.: Google Speech Commands).
- Fine-tunar modelo `wav2vec2` ou usar pré-treinado.
- Salvar modelo e processor em `modelos/wav2vec2_finetuned/`.

### 2 - Aplicação do PCA
- Extrair embeddings do wav2vec2 (média temporal das hidden states).
- Ajustar PCA (`sklearn.decomposition.PCA`) preservando ~95% da variância.
- Salvar em `modelos/pca_model.pkl`.
- Confirmar número de componentes (ex.: 116).

### 3 - Inferência com áudios do diretório `áudio/`
- Implementar `inference.py`:
  - Carrega wav2vec2, PCA e MLP treinado.
  - Extrai embedding → reduz com PCA → classifica com MLP.
  - Itera sobre `áudio/*.wav` e mostra rótulos previstos.
- Testar localmente:
```bash
python3 inference.py
```

### 4 - Preparação do ambiente para implementar o Greengrass V2 (Docker e Python no WSL)
- Instalar pacotes:
```bash
sudo apt update
sudo apt install -y default-jre docker.io python3 python3-pip unzip
```
- Adicionar usuário ao grupo docker:
```bash
sudo usermod -aG docker $USER
```
- Criar usuários Greengrass:
```bash
sudo adduser --system ggc_user || true
sudo addgroup --system ggc_group || true
```
- Configurar AWS CLI (`aws configure`).

### 5 - Build da imagem Docker apropriada via `Dockerfile`
- Exemplo de `Dockerfile`:
```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y default-jre python3 python3-pip docker.io unzip
RUN adduser --system ggc_user && addgroup --system ggc_group
WORKDIR /greengrass/v2
COPY start-greengrass.sh /usr/local/bin/start-greengrass.sh
RUN chmod +x /usr/local/bin/start-greengrass.sh
ENTRYPOINT ["/usr/local/bin/start-greengrass.sh"]
```
- Build da imagem:
```bash
docker build -t greengrass-v2-core .
```

### 6 - Criação do componente Greengrass + inicialização (`start-greengrass.sh`)
- `start-greengrass.sh`:
```bash
#!/bin/bash
set -e
exec java -Droot="/greengrass/v2" -Dlog.store=FILE -jar /greengrass/v2/lib/Greengrass.jar --start
```
- `recipe.yaml` (trecho relevante):
```yaml
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

### 7 - Testes sugeridos
- **Teste local:** executar `inference.py` e confirmar previsões.
- **Verificar artefatos dentro do container:**
```bash
docker exec -it greengrass-core-device ls -la /greengrass/v2/components
```
- **Logs:**
```bash
docker exec -it greengrass-core-device tail -f /greengrass/v2/logs/greengrass.log
docker exec -it greengrass-core-device tail -f /greengrass/v2/logs/com.projeto.ml-inference.log
```
- **MQTT client (AWS IoT Core):** assinar tópico `ml/inference` e observar publicações.

### 8 - Verificação de falhas
- **Falha no publish MQTT via IPC:** revisar `accessControl` no recipe, role IAM do Core Device (`iot:Publish`, `iot:Connect`, `s3:GetObject`).
- **Arquivos não aparecem em `/greengrass/v2/components`:** povoar volume `greengrass-v2-data` após `docker run` ou usar bind-mount.
- **Erros em dependências:** incluir `requirements.txt` e ajustar recipe (`Install` com `pip install`).

## Métricas
- Dataset: **Google Speech Commands** (8 palavras, ~4000 áudios).  
- Pipeline: wav2vec2 + PCA + MLP.  
- Resultados de teste:  
  - **Acurácia sem PCA:** 89,25%  
  - **Acurácia com PCA:** 90,38%  
- PCA reduziu dimensionalidade (768 → 116) e acelerou convergência.  
- Publicação MQTT validada no AWS IoT Core.

## Limpeza
```bash
aws greengrassv2 delete-deployment --deployment-id <id>
aws iot delete-thing --thing-name MeuCoreWSLV2
docker rm -f greengrass-core-device
docker volume rm greengrass-v2-data
```

## Referência completa do projeto
Para uma análise detalhada da implementação, desafios e resultados obtidos neste projeto, consulte o relatório completo do trabalho final disponível em:
https://drive.google.com/file/d/1UwNsYPePgyaC6Nqp4JXKp6taHG-rkjUZ/view?usp=sharing
