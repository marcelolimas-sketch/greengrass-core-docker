import os
import json
import torch
import joblib
import librosa
import numpy as np
from transformers import Wav2Vec2Processor, Wav2Vec2Model
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClient
from awsiot.greengrasscoreipc.model import PublishToTopicRequest

# -------------------------------
# Configurações
# -------------------------------
AUDIO_DIR = "audio"  # pasta com os áudios
DEVICE = "cpu"  # ou "cuda"
MQTT_TOPIC = "ml/inference"

# -------------------------------
# Configurar IPC do Greengrass
# -------------------------------
ipc_client = GreengrassCoreIPCClient()

def publish_result(topic, payload):
    """Publica payload JSON no tópico MQTT via Greengrass IPC"""
    request = PublishToTopicRequest()
    request.topic = topic
    request.payload = json.dumps(payload).encode('utf-8')
    try:
        future = ipc_client.publish_to_topic(request)
        future.result()
    except Exception as e:
        print(f"Erro ao publicar MQTT: {e}")

# -------------------------------
# Carregar Wav2Vec2
# -------------------------------
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base")
wav2vec2 = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")
wav2vec2.eval()
wav2vec2.to(DEVICE)

# -------------------------------
# Carregar PCA e MLP treinados
# -------------------------------
pca = joblib.load("modelos/pca_model.pkl")
mlp_model_state = torch.load("modelos/mlp_model.pth", map_location=DEVICE)

# Reconstruir o modelo MLP corretamente
# (assumindo que você tem a classe MLP definida)
import torch.nn as nn

class MLP(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, output_dim=8):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

mlp_model = MLP(input_dim=pca.n_components_, hidden_dim=64, output_dim=8)
mlp_model.load_state_dict(mlp_model_state)
mlp_model.eval()
mlp_model.to(DEVICE)

# -------------------------------
# Função para extrair embeddings médios do áudio
# -------------------------------
def extract_embedding(file_path):
    audio, sr = librosa.load(file_path, sr=16000)
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = wav2vec2(**inputs.to(DEVICE))
    embedding = outputs.last_hidden_state[0].mean(dim=0).cpu().numpy()
    return embedding

# -------------------------------
# Função para classificar áudio
# -------------------------------
def classify_audio(file_path):
    emb = extract_embedding(file_path)
    emb_reduced = pca.transform([emb])
    emb_tensor = torch.tensor(emb_reduced, dtype=torch.float32).to(DEVICE)
    with torch.no_grad():
        logits = mlp_model(emb_tensor)
    pred = torch.argmax(logits, dim=1).item()
    return pred

# -------------------------------
# Rótulos
# -------------------------------
rotulos = ['yes', 'no', 'stop', 'up', 'down', 'dog', 'three', 'tree']
label_map = {i: label for i, label in enumerate(rotulos)}

# -------------------------------
# Loop pelos arquivos de áudio
# -------------------------------
if __name__ == "__main__":
    for root, _, files in os.walk(AUDIO_DIR):
        for file in sorted(files):
            if file.endswith(".wav"):
                path = os.path.join(root, file)
                pred_idx = classify_audio(path)
                pred_label = label_map[pred_idx]
                print(f"{file} -> {pred_label}")
                publish_result(MQTT_TOPIC, {"file": file, "prediction": pred_label})
