#!/usr/bin/env python3
"""
GitMentor CLI - Extended with History, Explain, and Search features
"""
import click
import subprocess
import os
from rich.console import Console
from rich.panel import Panel

console = Console()

@click.group()
def cli():
    """🚀 GitMentor - Your Autonomous Code Steward"""
    pass


# ============================================================================
# ORIGINAL COMMANDS
# ============================================================================

@cli.command()
@click.option('--intent', '-m', help='Commit intent/message')
def commit(intent):
    """Generate commit message for staged changes"""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--quiet'],
        capture_output=True
    )
    
    if result.returncode == 0:
        console.print("[red]❌ No staged changes found[/red]")
        console.print("[yellow]Hint: Use 'git add <files>' first[/yellow]")
        return
    
    cmd = ['python', 'main.py', '--mode', 'commit']
    if intent:
        cmd.extend(['--commit-intent', intent])
    
    subprocess.run(cmd)


@cli.command()
@click.option('--target', '-t', default='main', help='Target branch')
def pr(target):
    """Generate PR documentation (Steward -> Scribe)"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'pr',
        '--target-branch', target
    ])


@cli.command()
def docs():
    """Generate full system documentation (CODE_DOCS.md)"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'docs'
    ])


@cli.command()
@click.option('--target', '-t', default='main', help='Target branch')
def audit(target):
    """Run code quality audit only (Steward)"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'audit',
        '--target-branch', target
    ])


@cli.command()
@click.option('--target', '-t', default='main', help='Target branch')
def full(target):
    """Run full analysis swarm (Architect -> Steward -> Tactician -> Scribe)"""
    subprocess.run([
        'python', 'main.py',
        '--mode', 'full',
        '--target-branch', target
    ])


@cli.command()
@click.option('--intent', '-m', prompt='What do you want to work on?', help='Branch purpose/intent')
@click.option('--type', '-t', type=click.Choice([
    'feat', 'fix', 'hotfix', 'refactor', 'perf', 
    'docs', 'test', 'chore', 'style', 'ci', 'build'
]), help='Branch type (auto-detected if not specified)')
@click.option('--no-commit', is_flag=True, help='Skip initial commit')
def branch(intent, type, no_commit):
    """Create a smart branch with AI-generated name"""
    from src.tools.gitops import GitOps
    from src.tools.branch_manager import BranchManager
    
    console.print(Panel(
        "🌿 [bold green]Smart Branch Creator[/bold green]",
        border_style="green"
    ))
    
    git_ops = GitOps(os.getcwd())
    manager = BranchManager(git_ops)
    
    console.print(f"\n💭 Intent: [cyan]{intent}[/cyan]")
    
    if type:
        console.print(f"🏷️  Type: [yellow]{type}[/yellow] (specified)")
    else:
        console.print("🤖 Detecting branch type...")
    
    with console.status("[bold yellow]Generating branch name...[/bold yellow]"):
        try:
            branch_name, branch_type = manager.create_smart_branch(
                user_intent=intent,
                auto_detect_type=(type is None),
                suggested_type=type,
                create_initial_commit=(not no_commit)
            )
            
            console.print(Panel(
                f"[bold green]✅ Branch created and checked out![/bold green]\n\n"
                f"🌿 Branch: [cyan]{branch_name}[/cyan]\n"
                f"🏷️  Type: [yellow]{branch_type}[/yellow]\n\n"
                f"Usage:\n"
                f"  [dim]git add .[/dim]\n"
                f"  [dim]gm commit[/dim]",
                border_style="green",
                title="🎉 Success"
            ))
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")


# ============================================================================
# NEW FEATURE COMMANDS
# ============================================================================

@cli.command(name='search-history')
@click.argument('query', nargs=-1, required=True)
def search_history(query):
    """
    Search git history for variable changes, function modifications, etc.
    
    Examples:
        gm search-history trajectory_angle_c in normal_inference.py
        gm search-history update_config
    """
    from src.tools.gitops import GitOps
    from src.tools.history import HistoryAnalyzer
    from rich.table import Table
    from rich.syntax import Syntax
    
    query_text = ' '.join(query)
    
    console.print(Panel(
        f"[bold cyan]Searching Git History[/bold cyan]\n"
        f"Query: [yellow]{query_text}[/yellow]",
        border_style="blue"
    ))
    
    # Parse query: "variable_name in file.py" or just "variable_name"
    parts = query_text.split(' in ')
    search_term = parts[0].strip()
    file_path = parts[1].strip() if len(parts) > 1 else None
    
    try:
        git_ops = GitOps(os.getcwd())
        analyzer = HistoryAnalyzer(git_ops)
        
        with console.status(f"[dim]Analyzing history for '{search_term}'...", spinner="dots"):
            changes = analyzer.track_variable_changes(search_term, file_path, max_commits=100)
            current_value = None
            if file_path:
                current_value = analyzer.get_current_value(search_term, file_path)
        
        if not changes:
            console.print(f"\n[yellow]No history found for '{search_term}'[/yellow]")
            
            console.print(f"\n[dim]Searching for current definition...[/dim]")
            results = analyzer.search_files_for_pattern(search_term)
            
            if results:
                console.print(f"\n[green]Found in {len(results)} location(s):[/green]")
                for result in results[:5]:
                    console.print(f"  • {result['file']}:{result['line_number']}")
            else:
                console.print(f"[red]'{search_term}' not found in codebase[/red]")
            return
        
        console.print(f"\n[bold green]Found {len(changes)} change(s)[/bold green]\n")
        
        # Create timeline table
        table = Table(title=f"History of '{search_term}'", show_header=True, header_style="bold cyan")
        table.add_column("Date", style="dim", width=20)
        table.add_column("Commit", style="yellow", width=10)
        table.add_column("Author", style="green", width=20)
        table.add_column("Value", style="cyan")
        table.add_column("File", style="dim")
        
        changes.sort(key=lambda x: x['commit_date'])
        
        for change in changes[-10:]:
            table.add_row(
                change['commit_date'].strftime("%Y-%m-%d %H:%M"),
                change['commit_hash'],
                change['author'],
                change['value'][:50] + "..." if len(change['value']) > 50 else change['value'],
                change['file']
            )
        
        console.print(table)
        
        # Show most recent change
        latest = changes[-1]
        console.print(Panel(
            f"[bold]Last Modified:[/bold]\n"
            f"Commit: [yellow]{latest['commit_hash']}[/yellow]\n"
            f"Date: [cyan]{latest['commit_date'].strftime('%Y-%m-%d %H:%M')}[/cyan]\n"
            f"Author: [green]{latest['author']}[/green]\n"
            f"Message: [dim]{latest['message']}[/dim]\n\n"
            f"[bold]Previous Value:[/bold]\n"
            f"[white]{latest['value']}[/white]",
            title="Latest Change",
            border_style="green"
        ))
        
        if current_value:
            console.print(Panel(
                f"[bold white]{current_value}[/bold white]",
                title="Current Value",
                border_style="blue"
            ))
        
        commit_details = analyzer.get_commit_details(latest['commit_hash'])
        if commit_details:
            console.print(Panel(
                f"[bold]Full Commit Message:[/bold]\n"
                f"{commit_details['message']}\n\n"
                f"Files changed: {len(commit_details['files_changed'])}\n"
                f"[green]+{commit_details['insertions']}[/green] [red]-{commit_details['deletions']}[/red]",
                title=f"Commit {commit_details['hash']}",
                border_style="dim"
            ))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument('name')
@click.option('--level', '-l', 
              type=click.Choice(['beginner', 'medium', 'hard']), 
              default='medium',
              help='Explanation complexity level')
@click.option('--file', '-f', help='Specific file to search in')
@click.option('--type', '-t', 
              type=click.Choice(['function', 'class', 'auto']),
              default='auto',
              help='Whether to explain a function or class')
def explain(name, level, file, type):
    """
    Get detailed AI-powered explanation of a function or class.
    
    Examples:
        gm explain analyze_file --level beginner
        gm explain PythonCodeParser --type class --level hard
        gm explain commit_changes -f src/tools/gitops.py
    """
    from src.agents.explainer import CodeExplainer
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    
    console.print(Panel(
        f"[bold cyan]Code Explainer[/bold cyan]\n"
        f"Target: [yellow]{name}[/yellow]\n"
        f"Level: [green]{level}[/green]",
        border_style="blue"
    ))
    
    try:
        explainer = CodeExplainer(os.getcwd())
        
        with console.status(f"[dim]Analyzing '{name}'...", spinner="dots"):
            if type == 'auto':
                result = explainer.explain_function(name, level, file)
                if not result['success']:
                    result = explainer.explain_class(name, level, file)
            elif type == 'function':
                result = explainer.explain_function(name, level, file)
            else:
                result = explainer.explain_class(name, level, file)
        
        if not result['success']:
            console.print(f"\n[red]{result['error']}[/red]")
            return
        
        # Display location
        console.print(Panel(
            f"[bold]Location:[/bold] [cyan]{result['file']}:{result['line']}[/cyan]\n"
            f"[bold]Expertise Level:[/bold] [yellow]{level.capitalize()}[/yellow]",
            border_style="dim"
        ))
        
        # Display source code
        console.print("\n[bold]Source Code:[/bold]")
        syntax = Syntax(result['source_code'], "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, border_style="dim"))
        
        # Display explanation
        console.print("\n[bold cyan]Explanation:[/bold cyan]")
        md = Markdown(result['explanation'])
        console.print(Panel(md, border_style="cyan", padding=(1, 2)))
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.argument('query', nargs=-1, required=True)
def where(query):
    """
    Find where specific functions, classes, or files are located.
    Uses AI to understand natural language queries.
    
    Examples:
        gm where function that generates flash_payload.json
        gm where class handles git operations
        gm where code for branch creation
    """
    from src.tools.gitops import GitOps
    from src.tools.history import HistoryAnalyzer
    from src.utils.llm import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    from rich.table import Table
    import textwrap
    import json
    import re
    
    query_text = ' '.join(query)
    
    console.print(Panel(
        f"[bold cyan]Code Location Finder[/bold cyan]\n"
        f"Query: [yellow]{query_text}[/yellow]",
        border_style="blue"
    ))
    
    try:
        git_ops = GitOps(os.getcwd())
        analyzer = HistoryAnalyzer(git_ops)
        llm = get_llm("default")
        
        console.print("\n[dim]Analyzing query...[/dim]")
        
        extraction_prompt = textwrap.dedent(f"""
        You are a code search assistant. Extract key search terms from the user's query.
        
        User Query: "{query_text}"
        
        Extract:
        1. Specific identifiers (function names, class names, variable names)
        2. File patterns (e.g., "flash_payload.json")
        3. Functional keywords (e.g., "generates", "handles", "creates")
        
        Return a JSON object with:
        {{
            "identifiers": ["list", "of", "names"],
            "file_patterns": ["file.json", "*.py"],
            "keywords": ["generate", "create", "handle"]
        }}
        
        Return ONLY the JSON, no explanation.
        """)
        
        response = llm.invoke([
            SystemMessage(content="You are a code search assistant."),
            HumanMessage(content=extraction_prompt)
        ])
        
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            search_params = json.loads(json_match.group(0))
        else:
            search_params = {
                "identifiers": [query_text],
                "file_patterns": [],
                "keywords": []
            }
        
        console.print(f"[dim]Search parameters: {search_params}[/dim]\n")
        
        all_results = []
        
        with console.status("[dim]Searching codebase...", spinner="dots"):
            for identifier in search_params.get('identifiers', []):
                func_results = analyzer.find_function_definition(identifier)
                for result in func_results:
                    result['type'] = 'function'
                    result['identifier'] = identifier
                all_results.extend(func_results)
                
                class_results = analyzer.find_class_definition(identifier)
                for result in class_results:
                    result['type'] = 'class'
                    result['identifier'] = identifier
                all_results.extend(class_results)
            
            for pattern in search_params.get('file_patterns', []):
                file_results = analyzer.search_files_for_pattern(pattern)
                for result in file_results:
                    result['type'] = 'file_reference'
                    result['identifier'] = pattern
                all_results.extend(file_results)
            
            if not all_results:
                for keyword in search_params.get('keywords', []):
                    keyword_results = analyzer.search_files_for_pattern(keyword)
                    for result in keyword_results[:10]:
                        result['type'] = 'keyword_match'
                        result['identifier'] = keyword
                    all_results.extend(keyword_results[:10])
        
        if not all_results:
            console.print(f"\n[yellow]No results found for: {query_text}[/yellow]")
            console.print("[dim]Try being more specific or checking spelling[/dim]")
            return
        
        console.print(f"\n[green]Found {len(all_results)} result(s)[/green]")
        
        table = Table(title="Search Results", show_header=True, header_style="bold cyan")
        table.add_column("Type", style="yellow", width=12)
        table.add_column("Location", style="cyan")
        table.add_column("Line", style="dim", width=6)
        table.add_column("Match", style="white")
        
        for result in all_results[:15]:
            table.add_row(
                result.get('type', 'unknown'),
                result['file'],
                str(result['line_number']),
                result['matched_line'][:60] + "..." if len(result['matched_line']) > 60 else result['matched_line']
            )
        
        console.print(table)
        
        if all_results:
            top_result = all_results[0]
            console.print(Panel(
                f"[bold]Most Relevant Match:[/bold]\n\n"
                f"[bold cyan]Location:[/bold cyan] {top_result['file']}:{top_result['line_number']}\n"
                f"[bold cyan]Type:[/bold cyan] {top_result.get('type', 'unknown')}\n\n"
                f"[bold]Context:[/bold]\n"
                f"[white]{top_result.get('context', top_result['matched_line'])}[/white]",
                title="Top Result",
                border_style="green"
            ))
            
            console.print("\n[dim]Tip: Use 'gm explain <name>' for detailed explanation[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    cli()