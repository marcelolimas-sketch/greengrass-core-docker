# PSI5120-TCN-Trabalho-Final

Trabalho final da disciplina PSI5120 - Tópicos de Computação em Nuvem de
pós-graduação oferecida na Escola Politécnica da USP.

*Produzido pelos alunos:\
João Vilar de Souza Junior e Marcelo Lima dos Santos*

## Edge Computing com AWS Greengrass V2 para Reconhecimento de Fala

Este projeto implementa uma solução de **computação em borda**
utilizando o **AWS Greengrass V2** para realizar **reconhecimento de
fala baseado em comandos curtos de voz**.\
O sistema emprega o modelo **wav2vec2** para extração de embeddings,
seguido de **PCA** para redução de dimensionalidade e um **classificador
MLP** para a tarefa de detecção.\
Os resultados das inferências são publicados em tópicos **MQTT** no
**AWS IoT Core**, que permite integração com aplicações em nuvem.

## Pré-requisitos

-   Conta AWS ativa
-   Windows 10/11 com **WSL 2** e distribuição **Ubuntu 22.04 LTS**
    instalada
-   **Docker Engine** instalado no WSL
-   **AWS CLI** configurada (`aws configure`)
-   **Python 3.8+**, `pip` e bibliotecas (`torch`, `transformers`,
    `librosa`, `joblib`, etc.)

## Roteiro

1.  **Preparar ambiente no WSL Ubuntu**

    ``` bash
    sudo apt update
    sudo apt install -y python3 python3-pip docker.io
    python3 --version
    docker --version
    ```

2.  **Configurar usuários do Greengrass**

    ``` bash
    sudo adduser --system ggc_user
    sudo addgroup --system ggc_group
    ```

3.  **Provisionar o dispositivo Greengrass no AWS IoT Core**

    -   Criar **Policy IoT** com permissões de `iot:Publish`,
        `iot:Subscribe`, `s3:GetObject`.
    -   Registrar o **Core Device** no console da AWS IoT.
    -   Baixar os artefatos de instalação (connection kit + installer).

4.  **Instalar o Greengrass Core V2**

    ``` bash
    unzip greengrass-nucleus-latest.zip -d GreengrassInstaller
    sudo mkdir -p /greengrass/v2
    sudo unzip MeuCore-connectionKit.zip -d /greengrass/v2
    sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE        -jar ./GreengrassInstaller/lib/Greengrass.jar        --init-config /greengrass/v2/config.yaml        --component-default-user ggc_user:ggc_group        --setup-system-service true
    ```

5.  **Organizar diretórios do projeto**

        greengrass-core-docker/
        ├── components/
        │   ├── modelos/   (PCA e MLP treinados)
        │   └── audio/     (amostras de áudio para teste)
        └── inference.py   (código de inferência)

6.  **Construir o componente ML**

    -   Arquivo principal: `inference.py`

        -   Extrai embeddings com wav2vec2\
        -   Aplica PCA\
        -   Classifica com MLP\
        -   Publica resultado em tópico MQTT (`ml/inference`)

    -   Criar `recipe.yaml`:

        ``` yaml
        RecipeFormatVersion: '2020-01-25'
        ComponentName: com.projeto.ml-inference
        ComponentVersion: '1.0.0'
        Manifests:
          - Platform:
              OS: linux
            Lifecycle:
              Run: python3 -u {artifacts:path}/inference.py
        ```

    -   Empacotar e enviar para o S3:

        ``` bash
        zip -r ml_component.zip inference.py modelos/ audio/
        aws s3 cp ml_component.zip s3://<SEU_BUCKET_NAME>/artifacts/
        aws greengrassv2 create-component-version --inline-recipe file://recipe.yaml
        ```

7.  **Implantar no Greengrass Core**

    -   Criar uma **deployment** no console AWS IoT Greengrass.
    -   Selecionar o Core Device e adicionar o componente
        `com.projeto.ml-inference`.

8.  **Testar a inferência**

    -   Monitorar logs:

        ``` bash
        sudo tail -f /greengrass/v2/logs/com.projeto.ml-inference.log
        ```

    -   Verificar publicações no MQTT no AWS IoT Core (`ml/inference`).

## Métricas

-   Dataset: **Google Speech Commands** (subconjunto de 8 palavras,
    \~4000 áudios).
-   Modelo: wav2vec2 + PCA + MLP.
-   Resultados:
    -   **Acurácia sem PCA:** 89.25%
    -   **Acurácia com PCA:** 90.38%
    -   **Vantagem do PCA:** redução de dimensionalidade (768 → 116) e
        convergência mais rápida.
-   Publicação MQTT em tempo real validada no AWS IoT Core.

## Limpeza

Para remover os recursos criados:

``` bash
aws greengrassv2 delete-deployment --deployment-id <id>
aws iot delete-thing --thing-name MeuCoreWSLV2
```
aws iot delete-thing --thing-name MeuCoreWSLV2
```
