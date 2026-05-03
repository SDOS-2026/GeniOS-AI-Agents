# GeniOS Gateway 🚪

The GeniOS Gateway serves as the unified entry point and thin proxy for the entire GeniOS AI Agent ecosystem. It simplifies client interaction by abstracting multiple backend services behind a single API surface.

## 🏗️ Core Architecture

The gateway is a high-performance **FastAPI** application designed to be extremely lightweight. It does not contain agent logic; instead, it focuses on request routing, header management, and service discovery.

- **Port**: 8000
- **Proxy Engine**: `httpx` (Asynchronous HTTP client)

## 🔀 Routing Capabilities

The gateway uses a dynamic routing pattern to forward requests to backend services.

### Service Map
The gateway maintains a registry of available services:
- `daa`: Daily Attention Agent (Internal Port 8001)
- `email`: Email Drafting Agent (Internal Port 8002)

### Proxy Logic (`/{service}/{path}`)
- **Endpoint**: `ANY /{service}/{path:path}`
- **Logic**:
    1. Extracts the `service` name from the URL.
    2. Looks up the backend URL in the `SERVICE_MAP`.
    3. Forwards the request (Method, Body, Headers, Query Params) to the backend.
    4. Streams the response back to the client.

## 🚀 Setup & Execution

### 1. Installation
Ensure you have the required dependencies installed (refer to the root `requirements.txt` or `gateway/requirements.txt`).

### 2. Running the Gateway
Start the proxy server using the provided shell script:

```bash
bash start.sh
```

### 3. Usage Example
To interact with the **Email Agent** via the gateway:
- **Direct Backend URL**: `http://localhost:8002/draft`
- **Gateway Proxy URL**: `http://localhost:8000/email/draft`

To check the health of the entire stack:
- **Endpoint**: `GET http://localhost:8000/`
- **Response**: Returns a list of all active/registered services.
