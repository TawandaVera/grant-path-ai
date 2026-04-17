# 🧭 Grant Path AI

**Find grants. Write proposals. Win funding. — Powered by AI, costs nearly nothing.**

[![CI](https://github.com/your-org/grant-path-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/grant-path-ai/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

Grant Path AI helps nonprofits, schools, and small organizations discover grant 
funding and write winning proposals using a hybrid AI architecture that costs 
**95% less** than traditional AI approaches.

---

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Docker)
- A free [Google Gemini API key](https://aistudio.google.com/apikey)

### Quick Start

```bash
# Clone
git clone https://github.com/your-org/grant-path-ai.git
cd grant-path-ai

# Configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Setup & Run
make setup    # Install dependencies
make seed     # Load 500 sample grants
make dev      # Start all services
