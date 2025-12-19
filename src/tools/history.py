"""
src/tools/history.py - Git History Analysis Tool (Enhanced)
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
import os
from git import Repo
from src.tools.gitops import GitOps
from rich.console import Console

console = Console()

class HistoryAnalyzer:
    """
    Analyzes Git history to track changes to specific variables, functions, or files.
    """
    
    def __init__(self, git_ops: GitOps):
        self.git_ops = git_ops
        self.repo = git_ops.repo
    
    def track_variable_changes(
        self, 
        variable_name: str, 
        file_path: Optional[str] = None,
        max_commits: int = 100
    ) -> List[Dict]:
        """
        Track changes to a specific variable across commit history.
        Uses a flexible search to catch assignments, usage, and constants.
        """
        changes = []
        # Flexible pattern: matches the variable name as a whole word
        # This catches 'Z_MIN = 1', 'if x < Z_MIN:', and 'func(Z_MIN)'
        pattern = rf'\b{re.escape(variable_name)}\b'
        
        console.print(f"[dim]🔍 Scanning last {max_commits} commits for '{variable_name}'...[/dim]")
        
        try:
            # Get commit history for specific file or repo
            if file_path:
                commits = list(self.repo.iter_commits(paths=file_path, max_count=max_commits))
                console.print(f"[dim]📁 Filtering by file: {file_path} ({len(commits)} commits found)[/dim]")
            else:
                commits = list(self.repo.iter_commits(max_count=max_commits))

            for commit in commits:
                try:
                    # Get the diff for this commit
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit, create_patch=True)
                    else:
                        diffs = commit.diff(self.repo.tree(), create_patch=True)
                    
                    for diff in diffs:
                        if diff.change_type in ['A', 'M']:
                            file_path_in_commit = diff.b_path
                            
                            # Filter by file path if provided
                            if file_path and os.path.basename(file_path) not in file_path_in_commit:
                                continue

                            if diff.diff:
                                diff_text = diff.diff.decode('utf-8', errors='ignore')
                                
                                for line in diff_text.split('\n'):
                                    # We focus on added lines (+) to track how the value changed/evolved
                                    if line.startswith('+') and not line.startswith('+++'):
                                        if re.search(pattern, line):
                                            # Clean up the line for the 'value' display
                                            # If it's an assignment, we try to extract the right side
                                            assignment_match = re.search(rf'{pattern}\s*=\s*(.+)', line)
                                            display_value = assignment_match.group(1).strip() if assignment_match else line[1:].strip()

                                            changes.append({
                                                'commit_hash': commit.hexsha[:7],
                                                'commit_date': datetime.fromtimestamp(commit.committed_date),
                                                'author': commit.author.name,
                                                'message': commit.message.split('\n')[0],
                                                'file': file_path_in_commit,
                                                'value': display_value,
                                                'diff_line': line.strip()
                                            })
                except Exception as e:
                    continue # Skip problematic commits
            
            console.print(f"[dim]✅ Found {len(changes)} historical references.[/dim]")
            return changes
        
        except Exception as e:
            console.print(f"[red]Error during history analysis: {e}[/red]")
            return []
    
    def get_current_value(self, variable_name: str, file_path: str) -> Optional[str]:
        """
        Get the current state of a variable in a file.
        """
        try:
            full_path = os.path.join(self.repo.working_dir, file_path)
            if not os.path.exists(full_path):
                return None
                
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Try to find the most recent assignment
            pattern = rf'\b{re.escape(variable_name)}\s*=\s*(.+?)(?:\n|$|#)'
            match = re.search(pattern, content)
            
            return match.group(1).strip() if match else "Found in file, but no direct assignment."
        except Exception as e:
            console.print(f"[dim]Could not read current value: {e}[/dim]")
            return None

    def search_files_for_pattern(self, pattern: str, file_extension: str = '.py') -> List[Dict]:
        """Search all tracked files for a specific pattern with logging."""
        results = []
        try:
            files = self.repo.git.ls_files(f'*{file_extension}').split('\n')
            for file_path in files:
                full_path = os.path.join(self.repo.working_dir, file_path)
                if not os.path.isfile(full_path): continue
                
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append({
                                'file': file_path,
                                'line_number': line_num,
                                'matched_line': line.strip()
                            })
        except Exception as e:
            console.print(f"[red]Search error: {e}[/red]")
        return results

    def find_function_definition(self, function_name: str) -> List[Dict]:
        return self.search_files_for_pattern(rf'^\s*def\s+{re.escape(function_name)}\s*\(')

    def find_class_definition(self, class_name: str) -> List[Dict]:
        return self.search_files_for_pattern(rf'^\s*class\s+{re.escape(class_name)}\s*[\(:]')

    def get_commit_details(self, commit_hash: str) -> Optional[Dict]:
        try:
            commit = self.repo.commit(commit_hash)
            return {
                'hash': commit.hexsha[:7],
                'message': commit.message,
                'author': commit.author.name,
                'date': datetime.fromtimestamp(commit.committed_date),
                'files_changed': list(commit.stats.files.keys()),
                'insertions': commit.stats.total['insertions'],
                'deletions': commit.stats.total['deletions']
            }
        except: return None