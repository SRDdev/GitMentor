"""
src/agents/explainer.py - AI-powered Code Explainer Agent
"""
import os
import ast
import textwrap
from typing import Dict, Optional
from src.utils.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

class CodeExplainer:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.llm = get_llm("default")

    def _find_node_in_file(self, file_path: str, name: str, node_type: ast.AST) -> Optional[tuple]:
        """Search a specific file for a function or class definition."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, node_type) and node.name == name:
                    # Extract the source lines for this specific node
                    lines = source.splitlines()
                    start_line = node.lineno - 1
                    end_line = node.end_lineno
                    node_source = "\n".join(lines[start_line:end_line])
                    return node_source, node.lineno
        except Exception:
            return None
        return None

    def _search_codebase(self, name: str, node_type: ast.AST, specific_file: Optional[str] = None) -> Optional[dict]:
        """Scan the directory for the target definition."""
        files_to_scan = []
        if specific_file:
            files_to_scan.append(os.path.join(self.repo_path, specific_file))
        else:
            for root, _, files in os.walk(self.repo_path):
                if "venv" in root or ".git" in root:
                    continue
                for file in files:
                    if file.endswith(".py"):
                        files_to_scan.append(os.path.join(root, file))

        for file_path in files_to_scan:
            result = self._find_node_in_file(file_path, name, node_type)
            if result:
                source, line = result
                return {
                    "source_code": source,
                    "line": line,
                    # FIX: Use os.path.relpath instead of os.relpath
                    "file": os.path.relpath(file_path, self.repo_path),
                    "success": True
                }
        return {"success": False, "error": f"Could not find '{name}' in codebase."}

    def explain_function(self, name: str, level: str = "medium", file_path: Optional[str] = None) -> Dict:
        """Finds and explains a function."""
        data = self._search_codebase(name, ast.FunctionDef, file_path)
        if not data["success"]:
            return data
        
        data["explanation"] = self._generate_ai_explanation(data["source_code"], "function", level)
        return data

    def explain_class(self, name: str, level: str = "medium", file_path: Optional[str] = None) -> Dict:
        """Finds and explains a class."""
        data = self._search_codebase(name, ast.ClassDef, file_path)
        if not data["success"]:
            return data
        
        data["explanation"] = self._generate_ai_explanation(data["source_code"], "class", level)
        return data

    def _generate_ai_explanation(self, source: str, context_type: str, level: str) -> str:
        """Calls the LLM to explain the code snippet."""
        prompt = textwrap.dedent(f"""
            You are an expert software architect. Explain the following Python {context_type} 
            to someone at a '{level}' expertise level.
            
            Expertise Level Definitions:
            - beginner: Focus on high-level purpose, basic logic, and simple analogies. Avoid jargon.
            - medium: Explain the flow, key dependencies, and technical implementation details.
            - hard: Deep dive into architectural decisions, performance implications, and edge cases.

            Source Code:
            ```python
            {source}
            ```

            Provide a structured explanation using Markdown. Include:
            1. **Purpose**: What does this {context_type} do?
            2. **Logic Breakdown**: How does it work?
            3. **Key Components**: Notable variables or logic blocks.
        """)

        response = self.llm.invoke([
            SystemMessage(content="You are a helpful technical documentation assistant."),
            HumanMessage(content=prompt)
        ])
        
        return response.content