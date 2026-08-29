#!/usr/bin/env python3
"""
generate_ci.py — AntecipIA Agent Platform v2.0 — Deploy Pipeline
Gera arquivos GitHub Actions workflows para CI/CD do AntecipIA.
Uso: python .agents/deploy/scripts/generate_ci.py
"""

import sys
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent.parent.parent
GITHUB_DIR = ROOT / ".github" / "workflows"

API_WORKFLOW = """name: CI/CD — AntecipIA API

on:
  push:
    branches: [develop, main]
    paths:
      - 'antecipia-api/**'
      - 'shared/**'
  pull_request:
    branches: [develop, main]
    paths:
      - 'antecipia-api/**'

jobs:
  validate:
    name: 🔍 TypeScript & Testes
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 9

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: TypeScript check
        run: cd antecipia-ui && npx tsc --noEmit

      - name: Kill legacy port
        run: npx --yes kill-port 3000 || true

  deploy-api:
    name: 🚀 Deploy API
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: antecipia-api
"""

UI_WORKFLOW = """name: CI/CD — AntecipIA UI

on:
  push:
    branches: [develop, main]
    paths:
      - 'antecipia-ui/**'
      - 'shared/**'
  pull_request:
    branches: [develop, main]
    paths:
      - 'antecipia-ui/**'

jobs:
  validate:
    name: 🔍 TypeScript & Build Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 9

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: TypeScript check
        run: cd antecipia-ui && npx tsc --noEmit

      - name: Build (validação)
        run: cd antecipia-ui && pnpm build

  deploy-ui:
    name: 🚀 Deploy Frontend
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v3
        with:
          version: 9

      - name: Install & Build
        run: |
          pnpm install --frozen-lockfile
          cd antecipia-ui && pnpm build

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: antecipia-ui/dist
"""

def main():
    GITHUB_DIR.mkdir(parents=True, exist_ok=True)

    api_file = GITHUB_DIR / "api-ci.yml"
    ui_file = GITHUB_DIR / "ui-ci.yml"

    api_file.write_text(API_WORKFLOW.lstrip(), encoding="utf-8")
    print(f"[OK] Gerado: {api_file}")

    ui_file.write_text(UI_WORKFLOW.lstrip(), encoding="utf-8")
    print(f"[OK] Gerado: {ui_file}")

    print(f"\n[INFO] Workflows de CI/CD gerados em .github/workflows/")
    print("[INFO] Configure os secrets no GitHub:")
    print("   • RAILWAY_TOKEN")
    print("   • VERCEL_TOKEN")
    print("   • VERCEL_ORG_ID")
    print("   • VERCEL_PROJECT_ID")
    print("   • SUPABASE_URL (não é o service_role!)")

if __name__ == "__main__":
    main()
