# Contributing to DecisionLens

Thank you for your interest in contributing to DecisionLens! We are committed to building a world-class enterprise decision intelligence platform.

---

## 1. Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20.x+ (LTS)
- Git

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/AnzarKhan855/decisionlens-enterprise-analytics.git
cd decisionlens-enterprise-analytics

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt

# Run backend API
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 2. Coding Standards & Conventions

### Python Backend
- Target Python 3.12+.
- Follow PEP 8 and use `ruff check backend/app`.
- Type annotations are mandatory for all public functions and classes.
- Ensure all database queries respect workspace scoping (`workspace_id`).
- Endpoints must declare explicit authentication and RBAC dependencies.

### TypeScript / Next.js Frontend
- Strictly adhere to TypeScript strict mode. Verify with `npx tsc --noEmit`.
- Use functional React components with hooks.
- Semantic HTML and WCAG 2.1 AA accessibility are required (single H1, aria attributes, focus states).
- Optimize bundle size using `next/dynamic` for heavy client-only packages.

---

## 3. Testing Requirements

All contributions must include appropriate automated tests:
```bash
# Run backend tests
pytest backend/tests/

# Run frontend build check
cd frontend && npm run build
```

---

## 4. Pull Request Process
1. Create a feature branch: `git checkout -b feature/your-feature-name`.
2. Commit changes with clear, semantic commit messages: `git commit -m "feat(analytics): add quantile trend analysis"`.
3. Push branch and open a Pull Request using the PR template.
4. Ensure CI checks pass. All PRs require at least one code owner review.
