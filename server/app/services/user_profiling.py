"""
User profiling system to track individual coding styles and preferences.
Analyzes accepted completions to build personalized coding profiles.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

from pydantic import BaseModel


class CodingStyle(BaseModel):
    """User's coding style preferences detected from their accepted completions"""
    
    # Indentation
    indent_size: int = 4  # 2, 4, or 8 spaces
    uses_tabs: bool = False
    
    # Quotes
    prefers_single_quotes: bool = False  # True = '', False = ""
    
    # Naming conventions
    prefers_snake_case: bool = True  # snake_case vs camelCase
    
    # Code structure
    avg_line_length: int = 80
    max_line_length: int = 120
    prefers_early_return: bool = True
    
    # Typing
    uses_type_hints: bool = False
    
    # Documentation
    uses_docstrings: bool = False
    docstring_style: str = "google"  # google, numpy, sphinx
    
    # Comments
    comment_frequency: float = 0.1  # comments per line of code
    
    # Samples analyzed
    total_samples: int = 0
    last_updated: str = ""


class UserProfile(BaseModel):
    """Complete user profile with coding style and behavior patterns"""
    
    user_id: str  # SHA-256 hash of user identifier
    coding_style: CodingStyle = CodingStyle()
    
    # Behavior metrics
    accept_rate: float = 0.0  # % of suggestions accepted
    avg_accept_time_ms: float = 0.0  # how long before accepting
    rejection_patterns: list[str] = []  # common rejection reasons
    
    # Preferences
    preferred_completion_length: int = 50  # avg chars in accepted completions
    prefers_multi_line: bool = False
    
    # Context
    common_libraries: list[str] = []  # most used imports
    project_patterns: list[str] = []  # common code patterns
    
    created_at: str = ""
    updated_at: str = ""


class UserProfiler:
    """Analyzes user code to build personalized profiles"""
    
    def __init__(self, data_dir: Path = Path("data/user_profiles")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def get_profile_path(self, user_id: str) -> Path:
        """Get path to user's profile file"""
        return self.data_dir / f"{user_id}.json"
    
    def load_profile(self, user_id: str) -> UserProfile:
        """Load user profile or create new one"""
        profile_path = self.get_profile_path(user_id)
        
        if profile_path.exists():
            try:
                data = json.loads(profile_path.read_text())
                return UserProfile(**data)
            except Exception:
                pass
        
        # Create new profile
        now = datetime.utcnow().isoformat()
        return UserProfile(
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
    
    def save_profile(self, profile: UserProfile):
        """Save user profile to disk"""
        profile.updated_at = datetime.utcnow().isoformat()
        profile_path = self.get_profile_path(profile.user_id)
        profile_path.write_text(profile.model_dump_json(indent=2))
    
    def analyze_code_sample(self, code: str) -> dict:
        """Analyze a code sample to extract style preferences"""
        lines = code.split('\n')
        non_empty_lines = [ln for ln in lines if ln.strip()]
        
        if not non_empty_lines:
            return {}
        
        analysis = {}
        
        # Detect indent size
        indents = []
        for ln in non_empty_lines:
            if ln.startswith(' '):
                indent = len(ln) - len(ln.lstrip(' '))
                if indent > 0:
                    indents.append(indent)
        
        if indents:
            # Find GCD of all indents (common indent size)
            from math import gcd
            from functools import reduce
            indent_size = reduce(gcd, indents) if len(indents) > 1 else indents[0]
            analysis['indent_size'] = min(indent_size, 8)  # cap at 8
        
        # Detect tabs vs spaces
        analysis['uses_tabs'] = any('\t' in ln for ln in lines)
        
        # Quote preference
        single_quotes = len(re.findall(r"'[^']*'", code))
        double_quotes = len(re.findall(r'"[^"]*"', code))
        if single_quotes + double_quotes > 0:
            analysis['prefers_single_quotes'] = single_quotes > double_quotes
        
        # Naming convention
        snake_case_vars = len(re.findall(r'\b[a-z_][a-z0-9_]*\b', code))
        camel_case_vars = len(re.findall(r'\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b', code))
        if snake_case_vars + camel_case_vars > 0:
            analysis['prefers_snake_case'] = snake_case_vars > camel_case_vars
        
        # Line length
        line_lengths = [len(ln) for ln in non_empty_lines]
        if line_lengths:
            analysis['avg_line_length'] = int(sum(line_lengths) / len(line_lengths))
            analysis['max_line_length'] = max(line_lengths)
        
        # Type hints
        analysis['uses_type_hints'] = bool(re.search(r':\s*\w+(\[|$)', code))
        
        # Docstrings
        analysis['uses_docstrings'] = bool(re.search(r'"""[\s\S]*?"""', code))
        
        # Comments
        comment_lines = len([ln for ln in lines if ln.strip().startswith('#')])
        analysis['comment_frequency'] = comment_lines / max(len(non_empty_lines), 1)
        
        # Common imports
        imports = re.findall(r'(?:from|import)\s+(\w+)', code)
        analysis['imports'] = list(set(imports))
        
        return analysis
    
    def update_profile_from_completion(
        self, 
        user_id: str, 
        prefix: str,
        completion: str, 
        accepted: bool,
        accept_time_ms: float = 0.0
    ):
        """Update user profile based on a completion interaction"""
        profile = self.load_profile(user_id)
        
        if accepted:
            # Analyze the accepted completion
            analysis = self.analyze_code_sample(completion)
            
            # Update coding style (weighted average)
            style = profile.coding_style
            n = style.total_samples
            weight = 1.0 / (n + 1)  # weight for new sample
            
            if 'indent_size' in analysis:
                style.indent_size = int(
                    style.indent_size * (1 - weight) + analysis['indent_size'] * weight
                )
            
            if 'uses_tabs' in analysis:
                style.uses_tabs = analysis['uses_tabs']
            
            if 'prefers_single_quotes' in analysis:
                # Use majority vote
                if n == 0:
                    style.prefers_single_quotes = analysis['prefers_single_quotes']
                else:
                    votes = n * (1 if style.prefers_single_quotes else 0) + (1 if analysis['prefers_single_quotes'] else 0)
                    style.prefers_single_quotes = votes > (n + 1) / 2
            
            if 'prefers_snake_case' in analysis:
                if n == 0:
                    style.prefers_snake_case = analysis['prefers_snake_case']
                else:
                    votes = n * (1 if style.prefers_snake_case else 0) + (1 if analysis['prefers_snake_case'] else 0)
                    style.prefers_snake_case = votes > (n + 1) / 2
            
            if 'avg_line_length' in analysis:
                style.avg_line_length = int(
                    style.avg_line_length * (1 - weight) + analysis['avg_line_length'] * weight
                )
            
            if 'max_line_length' in analysis:
                style.max_line_length = max(style.max_line_length, analysis['max_line_length'])
            
            if 'uses_type_hints' in analysis:
                if n == 0:
                    style.uses_type_hints = analysis['uses_type_hints']
                else:
                    votes = n * (1 if style.uses_type_hints else 0) + (1 if analysis['uses_type_hints'] else 0)
                    style.uses_type_hints = votes > (n + 1) / 2
            
            if 'uses_docstrings' in analysis:
                if n == 0:
                    style.uses_docstrings = analysis['uses_docstrings']
                else:
                    votes = n * (1 if style.uses_docstrings else 0) + (1 if analysis['uses_docstrings'] else 0)
                    style.uses_docstrings = votes > (n + 1) / 2
            
            if 'comment_frequency' in analysis:
                style.comment_frequency = (
                    style.comment_frequency * (1 - weight) + analysis['comment_frequency'] * weight
                )
            
            # Update imports
            if 'imports' in analysis:
                for imp in analysis['imports']:
                    if imp not in profile.common_libraries:
                        profile.common_libraries.append(imp)
                # Keep top 20 most common
                profile.common_libraries = profile.common_libraries[:20]
            
            # Update completion preferences
            comp_len = len(completion)
            profile.preferred_completion_length = int(
                profile.preferred_completion_length * (1 - weight) + comp_len * weight
            )
            profile.prefers_multi_line = '\n' in completion
            
            # Update behavior metrics
            profile.accept_rate = (profile.accept_rate * n + 1) / (n + 1)
            profile.avg_accept_time_ms = (profile.avg_accept_time_ms * n + accept_time_ms) / (n + 1)
            
            style.total_samples += 1
            style.last_updated = datetime.utcnow().isoformat()
        
        else:
            # Rejected - update metrics
            n = profile.coding_style.total_samples
            if n > 0:
                profile.accept_rate = (profile.accept_rate * n) / (n + 1)
        
        self.save_profile(profile)
        return profile
    
    def get_style_hints(self, user_id: str) -> str:
        """Generate style hints for LLM prompt"""
        profile = self.load_profile(user_id)
        style = profile.coding_style
        
        if style.total_samples < 3:
            return ""  # Not enough data yet
        
        hints = []
        
        # Indentation
        if style.uses_tabs:
            hints.append("Use tabs for indentation")
        else:
            hints.append(f"Use {style.indent_size} spaces for indentation")
        
        # Quotes
        if style.prefers_single_quotes:
            hints.append("Prefer single quotes for strings")
        else:
            hints.append("Prefer double quotes for strings")
        
        # Naming
        if style.prefers_snake_case:
            hints.append("Use snake_case naming")
        else:
            hints.append("Use camelCase naming")
        
        # Line length
        hints.append(f"Keep lines under {style.max_line_length} characters")
        
        # Type hints
        if style.uses_type_hints:
            hints.append("Include type hints")
        
        # Docstrings
        if style.uses_docstrings:
            hints.append(f"Include docstrings ({style.docstring_style} style)")
        
        # Comments
        if style.comment_frequency > 0.15:
            hints.append("Add explanatory comments")
        
        return "User's coding style: " + "; ".join(hints) + "."


# Global profiler instance
_profiler: Optional[UserProfiler] = None


def get_profiler() -> UserProfiler:
    """Get global profiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = UserProfiler()
    return _profiler
