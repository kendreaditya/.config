"""Shared text/LLM domain processing utilities for config scripts."""
import re


def split_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries (period/exclamation/question followed by capital)."""
    pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    return [s.strip() for s in re.split(pattern, text) if s.strip()]


def get_tokenizer(model: str = "cl100k_base"):
    """Get tiktoken tokenizer, with helpful error if not installed."""
    try:
        import tiktoken
        return tiktoken.get_encoding(model)
    except ImportError:
        import sys
        print("Error: tiktoken is required. Install with: pip install tiktoken", file=sys.stderr)
        sys.exit(1)


def count_tokens(text: str, tokenizer) -> int:
    """Count tokens in text."""
    return len(tokenizer.encode(text))
