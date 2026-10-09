# 📦 Asset Management Microservice

[![Docker Build CI](https://github.com/SystemAnis/asset-microservice/actions/workflows/ci.yml/badge.svg)](https://github.com/SystemAnis/asset-microservice/actions/workflows/ci.yml)

Un microservizio RESTful progettato per la gestione e il tracciamento degli asset infrastrutturali (es. server, database). Il progetto è focalizzato sulle best practice di containerizzazione e automazione CI/CD, concepito per un deployment rapido in ambienti Cloud.

## 🏗️ Architettura del Servizio

L'infrastruttura è interamente containerizzata e servita tramite un server WSGI production-ready, con una pipeline automatizzata per la validazione delle build.

```mermaid
graph TD
    Client([Client / Browser]) -->|Richiesta HTTP| Gunicorn
    
    subgraph DockerContainer [Container Docker]
        Gunicorn[Gunicorn WSGI Server] -->|Workers| Flask[Applicazione Flask]
        Flask -->|Gestione Dati| Logic[Logica Asset / Error Handling]
    end

    subgraph CIPipeline [CI/CD Pipeline]
        Code[GitHub Repository] -->|Push / PR| Actions[GitHub Actions]
        Actions -->|Test Build| DockerImage[Docker Image Validation]
    end
    
    classDef container fill:#0db7ed,stroke:#fff,stroke-width:2px,color:#fff;
    class DockerContainer container;
