# Architecture — Component & Deployment (Week 1)

## Component diagram

```mermaid
flowchart LR
    A[React SPA Customer Host Admin] --> B[Azure Load Balancer]
    B --> C[FastAPI App VM Scale Set]
    C --> D[Auth Service]
    C --> E[Listing Service]
    C --> F[Booking Service]
    C --> G[Review Service]
    C --> H[Analytics Service]
    D --> I[PostgreSQL]
    E --> I
    F --> I
    G --> I
    H --> I
    E --> J[Blob Storage Photos Videos]
    A --> K[Google Maps JS API]
```

## Deployment diagram

```mermaid
flowchart LR
    U[Browser] --> LB[Azure Load Balancer HTTPS]
    LB --> V1[VM Scale Set Instance 1 FastAPI]
    LB --> V2[VM Scale Set Instance 2 FastAPI]
    V1 --> DB[Azure Database for PostgreSQL Private]
    V2 --> DB
    V1 --> S[Blob Storage]
    V2 --> S
```

Scale rule (Sprint 3): min 2 instances, scale out on CPU over 70 percent,
max capped for cost. No session state on VMs (JWT). AWS mapping if asked:
VM Scale Set = EC2 Auto Scaling Group, Load Balancer = ALB,
Azure DB for PostgreSQL = RDS, Blob = S3.
