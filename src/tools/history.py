"""
src/tools/history.py - Git History Analysis Tool
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
from git import Repo
from src.tools.gitops import GitOps


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
        max_commits: int = 50
    ) -> List[Dict]:
        """
        Track changes to a specific variable across commit history.
        
        Args:
            variable_name: Name of the variable to track
            file_path: Optional specific file to search in
            max_commits: Maximum number of commits to analyze
            
        Returns:
            List of dictionaries containing change information
        """
        changes = []
        
        # Search pattern for the variable
        pattern = rf'\b{re.escape(variable_name)}\s*=\s*(.+?)(?:\n|$|#)'
        
        try:
            # Get commit history
            if file_path:
                commits = list(self.repo.iter_commits(paths=file_path, max_count=max_commits))
            else:
                # Search all Python files
                commits = list(self.repo.iter_commits(max_count=max_commits))
            
            for commit in commits:
                try:
                    # Get the diff for this commit
                    if commit.parents:
                        diffs = commit.parents[0].diff(commit, create_patch=True)
                    else:
                        # First commit - compare to empty tree
                        diffs = commit.diff(self.repo.tree(), create_patch=True)
                    
                    for diff in diffs:
                        # Only process additions/modifications
                        if diff.change_type in ['A', 'M']:
                            file_path_in_commit = diff.b_path
                            
                            # Skip non-Python files
                            if not file_path_in_commit.endswith('.py'):
                                continue
                            
                            # If file_path specified, filter
                            if file_path and file_path not in file_path_in_commit:
                                continue
                            
                            # Check if variable appears in diff
                            if diff.diff:
                                diff_text = diff.diff.decode('utf-8', errors='ignore')
                                
                                # Look for additions containing the variable
                                for line in diff_text.split('\n'):
                                    if line.startswith('+') and variable_name in line:
                                        # Extract value
                                        match = re.search(pattern, line)
                                        if match:
                                            value = match.group(1).strip()
                                            
                                            changes.append({
                                                'commit_hash': commit.hexsha[:7],
                                                'commit_date': datetime.fromtimestamp(commit.committed_date),
                                                'author': commit.author.name,
                                                'message': commit.message.split('\n')[0],
                                                'file': file_path_in_commit,
                                                'value': value,
                                                'diff_line': line.strip()
                                            })
                
                except Exception as e:
                    # Skip commits that cause errors
                    continue
            
            return changes
        
        except Exception as e:
            return []
    
    def get_current_value(self, variable_name: str, file_path: str) -> Optional[str]:
        """
        Get the current value of a variable in a file.
        """
        try:
            full_path = self.repo.working_dir + '/' + file_path
            with open(full_path, 'r') as f:
                content = f.read()
            
            pattern = rf'\b{re.escape(variable_name)}\s*=\s*(.+?)(?:\n|$|#)'
            match = re.search(pattern, content, re.MULTILINE)
            
            if match:
                return match.group(1).strip()
            return None
        except:
            return None
    
    def find_last_modification(
        self, 
        search_term: str, 
        file_path: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Find the last commit that modified a specific term (variable, function, etc.)
        """
        changes = self.track_variable_changes(search_term, file_path, max_commits=100)
        
        if changes:
            # Sort by date descending and return most recent
            changes.sort(key=lambda x: x['commit_date'], reverse=True)
            return changes[0]
        
        return None
    
    def search_files_for_pattern(self, pattern: str, file_extension: str = '.py') -> List[Dict]:
        """
        Search all tracked files for a specific pattern.
        Useful for finding where functions/classes are defined.
        """
        results = []
        
        try:
            # Get all files with specified extension
            files = self.repo.git.ls_files(f'*{file_extension}').split('\n')
            
            for file_path in files:
                try:
                    full_path = self.repo.working_dir + '/' + file_path
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    # Search for pattern
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            # Get context (3 lines before and after)
                            context_start = max(0, line_num - 4)
                            context_end = min(len(lines), line_num + 3)
                            context = '\n'.join(lines[context_start:context_end])
                            
                            results.append({
                                'file': file_path,
                                'line_number': line_num,
                                'matched_line': line.strip(),
                                'context': context
                            })
                except Exception:
                    continue
        
        except Exception:
            pass
        
        return results
    
    def find_function_definition(self, function_name: str) -> List[Dict]:
        """
        Find where a function is defined in the codebase.
        """
        # Pattern for function definitions
        pattern = rf'^\s*def\s+{re.escape(function_name)}\s*\('
        return self.search_files_for_pattern(pattern)
    
    def find_class_definition(self, class_name: str) -> List[Dict]:
        """
        Find where a class is defined in the codebase.
        """
        # Pattern for class definitions
        pattern = rf'^\s*class\s+{re.escape(class_name)}\s*[\(:]'
        return self.search_files_for_pattern(pattern)
    
    def get_commit_details(self, commit_hash: str) -> Optional[Dict]:
        """
        Get detailed information about a specific commit.
        """
        try:
            commit = self.repo.commit(commit_hash)
            
            return {
                'hash': commit.hexsha[:7],
                'full_hash': commit.hexsha,
                'author': commit.author.name,
                'email': commit.author.email,
                'date': datetime.fromtimestamp(commit.committed_date),
                'message': commit.message,
                'files_changed': [item.a_path for item in commit.stats.files.keys()],
                'insertions': sum([f['insertions'] for f in commit.stats.files.values()]),
                'deletions': sum([f['deletions'] for f in commit.stats.files.values()])
            }
        except:
            return None