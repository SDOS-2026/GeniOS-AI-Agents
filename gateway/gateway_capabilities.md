# GeniOS Gateway Capabilities & Logic

The GeniOS Gateway serves as the unified entry point and thin proxy for the entire GeniOS AI Agent ecosystem. It simplifies client interaction by abstracting multiple backend services behind a single API surface.

## 1. Core Architecture

The gateway is a high-performance **FastAPI** application designed to be extremely lightweight. It does not contain agent logic; instead, it focuses on request routing, header management, and service discovery.

- **Port**: 8000
- **Proxy Engine**: `httpx` (Asynchronous HTTP client)

---

## 2. Routing Capabilities

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
- **Header Handling**: 
    - Automatically strips the `host` header before forwarding to prevent routing loops.
    - Filters out "hop-by-hop" headers (like `transfer-encoding`) from the backend response to ensure compatibility with standard HTTP clients.

---

## 3. Benefits for Other Services

The gateway provides several key advantages to the GeniOS architecture:

1. **Unified Interface**: Clients (like the Streamlit Frontend) only need to know one URL (`http://localhost:8000`) instead of tracking separate ports for every agent.
2. **Simplified CORS/Auth**: Centralizing entry points makes it easier to implement cross-origin policies or global authentication layers in the future.
3. **Decoupling**: Backend agents can be restarted, moved to different ports, or even different servers without the client ever needing a configuration change.
4. **Visibility**: Provides a central point for logging and monitoring traffic across all GeniOS agents.

---

## 4. Usage Example

To interact with the **Email Agent** via the gateway:
- **Direct Backend URL**: `http://localhost:8002/draft`
- **Gateway Proxy URL**: `http://localhost:8000/email/draft`

To check the health of the entire stack:
- **Endpoint**: `GET http://localhost:8000/`
- **Response**: Returns a list of all active/registered services.
