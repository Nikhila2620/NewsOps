"""
NewsOps Revision 2 - Tool Command Extraction Pipeline.
Extracts verbatim install commands from README fenced blocks.
Flags high-risk patterns: curl|wget piped to sh, sudo, rm -rf, etc.
verified_verbatim = True if extracted command is a literal substring of source README.
"""
import re
from typing import List, TypedDict

RISK_PATTERNS = [
    (r"curl\s+.*\|\s*(ba)?sh", "curl_pipe_sh"),
    (r"wget\s+.*\|\s*(ba)?sh", "wget_pipe_sh"),
    (r"\bsudo\b", "sudo"),
    (r"rm\s+-rf?\b", "rm_rf"),
    (r"chmod\s+777\b", "chmod_777"),
    (r">\s*/etc/", "write_etc"),
    (r"eval\s*[\$\(]", "eval_expansion"),
]

COMMAND_PATTERNS = [
    r"```(?:bash|sh|shell|zsh|powershell|ps1|cmd)?\n([\s\S]*?)```",
    r"`{1}([^`\n]+(?:pip install|npm install|cargo install|brew install|apt install|curl|wget)[^`\n]*)`",
]


class ExtractedCommand(TypedDict):
    command: str
    risk_flags: List[str]
    verified_verbatim: bool
    block_type: str


def extract_risk_flags(command: str) -> List[str]:
    """Return list of risk flag names present in a command string."""
    flags = []
    for pattern, name in RISK_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            flags.append(name)
    return flags


def extract_commands_from_readme(readme_text: str) -> List[ExtractedCommand]:
    """
    Extract all fenced code block commands from README text.
    Marks verified_verbatim=True if the exact command is a substring of readme_text.
    """
    commands: List[ExtractedCommand] = []
    seen = set()
    
    for pattern in COMMAND_PATTERNS:
        for match in re.finditer(pattern, readme_text, re.MULTILINE):
            block = match.group(1).strip()
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                
                risk_flags = extract_risk_flags(line)
                # verified_verbatim: command must be a literal substring of README
                verified_verbatim = line in readme_text
                
                commands.append(ExtractedCommand(
                    command=line,
                    risk_flags=risk_flags,
                    verified_verbatim=verified_verbatim,
                    block_type="fenced",
                ))
    
    return commands
