"""
Utility for managing the GitMentor workspace and artifact persistence.
Optimized to overwrite existing artifacts to maintain a clean workspace.
"""
import os
from typing import Optional
from src.utils.config import cfg

# Load workspace directory from config or default to the new GitMentor path
WORKSPACE_DIR = cfg.get("paths.workspace", "./.gitmentor_workspace")

def save_artifact(content: str, extension: str, prefix: Optional[str] = None) -> str:
    """
    Saves content to the GitMentor workspace. Overwrites existing files with the same prefix.
    
    Args:
        content: The string content to save.
        extension: File extension (e.g., 'md', 'mmd', 'txt').
        prefix: Optional descriptive name for the filename.
    """
    # Ensure we use the latest workspace path from config
    target_dir = cfg.get("paths.workspace", WORKSPACE_DIR)
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    if prefix:
        # Example: dependency_graph.mmd
        filename = f"{prefix}.{extension}"
    else:
        # Fallback if no prefix is provided
        filename = f"latest_artifact.{extension}"
    
    filepath = os.path.join(target_dir, filename)
    
    # Writing with 'w' naturally overwrites the existing file to prevent UUID clutter
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath

def load_artifact(filepath: str) -> str:
    """Reads artifact data from disk back into memory."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()