# src/agents/scribe.py - PROFESSIONAL VERSION
import os
import textwrap
import re
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import RepoState
from src.tools.gitops import GitOps
from src.utils.llm import get_llm
from src.utils.workspace import save_artifact
from src.utils.config import cfg
from rich.console import Console

console = Console()

def scribe_node(state: RepoState) -> RepoState:
    """
    The Contextual Scribe generates:
    1. Commit messages (if in commit mode)
    2. System Documentation (if in docs mode)
    3. PR documentation (if in pr or full mode)
    """
    console.print("[bold blue]--- Scribe: Drafting Documentation ---[/bold blue]")
    
    repo_path = state.get("repo_path", cfg.get("paths.repo_root"))
    target_branch = state.get("target_branch", "main")
    mode = state.get("mode", "pr")
    
    git_ops = GitOps(repo_path)
    artifacts = []
    
    if mode == "commit":
        artifacts = _generate_commit_message(git_ops, state)
    elif mode == "docs":
        artifacts = _generate_system_documentation(git_ops, state)
    elif mode == "pr":
        artifacts = _generate_pr_documentation(git_ops, state, target_branch)
    else:
        console.print(f"[red]Error:[/red] Unknown mode '{mode}'.")
        return state
        
    console.print("[bold blue]--- Scribe: Documentation Complete ---[/bold blue]\n")
    
    return {
        "artifacts": artifacts,
        "messages": [HumanMessage(
            content=f"Scribe generated {len(artifacts)} documentation artifact(s)"
        )]
    }


# ============================================================================
# SYSTEM DOCUMENTATION GENERATION
# ============================================================================

def _generate_system_documentation(git_ops: GitOps, state: RepoState) -> list:
    """Generates comprehensive technical documentation for the entire codebase."""
    console.print("    [yellow]Mode: System Documentation Generation[/yellow]")
    
    from src.tools.parser import PythonCodeParser
    from src.tools.diagram import MermaidGenerator
    
    repo_path = state.get("repo_path", os.getcwd())
    parser = PythonCodeParser(repo_path)
    architect = MermaidGenerator(parser)
    
    py_files = git_ops.repo.git.ls_files("*.py").splitlines()
    console.print(f"    Analyzing {len(py_files)} modules for system overview...")
    
    dep_graph = architect.generate_architecture_map(py_files)
    complexity_map = architect.generate_complexity_heatmap()
    
    detailed_context = ""
    for file_path in py_files[:15]: 
        try:
            analysis = parser.analyze_file(file_path)
            if analysis.classes or analysis.functions:
                detailed_context += f"\n### File: {file_path}\n"
                for cls in analysis.classes:
                    methods_list = ", ".join([m for m in cls.methods])
                    detailed_context += f"- Class: {cls.name} (Methods: {methods_list})\n"
                for func in analysis.functions:
                    detailed_context += f"- Function: {func.name}\n"
        except Exception:
            continue

    llm = get_llm("creative")
    prompt = textwrap.dedent(f"""
        You are a Principal Software Architect. Your goal is to write a "System Blueprint" document.
        
        Analyze the following technical context:
        {detailed_context}
        
        Requirements:
        1. Executive Summary: Explain the "Why" behind this system.
        2. Component Analysis: Describe the interaction between high-level modules.
        3. Implementation Detail: Summarize the logic found in key files.
        4. Operational Flow: How does data move through this system?
        
        Tone: Highly technical, objective, and authoritative.
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are a Technical Lead writing high-level system documentation."),
        HumanMessage(content=prompt)
    ])
    
    full_docs = f"# System Documentation\n\n{response.content}\n\n"
    
    if dep_graph:
        full_docs += f"## System Architecture Map\n```mermaid\n{dep_graph}\n```\n\n"
    
    if complexity_map:
        full_docs += f"## Complexity and Tech Debt Heatmap\n```mermaid\n{complexity_map}\n```\n"
    
    doc_path = save_artifact(full_docs, "md", prefix="documentation")
    
    try:
        with open("CODE_DOCS.md", "w") as f:
            f.write(full_docs)
        console.print("    [green]Success:[/green] Saved to CODE_DOCS.md")
    except Exception as e:
        console.print(f"    [red]Warning:[/red] Could not save to root: {e}")
    
    return [{
        "id": "system_docs",
        "type": "markdown_doc",
        "file_path": doc_path,
        "description": "System-wide technical documentation",
        "created_by": "scribe"
    }]


# ============================================================================
# COMMIT MESSAGE GENERATION
# ============================================================================

def _generate_commit_message(git_ops: GitOps, state: RepoState) -> list:
    """Generate commit message for staged changes"""
    console.print("    [yellow]Mode: Commit Message Generation[/yellow]")
    
    if not git_ops.has_staged_changes():
        console.print("    [red]Error:[/red] No staged changes found. Use 'git add <files>' first.")
        return []
    
    diff = git_ops.get_staged_diff()
    if not diff:
        return []
    
    try:
        staged_files = git_ops.repo.git.diff("--cached", name_only=True).split('\n')
        staged_files = [f.strip() for f in staged_files if f.strip()]
        console.print(f"    Analyzing {len(staged_files)} staged file(s)")
    except Exception:
        staged_files = []
    
    user_intent = state.get("commit_intent", "General improvements")
    code_issues = state.get("code_issues", [])
    
    console.print("    Generating commit message with AI...")
    
    try:
        commit_msg = _generate_commit_with_llm(
            diff=diff,
            files=staged_files,
            user_intent=user_intent,
            code_issues=code_issues
        )
        
        commit_path = save_artifact(commit_msg, "txt", prefix="commit_message")
        with open("COMMIT_MESSAGE.txt", "w") as f:
            f.write(commit_msg)
        console.print("    [green]Success:[/green] Saved to COMMIT_MESSAGE.txt")
        
        return [{
            "id": "commit_message",
            "type": "commit_msg",
            "file_path": commit_path,
            "description": "Generated commit message",
            "created_by": "scribe"
        }]
    except Exception as e:
        console.print(f"    [red]Error:[/red] {e}")
        return []

def _generate_commit_with_llm(diff: str, files: list, user_intent: str, code_issues: list) -> str:
    llm = get_llm("creative")

    diff_snippet = diff[:3000] + "\n... [truncated]" if len(diff) > 3000 else diff

    issues_context = ""
    if code_issues:
        critical = len([i for i in code_issues if i.get("severity") == "critical"])
        warnings = len([i for i in code_issues if i.get("severity") == "warning"])
        issues_context = (
            f"\nCode Quality Context:\n"
            f"- Critical issues addressed: {critical}\n"
            f"- Warnings addressed: {warnings}\n"
        )

    prompt = textwrap.dedent(f"""
    You are a senior software engineer writing a high-quality Conventional Commit message.

    AVAILABLE CONTEXT:
    Developer Intent (may be incomplete or informal):
    {user_intent}

    Changed Files (use to infer scope, not to list verbatim):
    {', '.join(files[:10])}

    {issues_context}

    Diff Summary (may be truncated):
    {diff_snippet}

    HARD RULES:
    1. Output ONLY the raw commit message text. No markdown, no code blocks.
    2. Follow Conventional Commits strictly: type(scope): subject
    3. Use one of these types only:
    feat, fix, refactor, perf, test, chore, docs, ci, build
    4. Subject line:
    - Imperative mood (e.g., "add", "fix", "remove", "refactor")
    - Max 72 characters
    - Describe the primary change, not the implementation
    5. Scope:
    - Single, concise noun derived from the affected area (e.g., api, auth, config)
    - Omit scope only if it cannot be inferred
    6. Body (optional but preferred if non-trivial):
    - Explain WHAT changed and WHY
    - Mention behavior changes, risk, or compatibility impact if relevant
    - Do NOT describe low-level implementation details
    7. If this change primarily addresses code quality issues, prefer 'fix' or 'refactor' as the type.

    QUALITY BAR:
    - The message should be suitable for changelogs and release notes.
    - Assume this commit will be read months later with no additional context.
    """)

    response = llm.invoke([
        SystemMessage(content="You write precise, conventional, production-quality commit messages."),
        HumanMessage(content=prompt)
    ])

    msg = response.content.strip()

    # Safety cleanup in case the model still emits fences
    msg = re.sub(r'^```[\w]*\n', '', msg)
    msg = re.sub(r'\n```$', '', msg)

    return msg.strip()



# ============================================================================
# README & PR DOCUMENTATION GENERATION
# ============================================================================

def _generate_enhanced_readme(git_ops: GitOps, state: RepoState) -> str:
    """Uses Gemini to rewrite the README based on codebase reality."""
    console.print("    [yellow]Mode: AI README Transformation[/yellow]")
    
    current_readme = ""
    if os.path.exists("README.md"):
        with open("README.md", "r") as f:
            current_readme = f.read()
            
    arch_context = ""
    for art in state.get("artifacts", []):
        if "architecture_overview" in art.get("file_path", ""):
            with open(art["file_path"], "r") as f:
                arch_context = f.read()
            break

    llm = get_llm("creative")
    prompt = textwrap.dedent(f"""
        You are a Principal Developer Advocate. Your task is to transform the project README.md 
        into a world-class documentation hub.
        
        Existing README:
        {current_readme}
        
        Current Architecture Context (Mermaid & Narrative):
        {arch_context}
        
        Recent Code Quality State:
        {state.get('code_issues', [])}
        
        Instructions:
        1. Retain the core mission statement of the project.
        2. Embed the provided Architecture Diagrams into a new "System Vision" section.
        3. Update the feature list based on the new modules detected in the architecture.
        4. Add a "Quality Standard" section summarizing the steward's findings.
        5. DO NOT wrap the entire response in markdown code blocks (e.g., ```markdown).
        6. Return the raw markdown content only.
    """)
    
    response = llm.invoke([
        SystemMessage(content="You are an expert technical documentarian specializing in developer experience (DX)."),
        HumanMessage(content=prompt)
    ])
    
    # Cleaning Logic: Remove any LLM-injected code fences
    clean_content = response.content.strip()
    clean_content = re.sub(r'^```markdown\n', '', clean_content)
    clean_content = re.sub(r'^```\n', '', clean_content)
    clean_content = re.sub(r'\n```$', '', clean_content)
    
    return clean_content

def _generate_pr_documentation(git_ops: GitOps, state: RepoState, target_branch: str) -> list:
    console.print("    [yellow]Mode: PR Documentation Generation[/yellow]")
    
    commits, actual_target = _get_commits_since(git_ops, target_branch)
    if not commits:
        console.print("    [red]Warning:[/red] No commits found to document.")
        return []
    
    commits_data = [_get_commit_details(git_ops, c) for c in commits]
    source_branch = git_ops.get_current_branch()
    
    pr_text = _generate_pr_with_llm(
        commits_data=commits_data,
        source_branch=source_branch,
        target_branch=target_branch,
        code_issues=state.get("code_issues", []),
        artifacts=state.get("artifacts", [])
    )
    
    pr_path = save_artifact(pr_text, "md", prefix="pr_documentation")
    with open("PR_Document.md", "w") as f:
        f.write(pr_text)
    console.print("    [green]Success:[/green] Saved to PR_Document.md")
    
    return [{
        "id": "pr_document",
        "type": "markdown_doc",
        "file_path": pr_path,
        "description": f"PR Documentation ({len(commits)} commits)",
        "created_by": "scribe"
    }]


def _get_commits_since(git_ops: GitOps, base_branch: str):
    try:
        target = base_branch if _branch_exists(git_ops, base_branch) else f"origin/{base_branch}"
        commits = git_ops.repo.git.log(f"{target}..HEAD", pretty="format:%H").splitlines()
        return commits, target
    except Exception:
        return [], base_branch


def _branch_exists(git_ops: GitOps, branch: str) -> bool:
    try:
        git_ops.repo.git.rev_parse("--verify", branch)
        return True
    except Exception:
        return False


def _get_commit_details(git_ops: GitOps, commit_hash: str) -> dict:
    repo = git_ops.repo
    commit = repo.commit(commit_hash)
    stats = repo.git.show("--stat", commit_hash, "--oneline")
    preview = repo.git.show(commit_hash, color="never").split('\n')[5:20]
    
    return {
        "hash": commit.hexsha[:7],
        "author": commit.author.name,
        "date": commit.authored_datetime.strftime("%Y-%m-%d %H:%M"),
        "subject": commit.message.split('\n')[0],
        "stats": stats,
        "preview": '\n'.join(preview)
    }


def _generate_pr_with_llm(commits_data, source_branch, target_branch, code_issues, artifacts):
    llm = get_llm("creative")
    
    commits_text = "\n".join([f"- {c['hash']}: {c['subject']} ({c['author']})" for c in commits_data])
    
    issues_section = ""
    if code_issues:
        critical = len([i for i in code_issues if i.get("severity") == "critical"])
        issues_section = f"\n## Code Quality Audit\nSteward detected {critical} critical quality blockers addressed in this scope."

    prompt = textwrap.dedent(f"""
    You are a Staff Software Engineer. Generate a high-quality, production-ready Pull Request description.

    CONTEXT:
    Path: {source_branch} -> {target_branch}
    Commits:
    {commits_text}
    {issues_section}

    HARD REQUIREMENTS:
    1. Generate a concise, descriptive PR title derived strictly from the commit subjects and overall intent.
    2. Start the response with the PR title on the first line in the format:
    PR: <Generated Title>
    3. Follow immediately with the merge summary on the next line:
    Merging {source_branch} into {target_branch}
    4. Use numbered section headers exactly as shown below.
    5. Use clear, formal, technical language.
    6. Do NOT use emojis.
    7. Do NOT include conversational filler or introductions.
    8. Do NOT wrap the response in markdown code blocks.
    9. Be explicit and concrete; avoid vague or generic statements.

    REQUIRED STRUCTURE AND INTENT:

    1. Overview
    Provide a concise, high-level summary of what this PR delivers.
    - What is being added, changed, or removed
    - Why this change is important or foundational
    - Any notable validation or deployment context, if applicable

    2. Context / Motivation
    Explain why this PR exists.
    Include, where relevant:
    - Business, product, or milestone drivers
    - Technical debt being addressed or legacy components being replaced
    - Limitations of the previous implementation
    - Benefits such as performance, reliability, maintainability, or flexibility

    3. Key Technical Changes
    List the most important technical changes in detail.
    - Architectural or structural changes
    - Configuration, dependency, or interface updates
    - Behavioral changes or logic refinements
    - Include concrete examples or parameter changes when relevant

    4. Architecture / Implementation Notes
    Describe any meaningful design or implementation decisions.
    - New patterns or paradigms introduced
    - Rationale for major refactors or dependency changes
    - How this impacts scalability, portability, or maintainability

    5. Impact / Risk Assessment
    Analyze the impact and risks of this change.

    Systemic Impact:
    - Which systems, modules, or workflows are affected
    - Whether partial rollout is safe or unsafe

    Risks:
    For each risk, include:
    - Risk name and severity (Low / Medium / High)
    - Description
    - Mitigation strategy

    Rollback Plan:
    Provide clear, actionable rollback steps.

    6. Testing & Validation
    Describe how the changes were verified.
    - Environments used
    - Manual and/or automated testing performed
    - Edge cases or failure scenarios validated
    - Performance or regression checks, if applicable

    7. Next Steps / Recommendations
    Outline follow-up actions enabled or required by this PR.
    - Immediate next steps
    - Future improvements or automation opportunities
    - Post-deployment monitoring or validation recommendations

    Contributor:
    Derive from commit authors. If multiple authors are present, list the primary contributor or state "Multiple contributors".

    QUALITY BAR:
    - This PR description should stand alone as long-term documentation.
    - Assume future readers will not have additional context.
    """)

    
    response = llm.invoke([
        SystemMessage(content="You are a senior technical writer. You provide raw markdown output only. No conversational filler. No emojis."),
        HumanMessage(content=prompt)
    ])
    
    # CHATTER FILTER: Ensure we start at the first markdown header
    clean_content = response.content.strip()
    
    # 1. Strip everything before the first header
    if "##" in clean_content:
        clean_content = clean_content[clean_content.find("##"):]
        
    # 2. Strip potential markdown code fences
    clean_content = re.sub(r'^```markdown\n', '', clean_content)
    clean_content = re.sub(r'^```\n', '', clean_content)
    clean_content = re.sub(r'\n```$', '', clean_content)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = (
        f"# Pull Request Documentation\n\n"
        f"**Generated:** {now}\n"
        f"**Source:** {source_branch} -> **Target:** {target_branch}\n\n"
        f"---\n\n"
    )
    
    return header + clean_content