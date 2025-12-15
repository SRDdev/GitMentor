# RepoRanger System Design Specification

## 🤠 Project Specification: RepoRanger
An Autonomous, Multi-Agent DevOps System built with LangGraph.

### 1. Core Philosophy
RepoRanger is not a "chat with code" tool. It is an active maintainer. It operates as an autonomous agent swarm that lives inside a repository. It observes changes, audits quality, visualizes architecture, and documents work—acting effectively as a "Senior Engineer in a Box."

It solves the problem of "Rot & Drift": Documentation drifting from code, architecture becoming spaghetti, and technical debt accumulating unnoticed.

### 2. Architecture & Stack
- **Orchestrator:** LangGraph (Stateful, cyclic multi-agent workflows)
- **Memory:** Reference-based State. Large objects (diffs, diagrams) are stored as Artifacts (files) on disk to keep the LLM context window light.
- **Intelligence:** Hybrid
  - *Generative:* Gemini 1.5 Pro / GPT-4o (for reasoning/writing)
  - *Deterministic:* Python ast module (for 100% accurate metrics)
- **Infrastructure:** Python 3.12+, Poetry, GitPython

### 3. The Agent Swarm (Skills)
RepoRanger is composed of 4 specialized agents that pass a shared state ("The Clipboard") between them.

#### 🏛️ Agent 1: The Visual Architect
- **Role:** System Cartographer.
- **Trigger:** Runs on PRs or scheduled audits.
- **Capabilities:**
  - Dynamic Dependency Mapping: Scans the entire codebase to map how modules import each other.
  - Complexity Heatmaps: Visualizes which parts of the system are "hot spots" (high cyclomatic complexity) using color-coded graphs.
- **Output:** Generates live Mermaid.js charts (.mmd) that update automatically as code changes.

#### 🛡️ Agent 2: The Code Steward
- **Role:** Senior Code Reviewer & Quality Gatekeeper.
- **Trigger:** Runs after the Architect.
- **Capabilities:**
  - Incremental Auditing: Identifies only changed files to save cost/time.
  - Static Analysis: Uses AST to measure Cyclomatic Complexity, Nesting Depth, and Class Cohesion.
  - Dead Code Detection: Identifies unused imports and unreachable logic.
  - Auto-Refactoring: If a function breaches a threshold (e.g., complexity > 10), it autonomously drafts a refactored version using the LLM.

#### ⚔️ Agent 3: The Git Tactician
- **Role:** Operations & Execution.
- **Trigger:** Runs if the Steward proposes changes.
- **Capabilities:**
  - Branch Management: Creates isolated feature branches (e.g., `reporanger/refactor-auth-module`) for proposed fixes.
  - Safe Commits: Commits the Refactor Plans or Documentation to the repo so a human can review them.
  - **Future Scope:** Intelligent cherry-picking and merge conflict resolution.

#### ✍️ Agent 4: The Contextual Scribe
- **Role:** Technical Writer.
- **Trigger:** Runs at the end of the workflow.
- **Capabilities:**
  - Intent Recognition: Reads the git diff to understand why a change happened, not just what changed.
  - PR Generation: Writes professional Pull Request descriptions with sections for "Summary," "Technical Details," and "Architectural Impact."
  - Changelog Management: Updates `CHANGELOG.md` following Semantic Versioning.

### 4. The Toolbelt (Capabilities)
The agents rely on robust, custom-written tools to interact with the world.

#### 🔧 Tool A: PythonCodeParser (The Brain)
- **Type:** Deterministic / Static Analysis.
- **Features:**
  - AST Traversal: Parses Python Abstract Syntax Trees to understand code structure without running it.
  - Import Resolution: Mathematically resolves relative (from `..utils`) and absolute imports to build a perfect dependency graph.
  - Metric Calculation: Calculates Cyclomatic Complexity, Nesting Depth, and Method Counts per class.

#### 🔧 Tool B: GitOps (The Hands)
- **Type:** Wrapper around GitPython.
- **Features:**
  - Safely handles branch switching, staging, committing, and reading diffs.
  - Provides "Name Only" diffs to help agents decide what to scan.

#### 🔧 Tool C: MermaidGenerator (The Artist)
- **Type:** Visualization Engine.
- **Features:**
  - Translates the raw data from PythonCodeParser into valid Mermaid.js syntax.
  - Supports Flowcharts (dependencies) and Class Diagrams (inheritance).

### 5. The Workflow (The Graph)
The current v1 implementation follows a linear enhancement pipeline:

```
START

Architect: "I see the whole system. Here is the new map." -> Saves Diagram Artifact.
Steward: "I see you changed auth.py. It is too complex. Here is a fix." -> Saves Refactor Plan Artifact.
Tactician: "I see a fix plan. I am creating a new branch and saving the plan there." -> Performs Git Action.
Scribe: "I see what everyone did. I am writing the PR description now." -> Saves Docs Artifact.

END
```
