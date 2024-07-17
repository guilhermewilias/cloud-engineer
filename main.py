import os
import json
import base64
import io
import re
import difflib
import time
import asyncio
import aiohttp # type: ignore
import datetime
import venv
import subprocess
import sys
import signal
import logging
from typing import Tuple, Optional


def setup_virtual_environment() -> Tuple[str, str]:
    venv_name = "code_execution_env"
    venv_path = os.path.join(os.getcwd(), venv_name)
    try:
        if not os.path.exists(venv_path):
            venv.create(venv_path, with_pip=True)

        if sys.platform == "win32":
            activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
        else:
            activate_script = os.path.join(venv_path, "bin", "activate")
            
        return venv_path, activate_script
    
    except Exception as e:
        logging.error(f"Error setting up virtual environment: {str(e)}")
        raise

    # Load environment variables from .env file

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    client = Anthropic(api_key=anthropic_api_key)

    # Initialize the Tavily client

    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    tavily = TavilyClient(api_key=tavily_api_key)

    console = Console()

    # Token tracking variables
main_model_tokens = {'input': 0, 'output': 0}
tool_checker_tokens = {'input': 0, 'output': 0}
code_editor_tokens = {'input': 0, 'output': 0}
code_execution_tokens = {'input': 0, 'output': 0}

# Set up the conversation memory (maintains context for MAINMODEL)
conversation_history = []

# Store file contents (part of the context for MAINMODEL)
file_contents = {}

# Code editor memory (maintains some context for CODEEDITORMODEL between calls)
code_editor_memory = []

# automode flag
automode = False

# Store file contents
file_contents = {}

# Global dictionary to store running processes
running_processes = {}

# Constants
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25
MAX_CONTEXT_TOKENS = 200000  # Reduced to 200k tokens for context window

# Models
# Models that maintain context memory across interactions
MAINMODEL = "claude-3-5-sonnet-20240620"  # Maintains conversation history and file contents

# Models that don't maintain context (memory is reset after each call)
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"
CODEEDITORMODEL = "claude-3-5-sonnet-20240620"
CODEEXECUTIONMODEL = "claude-3-haiku-20240307"



def update_system_prompt(current_iteration: Optional[int] = None, max_iterations: Optional[int] = None) -> str:
    global file_contents
    chain_of_thought_prompt = ""

    file_contents_prompt = "\n\nFile Contents:\n"
    for path, content in file_contents.items():
        file_contents_prompt += f"\n--- {path} ---\n{content}\n"

    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + AUTOMODE_SYSTEM_PROMPT.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt # type: ignore
    else:
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + chain_of_thought_prompt # type: ignore
    

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"
    
def create_file(path, content=""):
    global file_contents
    try:
        with open(path, 'w') as f:
            f.write(content)
            file_contents[path] = content
            return f"File created and added to system prompt: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"
    
def highlight_diff(diff_text):
    return Syntax(diff_text, theme="monokai", line_numbers=True) # type: ignore

def generate_and_apply_diff(original_content, new_content, path):
    diff = list(difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    if not diff:
        return "No changes detected"
    
    try:
        with open(path, 'w') as f:
            f.writelines(new_content)

        diff_text = ''.join(diff)
        highlighted_diff = highlight_diff(diff_text)

        diff_panel = Panel( # type: ignore
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="Cyan"
        )

        console.print(diff_panel) # type: ignore

        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        summary = f"Changes applied to {path}:\n"
        summary += f"Lines added: {added_lines}\n"
        summary += f"Lines removed: {removed_lines}\n"

        return summary
    
    except Exception as e:
        error_panel = Panel( # type: ignore
            f"Error: {str(e)}",
            title="Error Applying Changes",
            style="bold red"
        )
        console.print(error_panel) # type: ignore
        return f"Error Applying Changes: {str(e)}"
    
async def generate_edit_instructions(file_content, instructions, project_context):
    global code_editor_tokens, code_editor_memory