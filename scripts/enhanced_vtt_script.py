#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pathlib import Path


def estimate_tokens(text):
    """
    Estimate the number of tokens in text using a simple heuristic.
    Rough approximation: 1 token ≈ 4 characters for English text.
    
    Args:
        text (str): Input text
        
    Returns:
        int: Estimated token count
    """
    return len(text) // 4


def truncate_text(text, max_length, position='end', use_tokens=False):
    """
    Truncate text based on specified parameters.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length (characters or tokens)
        position (str): Where to truncate ('start', 'middle', 'end')
        use_tokens (bool): Whether to use token estimation instead of character count
        
    Returns:
        str: Truncated text
    """
    if not text or max_length <= 0:
        return text
    
    # Determine current length
    current_length = estimate_tokens(text) if use_tokens else len(text)
    
    if current_length <= max_length:
        return text
    
    # Calculate truncation points
    if position == 'start':
        # Keep the end, remove from start
        if use_tokens:
            # Rough estimate: find character position for token count
            char_pos = max_length * 4
            return '...' + text[-char_pos:]
        else:
            return '...' + text[-max_length:]
    
    elif position == 'middle':
        # Keep start and end, remove from middle
        if use_tokens:
            # Rough estimate for character positions
            start_chars = (max_length // 2) * 4
            end_chars = (max_length // 2) * 4
            return text[:start_chars] + ' [...] ' + text[-end_chars:]
        else:
            start_chars = max_length // 2
            end_chars = max_length // 2
            return text[:start_chars] + ' [...] ' + text[-end_chars:]
    
    else:  # position == 'end' (default)
        # Keep the start, remove from end
        if use_tokens:
            # Rough estimate: find character position for token count
            char_pos = max_length * 4
            return text[:char_pos] + '...'
        else:
            return text[:max_length] + '...'


def clean_vtt_text(text):
    """
    Clean VTT subtitle text by removing timestamps, HTML tags, and redundant information.
    
    Args:
        text (str): Raw VTT file content
        
    Returns:
        str: Cleaned text
    """
    # Remove timestamps (00:00:00.000 --> 00:00:00.000)
    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', text)
    # Remove HTML-style tags (<c>, </c>, etc.)
    text = re.sub(r'<[^>]+>', '', text)
    # Remove WEBVTT header and metadata
    text = re.sub(r'WEBVTT\n.*?\n\n', '', text, flags=re.DOTALL)
    # Remove alignment and position info
    text = re.sub(r'align:.*position:.*%\n', '', text)
    # Remove empty lines and leading/trailing spaces
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # Remove duplicates while maintaining order
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    return '\n'.join(unique_lines)


def calculate_dynamic_truncation(total_files, context_length, current_total_length, use_tokens=False):
    """
    Calculate how much to truncate each remaining file to fit within context length.
    
    Args:
        total_files (int): Total number of files to process
        context_length (int): Maximum total context length
        current_total_length (int): Current accumulated length
        use_tokens (bool): Whether to use token estimation
        
    Returns:
        int: Maximum length per file for remaining files
    """
    remaining_length = context_length - current_total_length
    if remaining_length <= 0:
        return 0
    
    # Distribute remaining length among remaining files
    # Add some buffer for headers and spacing
    header_overhead = 50  # Approximate overhead per file header
    return max(0, (remaining_length - (total_files * header_overhead)) // total_files)


def process_vtt_file(vtt_file_path, outfile, verbose=False, max_length=None, 
                    truncate_position='end', use_tokens=False, dynamic_length=None):
    """
    Process a single file and write the content to the output file.
    For .vtt files, apply WebVTT-specific cleaning; for other files, pass content through unchanged.
    
    Args:
        vtt_file_path (Path): Path to the file
        outfile: File object for writing output
        verbose (bool): Whether to print detailed information
        max_length (int): Maximum length for truncation (None for no truncation)
        truncate_position (str): Where to truncate ('start', 'middle', 'end')
        use_tokens (bool): Whether to use token estimation
        dynamic_length (int): Dynamic truncation length (overrides max_length if provided)
        
    Returns:
        tuple: (success: bool, content_length: int)
    """
    try:
        if verbose:
            print(f"Reading file: {vtt_file_path}")
        
        is_vtt = vtt_file_path.suffix.lower() == '.vtt'
        with open(vtt_file_path, 'r', encoding='utf-8') as infile:
            content = infile.read()
            clean_text = clean_vtt_text(content) if is_vtt else content
            
            # Apply truncation if specified
            truncation_length = dynamic_length or max_length
            if truncation_length:
                original_length = estimate_tokens(clean_text) if use_tokens else len(clean_text)
                clean_text = truncate_text(clean_text, truncation_length, truncate_position, use_tokens)
                
                if verbose:
                    new_length = estimate_tokens(clean_text) if use_tokens else len(clean_text)
                    unit = "tokens" if use_tokens else "characters"
                    print(f"  Truncated from {original_length} to {new_length} {unit}")
            
            # Write file name as header
            header = f"\n=== {vtt_file_path.name} ===\n"
            content_with_header = header + clean_text + '\n\n'
            outfile.write(content_with_header)
            
            # Calculate content length for dynamic truncation tracking
            content_length = estimate_tokens(content_with_header) if use_tokens else len(content_with_header)
        
        print(f"Processed: {vtt_file_path.name}")
        return True, content_length
    except Exception as e:
        print(f"Error processing {vtt_file_path.name}: {str(e)}", file=sys.stderr)
        return False, 0


def process_vtt_files(input_dir='.', output_file='combined_transcripts.txt', single_file=None, 
                     verbose=False, max_length=None, context_length=None, 
                     truncate_position='end', use_tokens=False):
    """
    Process files in a directory and combine them into a single text file.
    WebVTT (.vtt) files will be cleaned; other files are included as-is.
    
    Args:
        input_dir (str): Directory containing files
        output_file (str): Name of the output file
        single_file (str): Optional single file to process instead of all files
        verbose (bool): Whether to print detailed information
        max_length (int): Maximum length per file for truncation
        context_length (int): Total context length limit
        truncate_position (str): Where to truncate ('start', 'middle', 'end')
        use_tokens (bool): Whether to use token estimation
        
    Returns:
        int: Number of successfully processed files
    """
    input_path = Path(input_dir)
    output_path = Path(output_file)
    
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist", file=sys.stderr)
        return 0
        
    if verbose:
        print(f"Input directory: {input_path.absolute()}")
        print(f"Output file: {output_path.absolute()}")
        if max_length:
            unit = "tokens" if use_tokens else "characters"
            print(f"Max length per file: {max_length} {unit}")
        if context_length:
            unit = "tokens" if use_tokens else "characters"
            print(f"Total context length limit: {context_length} {unit}")
        print(f"Truncation position: {truncate_position}")
    
    # Get files to process
    if single_file:
        single_file_path = input_path / single_file
        if not single_file_path.exists():
            print(f"Error: File '{single_file_path}' does not exist", file=sys.stderr)
            return 0
        vtt_files = [single_file_path]
        if verbose:
            print(f"Processing single file: {single_file_path.name}")
    else:
        vtt_files = [p for p in input_path.iterdir() if p.is_file()]
        if verbose:
            print(f"Found {len(vtt_files)} files to process")
    
    if not vtt_files:
        print("No files found to process", file=sys.stderr)
        return 0
    
    success_count = 0
    total_length = 0
    
    # Open output file in write mode
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for i, vtt_file in enumerate(vtt_files):
            # Calculate dynamic truncation if context_length is specified
            dynamic_length = None
            if context_length and not max_length:
                remaining_files = len(vtt_files) - i
                dynamic_length = calculate_dynamic_truncation(
                    remaining_files, context_length, total_length, use_tokens
                )
                if verbose and dynamic_length > 0:
                    unit = "tokens" if use_tokens else "characters"
                    print(f"  Dynamic truncation length: {dynamic_length} {unit}")
            
            # Process file
            success, content_length = process_vtt_file(
                vtt_file, outfile, verbose, max_length, 
                truncate_position, use_tokens, dynamic_length
            )
            
            if success:
                success_count += 1
                total_length += content_length
                
                # Check if we've exceeded context length
                if context_length and total_length >= context_length:
                    remaining_files = len(vtt_files) - i - 1
                    if remaining_files > 0:
                        print(f"Warning: Context length limit reached. Skipping {remaining_files} remaining files.")
                    break
    
    print(f"Successfully processed {success_count} out of {len(vtt_files)} files")
    if verbose:
        unit = "tokens" if use_tokens else "characters"
        print(f"Total output length: {total_length} {unit}")
    print(f"Output written to: {output_path.absolute()}")
    
    return success_count


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Combine files into a single text output; cleans WebVTT (.vtt) files automatically",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        default='.',
        help="Directory containing files"
    )
    
    parser.add_argument(
        '-o', '--output-file',
        default='combined_transcripts.txt',
        help="Output file name"
    )
    
    parser.add_argument(
        '-f', '--file',
        help="Process a single file instead of all files in the directory"
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Display detailed processing information"
    )
    
    # Truncation parameters
    parser.add_argument(
        '--max-length',
        type=int,
        help="Maximum length per transcript (characters or tokens)"
    )
    
    parser.add_argument(
        '--context-length',
        type=int,
        help="Total context length limit for all transcripts combined (characters or tokens)"
    )
    
    parser.add_argument(
        '--truncate-position',
        choices=['start', 'middle', 'end'],
        default='end',
        help="Where to truncate text: start (keep end), middle (keep start/end), or end (keep start)"
    )
    
    parser.add_argument(
        '--use-tokens',
        action='store_true',
        help="Use token estimation instead of character count for length calculations"
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for the script.
    """
    args = parse_arguments()
    
    # Validate arguments
    if args.max_length and args.context_length:
        print("Warning: Both --max-length and --context-length specified. --max-length will take precedence.", 
              file=sys.stderr)
    
    success_count = process_vtt_files(
        input_dir=args.input_dir,
        output_file=args.output_file,
        single_file=args.file,
        verbose=args.verbose,
        max_length=args.max_length,
        context_length=args.context_length,
        truncate_position=args.truncate_position,
        use_tokens=args.use_tokens
    )
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())