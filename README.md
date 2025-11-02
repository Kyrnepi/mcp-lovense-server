# Lovense MCP HTTP Server / Serveur MCP HTTP Lovense

[English](#english) | [Français](#français)

---

<a name="english"></a>
## 🇬🇧 English Version

### Lovense MCP HTTP Server

Streamable HTTP MCP (Model Context Protocol) server for controlling Lovense toys via the Lovense Remote app in Game Mode.

### 🚀 Features

- **Complete MCP Protocol**: Support for `initialize`, `tools/list`, and `tools/call` methods
- **JSON-RPC 2.0 Format**: Compliant with MCP standard
- **HTTP Streaming**: Streamed responses for better performance
- **Bearer Authentication**: Token-based security
- **Containerized**: Easy deployment with Docker
- **Health Checks**: Server status monitoring

### 📋 Prerequisites

- Docker and Docker Compose installed
- Lovense Remote app with Game Mode enabled
- Local network access to Lovense toys

### 🛠️ Installation

#### 1. Clone or create the project structure

```bash
mkdir lovense-mcp-server
cd lovense-mcp-server
```

#### 2. Create files

Create the following files in the directory:
- `server.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.env` (based on `.env.example`)

#### 3. Configuration

Copy `.env.example` to `.env` and configure the variables:

```bash
cp .env.example .env
nano .env  # or your preferred editor
```

**Required environment variables:**

```env
GAME_MODE_IP=192.168.1.100        # Local IP of Lovense Remote
GAME_MODE_PORT=30010              # HTTPS port (default: 30010)
AUTH_TOKEN=your-secure-token      # Authentication token
```

**Generate a secure token:**

```bash
# Linux/Mac
openssl rand -hex 32

# Or use an online generator
```

#### 4. Get Game Mode IP

1. Open the Lovense Remote app
2. Enable **Game Mode**
3. Note the displayed local IP (e.g., `192.168.1.100`)
4. Use this IP in `GAME_MODE_IP`

### 🚢 Deployment

#### With Docker Compose (recommended)

```bash
# Build and start the server
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop the server
docker-compose down
```

#### With Docker directly

```bash
# Build the image
docker build -t lovense-mcp .

# Start the container
docker run -d \
  -p 8000:8000 \
  -e GAME_MODE_IP=192.168.1.100 \
  -e GAME_MODE_PORT=30010 \
  -e AUTH_TOKEN=your-token \
  --name lovense-mcp-server \
  lovense-mcp
```

### 📡 API Usage

#### Main endpoint

```
POST http://localhost:8000/mcp
```

**Required headers:**
```
Authorization: Bearer your-secure-token
# OR without Bearer prefix:
Authorization: your-secure-token
Content-Type: application/json
```

#### 1. Initialize (MCP handshake)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "my-client",
      "version": "1.0.0"
    }
  }
}
```

#### 2. List available tools

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

#### 3. Call a tool - Send vibration

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "send_vibrate",
    "arguments": {
      "toy": "",
      "intensity": 15,
      "duration": 5
    }
  }
}
```

#### 4. Call a tool - Stop functions

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "send_stop",
    "arguments": {
      "toy": ""
    }
  }
}
```

### 🔧 Example with cURL

```bash
# 1. Initialize
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
  }'

# 2. Send vibration
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "send_vibrate",
      "arguments": {
        "intensity": 10,
        "duration": 3
      }
    }
  }'
```

### 🐍 Example with Python

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-secure-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Initialize
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "python-client", "version": "1.0.0"}
        }
    }
)
print("Initialize:", response.json())

# Send vibration
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "send_vibrate",
            "arguments": {
                "intensity": 15,
                "duration": 5
            }
        }
    }
)
print("Vibrate:", response.json())
```

### 🐛 Troubleshooting

#### Authentication error (401/403)

- Check that the `Authorization` header is present
- Verify the token matches `AUTH_TOKEN` in `.env`
- The server accepts both formats: `Bearer token` or just `token`

#### Connection error to toys

- Verify Game Mode is enabled in Lovense Remote
- Check that `GAME_MODE_IP` matches the IP shown in the app
- Verify port 30010 is accessible
- Ensure server and toys are on the same local network

### 📝 Project Structure

```
lovense-mcp-server/
├── server.py              # Main MCP HTTP server
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker orchestration
├── .env                  # Environment variables (create this)
├── .env.example          # Configuration example
└── README.md             # Documentation
```

---

<a name="français"></a>
## 🇫🇷 Version Française

### Serveur MCP HTTP Lovense

Serveur MCP (Model Context Protocol) HTTP streamable pour contrôler les jouets Lovense via l'application Lovense Remote en mode Game Mode.

### 🚀 Fonctionnalités

- **Protocole MCP complet** : Support des méthodes `initialize`, `tools/list`, et `tools/call`
- **Format JSON-RPC 2.0** : Respect du standard MCP
- **Streaming HTTP** : Réponses streamées pour une meilleure performance
- **Authentification Bearer** : Sécurisation par token
- **Containerisé** : Déploiement facile avec Docker
- **Health checks** : Surveillance de l'état du serveur

### 📋 Prérequis

- Docker et Docker Compose installés
- Application Lovense Remote avec le mode Game Mode activé
- Accès réseau local aux jouets Lovense

### 🛠️ Installation

#### 1. Cloner ou créer la structure du projet

```bash
mkdir lovense-mcp-server
cd lovense-mcp-server
```

#### 2. Créer les fichiers

Créez les fichiers suivants dans le répertoire :
- `server.py`
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.env` (basé sur `.env.example`)

#### 3. Configuration

Copiez `.env.example` vers `.env` et configurez les variables :

```bash
cp .env.example .env
nano .env  # ou votre éditeur préféré
```

**Variables d'environnement requises :**

```env
GAME_MODE_IP=192.168.1.100        # IP locale de Lovense Remote
GAME_MODE_PORT=30010              # Port HTTPS (défaut: 30010)
AUTH_TOKEN=votre-token-securise   # Token d'authentification
```

**Générer un token sécurisé :**

```bash
# Linux/Mac
openssl rand -hex 32

# Ou utilisez un générateur en ligne
```

#### 4. Obtenir l'IP de Game Mode

1. Ouvrez l'application Lovense Remote
2. Activez le mode **Game Mode**
3. Notez l'IP locale affichée (ex: `192.168.1.100`)
4. Utilisez cette IP dans `GAME_MODE_IP`

### 🚢 Déploiement

#### Avec Docker Compose (recommandé)

```bash
# Construire et démarrer le serveur
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Arrêter le serveur
docker-compose down
```

#### Avec Docker directement

```bash
# Construire l'image
docker build -t lovense-mcp .

# Démarrer le container
docker run -d \
  -p 8000:8000 \
  -e GAME_MODE_IP=192.168.1.100 \
  -e GAME_MODE_PORT=30010 \
  -e AUTH_TOKEN=votre-token \
  --name lovense-mcp-server \
  lovense-mcp
```

### 📡 Utilisation de l'API

#### Endpoint principal

```
POST http://localhost:8000/mcp
```

**Headers requis :**
```
Authorization: Bearer votre-token-securise
# OU sans le préfixe Bearer :
Authorization: votre-token-securise
Content-Type: application/json
```

#### 1. Initialize (handshake MCP)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "mon-client",
      "version": "1.0.0"
    }
  }
}
```

#### 2. Lister les outils disponibles

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

#### 3. Appeler un outil - Envoyer une vibration

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "send_vibrate",
    "arguments": {
      "toy": "",
      "intensity": 15,
      "duration": 5
    }
  }
}
```

#### 4. Appeler un outil - Arrêter les fonctions

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "send_stop",
    "arguments": {
      "toy": ""
    }
  }
}
```

### 🔧 Exemple avec cURL

```bash
# 1. Initialize
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer votre-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
  }'

# 2. Envoyer vibration
curl -X POST http://localhost:8000/mcp \
  -H "Authorization: votre-token" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "send_vibrate",
      "arguments": {
        "intensity": 10,
        "duration": 3
      }
    }
  }'
```

### 🐍 Exemple avec Python

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "votre-token-securise"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Initialize
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "python-client", "version": "1.0.0"}
        }
    }
)
print("Initialize:", response.json())

# Envoyer vibration
response = requests.post(
    f"{BASE_URL}/mcp",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "send_vibrate",
            "arguments": {
                "intensity": 15,
                "duration": 5
            }
        }
    }
)
print("Vibrate:", response.json())
```

### 📊 Monitoring

#### Logs du container

```bash
# Suivre les logs en temps réel
docker-compose logs -f lovense-mcp

# Afficher les dernières lignes
docker-compose logs --tail=100 lovense-mcp
```

#### Status du container

```bash
docker-compose ps
```

### 🔒 Sécurité

- **Authentification Bearer obligatoire** : Toutes les requêtes nécessitent un token valide
- **Token dans les variables d'environnement** : Jamais codé en dur dans le code
- **Validation des paramètres** : Vérification des intensités et durées
- **Logs sécurisés** : Le token n'est jamais loggé en entier

### 🐛 Dépannage

#### Le serveur ne démarre pas

```bash
# Vérifier les logs
docker-compose logs lovense-mcp

# Vérifier les variables d'environnement
docker-compose config
```

#### Erreur d'authentification (401/403)

- Vérifiez que le header `Authorization` est présent
- Vérifiez que le token correspond à `AUTH_TOKEN` dans `.env`
- Le serveur accepte les deux formats : `Bearer token` ou juste `token`

#### Erreur de connexion aux jouets

- Vérifiez que le mode Game Mode est activé dans Lovense Remote
- Vérifiez que `GAME_MODE_IP` correspond à l'IP affichée dans l'app
- Vérifiez que le port 30010 est accessible
- Vérifiez que le serveur et les jouets sont sur le même réseau local

#### Health check échoue

```bash
# Tester manuellement
curl http://localhost:8000/health

# Vérifier si le port est accessible
netstat -an | grep 8000
```

### 📝 Structure du projet

```
lovense-mcp-server/
├── server.py              # Serveur MCP HTTP principal
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration Docker
├── docker-compose.yml    # Orchestration Docker
├── .env                  # Variables d'environnement (à créer)
├── .env.example          # Exemple de configuration
└── README.md             # Documentation
```

### 🤝 Support

Pour les problèmes liés à :
- **Lovense Remote** : Consultez la documentation Lovense
- **MCP Protocol** : Consultez la spécification MCP officielle
- **Ce serveur** : Vérifiez les logs et les variables d'environnement

### 📜 Licence

Ce projet est fourni tel quel pour un usage personnel.