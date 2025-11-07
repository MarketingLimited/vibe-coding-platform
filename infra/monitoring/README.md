# Monitoring Stack

This optional stack deploys Prometheus and Grafana for the Vibe Coding platform. It
scrapes the API metrics endpoint (`/metrics`) and includes a pre-configured data
source for Grafana. Start it with:

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

Prometheus listens on `9090` and Grafana on `3000` (default credentials `admin` /
`admin`).
