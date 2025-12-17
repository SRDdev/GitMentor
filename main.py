# main.py - GitMentor Autonomous Code Steward
import os
import argparse
import subprocess
import json
import re
import textwrap
from dotenv import load_dotenv

from src.graph import app
from src.utils.config import cfg
from src.tools.gitops import GitOps
from src.tools.branch_manager import BranchManager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="GitMentor - Autonomous Code Steward",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gm search-history "db_url" in config.py
  gm explain CodeParser --level beginner
  gm where "logic that handles authentication"
  gm branch -m "Refactor parser logic"
  gm full -m "Major version 1.0 release prep"
  gm commit -m "Fix buffer overflow in auth"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Helper to create consistent parsers for all modes
    def add_standard_subcommand(name, help_text):
        p = subparsers.add_parser(name, help=help_text)
        p.add_argument('--intent', '-m', help='Context or intent for the AI agents')
        p.add_argument("--target-branch", "--target", default="main", help="Base branch for comparison")
        return p

    # --- DEFINE COMMANDS ---
    add_standard_subcommand('full', 'Full analysis and AI README synchronization')
    add_standard_subcommand('audit', 'Deep quality and security audit')
    add_standard_subcommand('docs', 'Generate/update documentation based on code')
    add_standard_subcommand('pr', 'Analyze changes and prepare PR description')
    add_standard_subcommand('commit', 'Generate a Conventional Commit message')

    # --- BRANCH COMMAND ---
    branch_parser = subparsers.add_parser('branch', help='Create semantic branch')
    branch_parser.add_argument('--intent', '-m', required=True, help='Branch purpose/intent')
    branch_parser.add_argument('--type', '-t', choices=[
        'feat', 'fix', 'hotfix', 'refactor', 'perf', 
        'docs', 'test', 'chore', 'style', 'ci', 'build'
    ], help='Override branch type')
    branch_parser.add_argument('--no-commit', action='store_true', help='Skip initial commit')

    # --- SEARCH HISTORY COMMAND ---
    search_parser = subparsers.add_parser('search-history', help='Search git history for variable/logic changes')
    search_parser.add_argument('query', nargs='+', help='Query (e.g., "var_name in file.py")')

    # --- EXPLAIN COMMAND ---
    explain_parser = subparsers.add_parser('explain', help='AI-powered explanation of code blocks')
    explain_parser.add_argument('name', help='Name of function or class')
    explain_parser.add_argument('--level', '-l', choices=['beginner', 'medium', 'hard'], default='medium', help='Explanation complexity')
    explain_parser.add_argument('--file', '-f', help='Specific file path')
    explain_parser.add_argument('--type', '-t', choices=['function', 'class', 'auto'], default='auto')

    # --- WHERE COMMAND ---
    where_parser = subparsers.add_parser('where', help='Find code location using natural language')
    where_parser.add_argument('query', nargs='+', help='Search query')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Header
    console.print(Panel(
        f"[bold blue]{cfg.get('project.name', 'GITMENTOR').upper()}[/bold blue] | {args.command.upper()} ENGINE",
        border_style="blue"
    ))

    # --- EXECUTION ROUTING ---
    
    if args.command == 'branch':
        _handle_branch_creation(args)
        return

    if args.command == 'search-history':
        _execute_search_history(args)
        return

    if args.command == 'explain':
        _execute_explain(args)
        return

    if args.command == 'where':
        _execute_where(args)
        return

    # Initialize Git for remaining commands
    git_ops = GitOps(os.getcwd())
    current_branch = git_ops.get_current_branch()
    target_branch = getattr(args, 'target_branch', 'main')
    user_intent = getattr(args, 'intent', None)

    if args.command == "commit":
        _execute_commit_mode(args)
        return

    _execute_graph_mode(args, current_branch, target_branch, user_intent)


# ========================================================================
# EXECUTION LOGIC
# ========================================================================

def _execute_search_history(args):
    from src.tools.history import HistoryAnalyzer
    query_text = ' '.join(args.query)
    parts = query_text.split(' in ')
    search_term = parts[0].strip()
    file_path = parts[1].strip() if len(parts) > 1 else None
    
    git_ops = GitOps(os.getcwd())
    analyzer = HistoryAnalyzer(git_ops)
    
    with console.status(f"[dim]Analyzing history for '{search_term}'..."):
        changes = analyzer.track_variable_changes(search_term, file_path, max_commits=100)
        current_value = analyzer.get_current_value(search_term, file_path) if file_path else None

    if not changes:
        console.print(f"\n[yellow]No history found for '{search_term}'[/yellow]")
        return

    table = Table(title=f"History of '{search_term}'", show_header=True, header_style="bold cyan")
    table.add_column("Date", style="dim")
    table.add_column("Commit", style="yellow")
    table.add_column("Author", style="green")
    table.add_column("Value", style="cyan")
    
    changes.sort(key=lambda x: x['commit_date'])
    for change in changes[-10:]:
        table.add_row(
            change['commit_date'].strftime("%Y-%m-%d %H:%M"),
            change['commit_hash'],
            change['author'],
            change['value'][:50] + "..." if len(change['value']) > 50 else change['value']
        )
    console.print(table)

def _execute_explain(args):
    from src.agents.explainer import CodeExplainer
    explainer = CodeExplainer(os.getcwd())
    
    with console.status(f"[dim]Analyzing '{args.name}'..."):
        if args.type == 'auto':
            result = explainer.explain_function(args.name, args.level, args.file)
            if not result['success']:
                result = explainer.explain_class(args.name, args.level, args.file)
        elif args.type == 'function':
            result = explainer.explain_function(args.name, args.level, args.file)
        else:
            result = explainer.explain_class(args.name, args.level, args.file)

    if not result['success']:
        console.print(f"\n[red]Error: {result['error']}[/red]")
        return

    syntax = Syntax(result['source_code'], "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Source Code", border_style="dim"))
    console.print(Markdown(result['explanation']))

def _execute_where(args):
    from src.tools.history import HistoryAnalyzer
    from src.utils.llm import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    
    query_text = ' '.join(args.query)
    git_ops = GitOps(os.getcwd())
    analyzer = HistoryAnalyzer(git_ops)
    llm = get_llm("default")
    
    extraction_prompt = textwrap.dedent(f"""
        Extract search terms from: "{query_text}"
        Return ONLY JSON: {{"identifiers": [], "file_patterns": [], "keywords": []}}
    """)
    
    response = llm.invoke([SystemMessage(content="Code search assistant"), HumanMessage(content=extraction_prompt)])
    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
    search_params = json.loads(json_match.group(0)) if json_match else {{"identifiers": [query_text]}}
    
    all_results = []
    with console.status("[dim]Searching..."):
        for iden in search_params.get('identifiers', []):
            all_results.extend(analyzer.find_function_definition(iden))
            all_results.extend(analyzer.find_class_definition(iden))

    if not all_results:
        console.print("[yellow]No matches found.[/yellow]")
        return

    table = Table(title="Search Results")
    table.add_column("Location", style="cyan")
    table.add_column("Line", style="dim")
    table.add_column("Match")
    for res in all_results[:10]:
        table.add_row(res['file'], str(res['line_number']), res['matched_line'][:60])
    console.print(table)

def _execute_graph_mode(args, current_branch, target_branch, user_intent):
    initial_state = {
        "repo_path": os.getcwd(), "target_branch": target_branch, "source_branch": current_branch,
        "mode": args.command, "intent": user_intent, "artifacts": [], "messages": [], "code_issues": []
    }
    console.print(f"\n[bold]STARTING {args.command.upper()} PIPELINE[/bold]\n", style="dim")
    
    final_state = initial_state
    with console.status(f"[dim]Processing {args.command} nodes...", spinner="dots"):
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]
            _render_node_summary(node_name, final_state)
    
    if args.command == "full": _update_readme_with_analysis(final_state)
    if args.command in ["pr", "full"]: _handle_pr_output(final_state, target_branch)
    console.print(f"\n[bold green]{args.command.capitalize()} finished.[/bold green]")

def _execute_commit_mode(args):
    from src.agents.scribe import scribe_node
    intent = getattr(args, 'intent', None) or Prompt.ask("Enter commit intent", default="General improvements")
    state = {"repo_path": os.getcwd(), "mode": "commit", "intent": intent, "artifacts": [], "messages": [], "code_issues": []}
    with console.status("[dim]Generating message..."):
        result = scribe_node(state)
        _handle_commit_output(result)

def _update_readme_with_analysis(state):
    from src.agents.scribe import _generate_enhanced_readme
    git_ops = GitOps(os.getcwd())
    new_content = _generate_enhanced_readme(git_ops, state)
    if new_content:
        with open("README.md", "w") as f: f.write(new_content)
        console.print("    [green]README.md updated.[/green]")

def _render_node_summary(node_name: str, state: dict):
    artifacts = state.get("artifacts", [])
    issues = state.get("code_issues", [])
    content = [f"Artifact: [bold]{a['description']}[/bold] -> [dim]{a['file_path']}[/dim]" for a in artifacts if a.get("created_by") == node_name]
    if node_name == "steward" and issues:
        content.append("[bold red]Audit Findings:[/bold red]")
        content.extend([f"  - {i['file']}: {i['message']}" for i in issues[:3]])
    if content:
        console.print(Panel("\n".join(content), title=f"Agent: {node_name.capitalize()}", border_style="dim"))

def _handle_branch_creation(args):
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    try:
        name, btype = manager.create_smart_branch(user_intent=args.intent, auto_detect_type=(args.type is None), suggested_type=args.type, create_initial_commit=(not args.no_commit))
        console.print(Panel(f"Branch: [cyan]{name}[/cyan]\nType: [yellow]{btype}[/yellow]", title="Success", border_style="green"))
    except Exception as e: console.print(f"[red]Error:[/red] {e}")

def _handle_commit_output(state):
    if any(a.get("type") == "commit_msg" for a in state.get("artifacts", [])):
        console.print(Panel("Apply using: [bold]git commit -F COMMIT_MESSAGE.txt[/bold]", title="Success", border_style="green"))

def _handle_pr_output(state, target_branch):
    git_ops = GitOps(os.getcwd())
    current = git_ops.get_current_branch()
    console.print(Panel(f"gh pr create --base {target_branch} --head {current} --body-file PR_Document.md", title="Deployment", border_style="green"))

if __name__ == "__main__":
    main()