# RepoRanger Setup Guide

RepoRanger is an autonomous multi-agent system designed to act as your codebase steward. This guide will walk you through the simplest path to getting it running locally and in your GitHub CI/CD pipeline.

---

### Prerequisites
* **Python 3.10+**
* **Git** installed on your local machine.
* **Google Gemini API Key**: Obtain one from the [Google AI Studio](https://aistudio.google.com/).
* **GitHub CLI (Optional)**: Recommended for automated PR creation.

---

### 1. Local Setup
Follow these steps to get RepoRanger running on your development machine in under 5 minutes.

**Step 1: Clone and Enter the Repository**

```bash
git clone https://github.com/SRDdev/RepoRanger.git
cd RepoRanger

```

**Step 2: Install Dependencies**
We use `pip` to install the project and its requirements (LangGraph, LangChain, Rich, etc.).

```bash
python -m pip install --upgrade pip
pip install .

```

**Step 3: Configure Environment Variables**
Create a `.env` file in the root directory to store your API key safely.

```bash
echo "GOOGLE_API_KEY=your_actual_key_here" > .env

```

**Step 4: Verify Installation**
Run the help command to ensure the CLI is working.

```bash
python main.py --help

```

---

### 2. Basic Usage
RepoRanger operates in several modes. Here are the most common commands:

| Command | Purpose |
| --- | --- |
| `python main.py branch --intent "Add user login"` | Creates a semantic branch name based on your goal. |
| `python main.py --mode commit` | Analyzes staged changes and writes a professional commit message. |
| `python main.py --mode full` | Runs a complete audit, updates README diagrams, and prepares a PR doc. |

---

### 3. Setting Up GitHub Actions
Integrating RepoRanger into your repository allows it to automatically analyze every Pull Request and post a detailed technical report as a comment.

**Step 1: Add the Secret to GitHub**

1. Navigate to your repository on GitHub.
2. Go to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. **Name**: `GOOGLE_API_KEY`
5. **Value**: Your Google Gemini API Key.

**Step 2: Ensure the Workflow File Exists**
Make sure the following file is present at `.github/workflows/reporanger-analysis.yml`:

```yaml
name: RepoRanger PR Analysis
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install .
      - name: Run Analysis
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          GITHUB_HEAD_REF: ${{ github.head_ref }}
        run: python main.py --mode pr --target-branch ${{ github.base_ref }}
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            if (fs.existsSync('PR_Document.md')) {
              const body = fs.readFileSync('PR_Document.md', 'utf8');
              github.rest.issues.createComment({
                issue_number: context.issue.number,
                owner: context.repo.owner,
                repo: context.repo.repo,
                body: body
              });
            }

```

---

### 4. Professional README 
SynchronizationTo keep your `README.md` updated with the latest AI-generated architecture maps and quality scores, ensure your `README.md` has these markers:

```markdown
# My Awesome Project


```

Whenever you run `python main.py --mode full`, RepoRanger will rewrite the content between those markers with a fresh **System Vision** and **Quality Assessment**.

---

### Troubleshooting
* **"No diagram generated"**: Ensure you have Python files (`.py`) in your repository. RepoRanger requires source code to build dependency maps.
* **Detached HEAD Error**: This is common in CI. Ensure your `src/tools/gitops.py` uses the updated `try/except` block to fallback to environment variables for the branch name.

Would you like me to help you write a **Contributing.md** file that explains the RepoRanger workflow to other developers on your team?