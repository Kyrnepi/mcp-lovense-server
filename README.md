# Lovense MCP Server

[English](#english) | [Français](#français)

---

<a name="english"></a>
## 🇬🇧 English Version

### Overview

**Model Context Protocol (MCP)** server for controlling Lovense toys via the Lovense Remote app's Game Mode. This server follows the [MCP specification](https://modelcontextprotocol.io/) and uses the Python MCP SDK.

### ✨ Key Features

**MCP Compliance:**
- ✅ MCP Python SDK implementation
- ✅ Stdio transport (standard MCP communication)
- ✅ Full protocol support: tools, resources, and prompts
- ✅ JSON-RPC 2.0 compliant

**Lovense Integration:**
- 🎮 **5 Control Tools**: vibrate, rotate, pump, stop, pattern
- 📊 **2 Resources**: connected toys status, API configuration
- 🎯 **3 Prompt Templates**: control_toy, quick_vibrate, pattern_play
- 🔒 Async HTTP client with proper error handling

**Production Ready:**
- 🐳 Docker containerized
- 🔐 Non-root user execution
- 🚀 Async/await throughout
- 📝 Comprehensive logging

---

### 📋 Prerequisites

- **Docker** and Docker Compose
- **Lovense Remote app** with Game Mode enabled
- Local network access to Lovense toys
- Python 3.11+ (for local development)

---

### 🚀 Quick Start

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd lovense-mcp-server
```

#### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your settings
```

**Required environment variables:**

```env
GAME_MODE_IP=192.168.1.100    # Your Lovense Remote local IP
GAME_MODE_PORT=30010          # HTTPS port (default: 30010)
```

#### 3. Get Game Mode IP Address

1. Open the **Lovense Remote** app
2. Enable **Game Mode**
3. Note the displayed local IP (e.g., `192.168.1.100`)
4. Use this IP in the `.env` file

#### 4. Run with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f lovense-mcp

# Stop
docker-compose down
```

---

### 🔧 Usage

This is an MCP server that communicates via **stdio** (standard input/output). It's designed to be used with MCP clients like Claude Desktop, or any application that supports the MCP protocol.

#### Connecting to Claude Desktop

Add this to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lovense": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GAME_MODE_IP=192.168.1.100",
        "-e",
        "GAME_MODE_PORT=30010",
        "lovense-mcp-server"
      ]
    }
  }
}
```

Or if running locally without Docker:

```json
{
  "mcpServers": {
    "lovense": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "GAME_MODE_IP": "192.168.1.100",
        "GAME_MODE_PORT": "30010"
      }
    }
  }
}
```

---

### 🛠️ Available Tools

#### 1. `vibrate`
Send vibration command to Lovense toy.

**Parameters:**
- `toy` (string, optional): Toy ID or empty for all toys
- `intensity` (integer, required): Vibration level 0-20
- `duration` (integer, required): Duration in seconds (1-60)

**Example:**
```json
{
  "name": "vibrate",
  "arguments": {
    "intensity": 15,
    "duration": 5
  }
}
```

#### 2. `rotate`
Send rotation command to toys with rotation capability.

**Parameters:**
- `toy` (string, optional): Toy ID or empty for all toys
- `intensity` (integer, required): Rotation level 0-20
- `duration` (integer, required): Duration in seconds (1-60)

#### 3. `pump`
Send pump command to toys with pump capability.

**Parameters:**
- `toy` (string, optional): Toy ID or empty for all toys
- `intensity` (integer, required): Pump level 0-3
- `duration` (integer, required): Duration in seconds (1-60)

#### 4. `stop`
Immediately stop all running functions.

**Parameters:**
- `toy` (string, optional): Toy ID or empty for all toys

#### 5. `pattern`
Play a preset vibration pattern.

**Parameters:**
- `toy` (string, optional): Toy ID or empty for all toys
- `pattern` (string, required): One of `pulse`, `wave`, `fireworks`, `earthquake`
- `duration` (integer, required): Duration in seconds (1-60)

---

### 📊 Available Resources

Resources expose real-time information about the Lovense setup.

#### 1. `lovense://toys/connected`
List all currently connected Lovense toys and their status.

#### 2. `lovense://config/api`
View current API configuration and connection details.

---

### 🎯 Available Prompts

Prompts provide guided interaction templates.

#### 1. `control_toy`
Interactive prompt for controlling toys with guided parameters.

**Arguments:**
- `action`: Action to perform (vibrate, rotate, pump, stop, pattern)
- `intensity`: Intensity level (optional)
- `duration`: Duration in seconds (optional)

#### 2. `quick_vibrate`
Quick vibration with preset intensity.

**Arguments:**
- `level`: Intensity level (low, medium, high)

#### 3. `pattern_play`
Play a vibration pattern.

**Arguments:**
- `pattern_name`: Pattern name (pulse, wave, fireworks, earthquake)
- `duration`: Duration in seconds (optional)

---

### 🏗️ Development

#### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GAME_MODE_IP=192.168.1.100
export GAME_MODE_PORT=30010

# Run server
python server.py
```

#### Project Structure

```
lovense-mcp-server/
├── server.py              # Main MCP server implementation
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker container configuration
├── docker-compose.yml    # Docker Compose orchestration
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
├── README.md            # This file
└── REQUIREMENTS.md      # Original project requirements
```

---

### 🔒 Security Features

- **Non-root container**: Runs as user `mcpuser` (UID 1000)
- **Async HTTP client**: Uses httpx with proper timeout handling
- **Input validation**: All tool parameters are validated
- **Error handling**: Comprehensive error handling and logging
- **No hardcoded secrets**: All configuration via environment variables

---

### 🐛 Troubleshooting

#### Server won't start

```bash
# Check logs
docker-compose logs lovense-mcp

# Verify environment variables
docker-compose config
```

#### Can't connect to toys

- Verify Game Mode is enabled in Lovense Remote app
- Check that `GAME_MODE_IP` matches the IP shown in the app
- Ensure the server and toys are on the same local network
- Verify port 30010 is accessible

#### MCP client can't connect

- Verify the MCP client is properly configured
- Check that stdio communication is working
- Review server logs for errors
- Ensure the container has stdin/stdout access

---

### 📚 Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Lovense Game Mode API](https://developer.lovense.com/)
- [MCP Python SDK](https://github.com/anthropics/anthropic-mcp-python)

---

### 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<a name="français"></a>
## 🇫🇷 Version Française

### Vue d'ensemble

Serveur **Model Context Protocol (MCP)** pour contrôler les jouets Lovense via le mode Game Mode de l'application Lovense Remote. Ce serveur respecte la [spécification MCP](https://modelcontextprotocol.io/) et utilise le SDK Python MCP.

### ✨ Fonctionnalités clés

**Conformité MCP:**
- ✅ Implémentation du SDK Python MCP
- ✅ Transport stdio (communication MCP standard)
- ✅ Support complet du protocole : outils, ressources et prompts
- ✅ Conforme à JSON-RPC 2.0

**Intégration Lovense:**
- 🎮 **5 outils de contrôle** : vibrate, rotate, pump, stop, pattern
- 📊 **2 ressources** : statut des jouets connectés, configuration API
- 🎯 **3 templates de prompts** : control_toy, quick_vibrate, pattern_play
- 🔒 Client HTTP asynchrone avec gestion d'erreurs appropriée

**Prêt pour la production:**
- 🐳 Conteneurisé avec Docker
- 🔐 Exécution en utilisateur non-root
- 🚀 Async/await partout
- 📝 Journalisation complète

---

### 📋 Prérequis

- **Docker** et Docker Compose
- **Application Lovense Remote** avec le mode Game Mode activé
- Accès réseau local aux jouets Lovense
- Python 3.11+ (pour le développement local)

---

### 🚀 Démarrage rapide

#### 1. Cloner le dépôt

```bash
git clone <url-du-depot>
cd lovense-mcp-server
```

#### 2. Configurer l'environnement

```bash
cp .env.example .env
nano .env  # Modifier avec vos paramètres
```

**Variables d'environnement requises:**

```env
GAME_MODE_IP=192.168.1.100    # Votre IP locale Lovense Remote
GAME_MODE_PORT=30010          # Port HTTPS (défaut: 30010)
```

#### 3. Obtenir l'adresse IP du mode Game Mode

1. Ouvrez l'application **Lovense Remote**
2. Activez le **mode Game Mode**
3. Notez l'IP locale affichée (ex: `192.168.1.100`)
4. Utilisez cette IP dans le fichier `.env`

#### 4. Exécuter avec Docker

```bash
# Construire et démarrer
docker-compose up -d

# Voir les logs
docker-compose logs -f lovense-mcp

# Arrêter
docker-compose down
```

---

### 🔧 Utilisation

Ceci est un serveur MCP qui communique via **stdio** (entrée/sortie standard). Il est conçu pour être utilisé avec des clients MCP comme Claude Desktop, ou toute application supportant le protocole MCP.

#### Connexion à Claude Desktop

Ajoutez ceci à votre configuration Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lovense": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GAME_MODE_IP=192.168.1.100",
        "-e",
        "GAME_MODE_PORT=30010",
        "lovense-mcp-server"
      ]
    }
  }
}
```

Ou si vous exécutez localement sans Docker:

```json
{
  "mcpServers": {
    "lovense": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "GAME_MODE_IP": "192.168.1.100",
        "GAME_MODE_PORT": "30010"
      }
    }
  }
}
```

---

### 🛠️ Outils disponibles

#### 1. `vibrate`
Envoyer une commande de vibration au jouet Lovense.

**Paramètres:**
- `toy` (chaîne, optionnel): ID du jouet ou vide pour tous les jouets
- `intensity` (entier, requis): Niveau de vibration 0-20
- `duration` (entier, requis): Durée en secondes (1-60)

**Exemple:**
```json
{
  "name": "vibrate",
  "arguments": {
    "intensity": 15,
    "duration": 5
  }
}
```

#### 2. `rotate`
Envoyer une commande de rotation aux jouets avec capacité de rotation.

**Paramètres:**
- `toy` (chaîne, optionnel): ID du jouet ou vide pour tous les jouets
- `intensity` (entier, requis): Niveau de rotation 0-20
- `duration` (entier, requis): Durée en secondes (1-60)

#### 3. `pump`
Envoyer une commande de pompe aux jouets avec capacité de pompe.

**Paramètres:**
- `toy` (chaîne, optionnel): ID du jouet ou vide pour tous les jouets
- `intensity` (entier, requis): Niveau de pompe 0-3
- `duration` (entier, requis): Durée en secondes (1-60)

#### 4. `stop`
Arrêter immédiatement toutes les fonctions en cours.

**Paramètres:**
- `toy` (chaîne, optionnel): ID du jouet ou vide pour tous les jouets

#### 5. `pattern`
Jouer un pattern de vibration préconfiguré.

**Paramètres:**
- `toy` (chaîne, optionnel): ID du jouet ou vide pour tous les jouets
- `pattern` (chaîne, requis): Un de `pulse`, `wave`, `fireworks`, `earthquake`
- `duration` (entier, requis): Durée en secondes (1-60)

---

### 📊 Ressources disponibles

Les ressources exposent des informations en temps réel sur la configuration Lovense.

#### 1. `lovense://toys/connected`
Liste tous les jouets Lovense actuellement connectés et leur statut.

#### 2. `lovense://config/api`
Voir la configuration API actuelle et les détails de connexion.

---

### 🎯 Prompts disponibles

Les prompts fournissent des templates d'interaction guidée.

#### 1. `control_toy`
Prompt interactif pour contrôler les jouets avec des paramètres guidés.

**Arguments:**
- `action`: Action à effectuer (vibrate, rotate, pump, stop, pattern)
- `intensity`: Niveau d'intensité (optionnel)
- `duration`: Durée en secondes (optionnel)

#### 2. `quick_vibrate`
Vibration rapide avec intensité préréglée.

**Arguments:**
- `level`: Niveau d'intensité (low, medium, high)

#### 3. `pattern_play`
Jouer un pattern de vibration.

**Arguments:**
- `pattern_name`: Nom du pattern (pulse, wave, fireworks, earthquake)
- `duration`: Durée en secondes (optionnel)

---

### 🏗️ Développement

#### Configuration locale

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Définir les variables d'environnement
export GAME_MODE_IP=192.168.1.100
export GAME_MODE_PORT=30010

# Exécuter le serveur
python server.py
```

#### Structure du projet

```
lovense-mcp-server/
├── server.py              # Implémentation principale du serveur MCP
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration du conteneur Docker
├── docker-compose.yml    # Orchestration Docker Compose
├── .env.example          # Template des variables d'environnement
├── .gitignore           # Règles Git ignore
├── LICENSE              # Licence MIT
├── README.md            # Ce fichier
└── REQUIREMENTS.md      # Exigences originales du projet
```

---

### 🔒 Fonctionnalités de sécurité

- **Conteneur non-root**: S'exécute en tant qu'utilisateur `mcpuser` (UID 1000)
- **Client HTTP asynchrone**: Utilise httpx avec gestion de timeout appropriée
- **Validation des entrées**: Tous les paramètres d'outils sont validés
- **Gestion des erreurs**: Gestion d'erreurs et journalisation complètes
- **Pas de secrets en dur**: Toute la configuration via variables d'environnement

---

### 🐛 Dépannage

#### Le serveur ne démarre pas

```bash
# Vérifier les logs
docker-compose logs lovense-mcp

# Vérifier les variables d'environnement
docker-compose config
```

#### Impossible de se connecter aux jouets

- Vérifiez que le mode Game Mode est activé dans l'application Lovense Remote
- Vérifiez que `GAME_MODE_IP` correspond à l'IP affichée dans l'application
- Assurez-vous que le serveur et les jouets sont sur le même réseau local
- Vérifiez que le port 30010 est accessible

#### Le client MCP ne peut pas se connecter

- Vérifiez que le client MCP est correctement configuré
- Vérifiez que la communication stdio fonctionne
- Consultez les logs du serveur pour les erreurs
- Assurez-vous que le conteneur a accès à stdin/stdout

---

### 📚 Ressources supplémentaires

- [Documentation du protocole MCP](https://modelcontextprotocol.io/)
- [API Lovense Game Mode](https://developer.lovense.com/)
- [SDK Python MCP](https://github.com/anthropics/anthropic-mcp-python)

---

### 📜 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
