"""Local model delegation harness for Gemini.

Sends mechanical, bounded subtasks to a local Ollama instance (default: qwen3.5:9b)
over HTTP on localhost:11434, standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

OLLAMA_BASE_URL = 'http://localhost:11434'
DEFAULT_MODEL = 'qwen3.5:9b'


def get_available_models(base_url: str = OLLAMA_BASE_URL) -> list[str]:
    """Retrieve list of model names currently available in Ollama.

    Args:
        base_url: Base URL of the Ollama server.

    Returns:
        List of installed model names.

    Raises:
        RuntimeError: If Ollama is unreachable.
    """
    url = f'{base_url}/api/tags'
    try:
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            models = [m.get('name', '') for m in data.get('models', []) if m.get('name')]
            return models
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise RuntimeError(
            f'Ollama is not running on {base_url}. Please ensure Ollama is started.\nDetail: {err}'
        ) from err


def verify_model_available(available_models: list[str], target_model: str) -> None:
    """Verify target model exists in Ollama.

    Args:
        available_models: List of installed model names.
        target_model: Target model name to check.

    Raises:
        ValueError: If model is not found in available models.
    """
    # Exact match or tag prefix match (e.g. qwen3.5:9b vs qwen3.5:9b:latest)
    for name in available_models:
        if name == target_model or name.startswith(f'{target_model}:') or target_model.startswith(f'{name}:'):
            return

    models_list = ', '.join(available_models) if available_models else 'none'
    raise ValueError(
        f"Model '{target_model}' not found in Ollama.\n"
        f'Available models: {models_list}\n'
        f"Please run 'ollama pull {target_model}'."
    )


def generate_response(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    num_ctx: int = 16384,
    timeout: int = 300,
) -> str:
    """Generate completion from Ollama using the /api/generate endpoint.

    Args:
        prompt: Full prompt string.
        model: Model identifier.
        base_url: Ollama base URL.
        num_ctx: Context window size (default 16384).
        timeout: Request timeout in seconds.

    Returns:
        Generated text response from the model.

    Raises:
        RuntimeError: If generation request fails.
    """
    url = f'{base_url}/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {
            'num_ctx': num_ctx,
        },
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            response_text = data.get('response', '')
            if not response_text and data.get('thinking'):
                # Fallback to thinking output if response is empty
                response_text = data.get('thinking', '')
            return response_text
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise RuntimeError(
            f'Failed to generate response from Ollama on {base_url}: {err}'
        ) from err


def run_selftest(model: str = DEFAULT_MODEL, base_url: str = OLLAMA_BASE_URL) -> int:
    """Execute end-to-end self-test against local Ollama.

    Args:
        model: Model name to test.
        base_url: Ollama base URL.

    Returns:
        0 on success, non-zero on failure.
    """
    print(f'Running Ollama self-test for model: {model} at {base_url}...')
    try:
        models = get_available_models(base_url)
        print(f"Ollama reachable. Installed models: {', '.join(models) if models else 'none'}")
        verify_model_available(models, model)
        print(f"Model '{model}' verified.")
    except (RuntimeError, ValueError) as err:
        sys.stderr.write(f'Selftest FAILED during pre-check: {err}\n')
        return 1

    test_prompt = 'Respond with the single word OK and nothing else.'
    print(f"Sending test prompt: '{test_prompt}'")
    try:
        reply = generate_response(
            test_prompt,
            model=model,
            base_url=base_url,
            num_ctx=4096,
            timeout=120,
        )
        clean_reply = reply.strip()
        print(f"Received reply: '{clean_reply}'")
        if not clean_reply:
            sys.stderr.write('Selftest FAILED: empty response from model.\n')
            return 1
        print('Selftest PASSED successfully.')
        return 0
    except RuntimeError as err:
        sys.stderr.write(f'Selftest FAILED during generation: {err}\n')
        return 1


def build_full_prompt(prompt_file: str, input_files: list[str]) -> str:
    """Read prompt and append any input files.

    Args:
        prompt_file: Path to main prompt file.
        input_files: List of paths to input files to append.

    Returns:
        Combined prompt string.
    """
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    parts = [prompt_text]
    for inp in input_files:
        with open(inp, 'r', encoding='utf-8') as f:
            content = f.read()
        parts.append(f'\n\n--- Input: {inp} ---\n{content}')

    return ''.join(parts)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command-line argument list.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description='Delegate a bounded subtask to a local Ollama model.'
    )
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help=f'Ollama model name (default: {DEFAULT_MODEL})',
    )
    parser.add_argument(
        '--prompt-file',
        help='Path to file containing instructions/prompt',
    )
    parser.add_argument(
        '--input',
        nargs='+',
        action='extend',
        dest='inputs',
        default=[],
        help='Zero or more input files to append to the prompt',
    )
    parser.add_argument(
        '--out',
        help='Path to output file to write generated text to',
    )
    parser.add_argument(
        '--num-ctx',
        type=int,
        default=16384,
        help='Ollama context window size in tokens (default: 16384)',
    )
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='Run connection and generation self-test against local Ollama',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 on success).
    """
    args = parse_args(argv)

    if args.selftest:
        return run_selftest(model=args.model, base_url=OLLAMA_BASE_URL)

    if not args.prompt_file or not args.out:
        sys.stderr.write(
            'Error: --prompt-file and --out are required when not running --selftest.\n'
            'Usage: python tools/local_model.py --prompt-file <path> --out <path> [--input <file> ...] [--model <name>]\n'
        )
        return 1

    if not os.path.exists(args.prompt_file):
        sys.stderr.write(f"Error: Prompt file not found: '{args.prompt_file}'\n")
        return 1

    for inp in args.inputs:
        if not os.path.exists(inp):
            sys.stderr.write(f"Error: Input file not found: '{inp}'\n")
            return 1

    try:
        models = get_available_models(OLLAMA_BASE_URL)
        verify_model_available(models, args.model)
    except (RuntimeError, ValueError) as err:
        sys.stderr.write(f'{err}\n')
        return 1

    full_prompt = build_full_prompt(args.prompt_file, args.inputs)

    try:
        result = generate_response(
            full_prompt,
            model=args.model,
            base_url=OLLAMA_BASE_URL,
            num_ctx=args.num_ctx,
        )
    except RuntimeError as err:
        sys.stderr.write(f'{err}\n')
        return 1

    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f'Output written to {args.out} ({len(result)} chars)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
