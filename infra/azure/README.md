# Azure deployment — templates only, NOT provisioned (Sprint 3)

`main.bicep` describes the target architecture from docs/architecture.md:
VM Scale Set (min 2, rolling upgrade = rollback by previous image),
Load Balancer (port 80 -> 8000), Azure Database for PostgreSQL 16,
Blob Storage (host photos), Key Vault (all secrets), Application Insights
(error rate + LB health alerts, US32).

**Do NOT run this without Vin's explicit approval** — it creates paid
Azure resources and a cloud account/billing relationship. No Azure
account, subscription, or credential was created for this project in
this repo, and no `az login` / `az deployment` step runs in CI.

To deploy (with approval, on a machine with Azure CLI + a subscription):
```bash
az group create --name staynest-rg --location westus2
az deployment group create --resource-group staynest-rg --template-file infra/azure/main.bicep --parameters adminPassword='<from Key Vault, never committed>'
# then: run backend/db/migrations/001_init.sql against the Postgres server,
# set STAYNEST_DB_URL on the VMSS instances, and run the acceptance script
# in docs/acceptance-full.md against the LB IP.
```
Rollback: redeploy the previous VMSS image / previous frontend build
(see docs/feature-breakdown.md, Definition of Done). Health check after
every deploy: `GET /health` on the LB IP must return `{"status":"ok"}`.

Local equivalent (verified, no cloud): `docker compose up --build`
gives API + Postgres + web on localhost — see RUNNING.md Option B.
The multi-instance race note in scripts/load_test.py applies to VMSS:
with 2+ instances, the overlap guard must move to a DB transaction /
unique constraint, not the in-memory store.
