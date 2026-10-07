import os
import re
from dotenv import load_dotenv

load_dotenv()

USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"

if USE_GROQ:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    MODEL = "openai/gpt-oss-20b"
else:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    MODEL = "gpt-4o-mini"


PROMPT_TEMPLATE = """You are a surgical code repair agent.

FAILING TEST:
{pytest_output}

FILE TO FIX: {file_path}

CURRENT CONTENT OF THE FILE:
{source_code}

TASK:
Fix the bug so the failing test passes. Keep everything else the same.

OUTPUT RULES:
1. Output ONLY the complete fixed file content
2. NO explanations
3. NO markdown code fences (no ```)
4. NO commentary
5. Just the raw Python code, exactly as it should appear in the file

Output the fixed {file_path} now:"""


def generate_fixed_file(pytest_output, file_path, source_code):
    """Ask LLM to return the FIXED FILE CONTENT directly."""
    prompt = PROMPT_TEMPLATE.format(
        pytest_output=pytest_output[-3000:],
        file_path=file_path,
        source_code=source_code
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2000
        )
        content = response.choices[0].message.content.strip()
        
        # Strip markdown code fences if LLM adds them anyway
        if content.startswith("```"):
            content = re.sub(r'^```[a-zA-Z]*\n', '', content)
            content = re.sub(r'\n```\s*$', '', content)
        
        return content.strip()
    except Exception as e:
        return f"CANNOT_FIX: LLM error: {e}"