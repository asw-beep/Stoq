# System Architecture

                    ┌───────────────┐
                    │   Next.js UI  │
                    └───────┬───────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ FastAPI Backend │
                   └───────┬─────────┘
                           │
       ┌───────────────────┼──────────────────┐
       ▼                   ▼                  ▼

 Forecast Module    Sentiment Module   Portfolio Module

       ▼                   ▼                  ▼

               PostgreSQL Database

       ▲
       │

 Yahoo Finance
 News Sources

---

Architecture Style

Modular Monolith

backend/

├── forecast/
├── sentiment/
├── portfolio/
├── market_data/
├── analytics/
├── core/
├── db/
└── api/