# FILE: scripts/code_utils.py
# Utilities for detecting coding topics and extracting/sanitizing code references

import re
from typing import List, Tuple

# Coding-related keywords that indicate a topic should include code displays
CODING_TOPICS = [
    'python', 'javascript', 'java', 'go', 'golang', 'ruby', 'php',
    'c++', 'c#', 'typescript', 'rust', 'kotlin', 'swift', 'scala',
    'git', 'terminal', 'bash', 'shell', 'command line', 'cli',
    'devops', 'docker', 'kubernetes', 'ci/cd', 'github actions',
    'web development', 'frontend', 'backend', 'api', 'rest', 'graphql',
    'database', 'sql', 'nosql', 'mongodb', 'postgresql',
    'data science', 'machine learning', 'ai', 'tensorflow', 'pytorch',
    'code', 'programming', 'developer', 'coding', 'software engineering',
    'react', 'vue', 'angular', 'node', 'django', 'flask', 'fastapi',
    'api design', 'microservices', 'cloud', 'aws', 'gcp', 'azure'
]

# Words/phrases to remove from non-coding scripts
CODE_MENTION_PATTERNS = [
    r'\bcode\b', r'\bsnippet\b', r'\bscript\b', r'\bfunction\b',
    r'see (below|the code|code below|here|this)',
    r"(I'll|let me|i will)\s+(show|display|reveal)",
    r'\b(python|javascript|java|ruby|php|golang|rust)\b',
    r'\bc\+\+\b', r'\bc#\b', r'\btypescript\b',
    r'\bsyntax\b', r'\bvariable\b', r'\bclass\b',
    r'\bmethod\b', r'\bfunction\b', r'\blibrary\b',
    r'\bmodule\b', r'\bpackage\b', r'\bimport\b',
    r'\brequire\b', r'\binstall\b', r'\bnpm\b', r'\bpip\b',
    r'```', r'`[^`]+`'
]


def is_coding_topic(topic: str) -> bool:
    """Check if topic should include code displays."""
    if not topic:
        return False
    
    topic_lower = topic.lower()
    return any(kw in topic_lower for kw in CODING_TOPICS)


def extract_code_markers(visual_cues: List) -> List[str]:
    """Extract code snippets from [CODE_DISPLAY: ...] markers in visual cues."""
    code_snippets = []
    
    if not visual_cues:
        return code_snippets
    
    for cue in visual_cues:
        cue_str = str(cue)
        # Match [CODE_DISPLAY: anything inside]
        matches = re.findall(r'\[CODE_DISPLAY:\s*([^\]]+)\]', cue_str, re.IGNORECASE)
        code_snippets.extend(matches)
    
    return code_snippets


def sanitize_script_for_topic(script: str, is_coding: bool = False) -> str:
    """
    Remove code references from scripts based on topic type.
    
    Args:
        script: Full script text
        is_coding: Whether this is a coding topic
        
    Returns:
        Sanitized script with code mentions removed (if not coding topic)
    """
    if is_coding:
        # For coding topics, keep structure but remove "see code" type phrases
        script = re.sub(
            r"(see|look at|check out)\s+(below|the code|code below|here)",
            "",
            script,
            flags=re.IGNORECASE
        )
        return script
    
    # For non-coding topics: aggressive removal
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', script)
    cleaned = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check if sentence contains any code-related keyword
        has_code_mention = any(
            re.search(pattern, sentence, re.IGNORECASE)
            for pattern in CODE_MENTION_PATTERNS
        )
        
        if not has_code_mention:
            cleaned.append(sentence)
    
    result = ' '.join(cleaned)
    
    # Remove code blocks
    result = re.sub(r'```[\s\S]*?```', '', result)
    result = re.sub(r'`[^`]+`', '', result)
    
    # Collapse extra whitespace
    result = ' '.join(result.split()).strip()
    
    return result


def extract_code_snippets_from_script(script: str, limit: int = 3) -> List[str]:
    """
    Extract actual code snippets from script text.
    Looks for content between triple backticks or marked with [CODE: ...]
    
    Args:
        script: Script text
        limit: Max number of snippets to extract
        
    Returns:
        List of code snippets
    """
    snippets = []
    
    # Try to extract from triple backticks
    backtick_matches = re.findall(r'```(?:python|js|javascript|json)?\n([\s\S]*?)```', script)
    snippets.extend(backtick_matches[:limit])
    
    if len(snippets) < limit:
        # Try [CODE: ...] format
        code_matches = re.findall(r'\[CODE:\s*([^\]]+)\]', script)
        snippets.extend(code_matches[:limit - len(snippets)])
    
    return snippets[:limit]


def format_code_for_display(code: str, max_lines: int = 3) -> str:
    """
    Format code for on-screen display.
    
    Args:
        code: Raw code text
        max_lines: Maximum lines to display
        
    Returns:
        Formatted code (truncated if needed)
    """
    lines = [l.strip() for l in code.split('\n') if l.strip()]
    
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append('# ...')
    
    return '\n'.join(lines)


def should_display_code_in_description(topic: str, allow_env: bool = True) -> bool:
    """
    Determine if code should be displayed in YouTube description.
    
    Args:
        topic: Topic name
        allow_env: Whether to respect ALLOW_CODE_IN_DESCRIPTION env var
        
    Returns:
        True if code should be in description
    """
    if not is_coding_topic(topic):
        return False
    
    if allow_env:
        import os
        return os.getenv('ALLOW_CODE_IN_DESCRIPTION', 'true').lower() == 'true'
    
    return True
