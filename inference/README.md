# vLLM Inference with Docker, OpenTelemetry, Prometheus & Grafana

This repository demonstrates how to spin up a scalable vLLM-based inference service instrumented with OpenTelemetry metrics, collected by Prometheus, and visualized in Grafana—fronted by an Nginx reverse-proxy.

---

## Features

- **High-performance** vLLM inference container, GPU-accelerated  
- **OpenTelemetry** instrumentation for real-time metrics export  
- **Prometheus** scraping the `/metrics` endpoint  
- **Grafana** provisioning of dashboards & data sources (out-of-the-box)  
- **Nginx** as a reverse proxy with dynamic DNS resolution  

---

## Architecture

```text
+-----------+        +-------------+        +-------------+         +-----------+
|  Client   |  HTTP  |    Nginx    |  HTTP  |   vLLM API   |  🡒 | GPU / ML  |
|  (curl,   | ────▶  |  (80/TCP)   | ────▶  | (8000/TCP)   |        |  Worker   |
|   Postman)|        +-------------+        /  + metrics \          +-----------+
|           |                                 │ (9464/TCP)         
+-----------+                                 ▼                   
                                       +-------------+            
                                       | Prometheus  |            
                                       |   (9090)    |            
                                       +-------------+            
                                             │                  
                                             ▼                  
                                       +-------------+            
                                       |   Grafana   |            
                                       |   (3000)    |            
                                       +-------------+            
```

---
## Inference folder Layout

```doctest
.
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   └── provisioning/
│       ├── datasources/datasources.yml
│       └── dashboards/dashboards.yml
│       └── dashboards/vllm.json
└── vllm/
    ├── Dockerfile
    └── scripts/
        └── run.sh
```

- docker-compose.yml – declarative multi‐container setup
- nginx/nginx.conf – reverse proxy + /metrics proxying
- prometheus/prometheus.yml – scrape vLLM’s OpenTelemetry exporter
- grafana/provisioning/ – pre-configured data source & dashboard
- vllm/ – custom Dockerfile building vLLM + OpenTelemetry support

---
## Launch all services
```bash
docker-compose up --build -d
```
