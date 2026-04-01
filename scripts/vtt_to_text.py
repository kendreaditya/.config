#!/usr/bin/env python3
import os
import re
import sys
import argparse
from pathlib import Path


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


def process_vtt_file(vtt_file_path, outfile, verbose=False):
    """
    Process a single VTT file and write the cleaned content to the output file.
    
    Args:
        vtt_file_path (Path): Path to the VTT file
        outfile: File object for writing output
        verbose (bool): Whether to print detailed information
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if verbose:
            print(f"Reading file: {vtt_file_path}")
            
        with open(vtt_file_path, 'r', encoding='utf-8') as infile:
            content = infile.read()
            clean_text = clean_vtt_text(content)
            
            # Write file name as header
            outfile.write(f"\n=== {vtt_file_path.name} ===\n")
            outfile.write(clean_text)
            outfile.write('\n\n')
            
        print(f"Processed: {vtt_file_path.name}")
        return True
    except Exception as e:
        print(f"Error processing {vtt_file_path.name}: {str(e)}", file=sys.stderr)
        return False


def process_vtt_files(input_dir='.', output_file='combined_transcripts.txt', single_file=None, verbose=False):
    """
    Process VTT files and combine them into a single text file.
    
    Args:
        input_dir (str): Directory containing VTT files
        output_file (str): Name of the output file
        single_file (str): Optional single file to process instead of all VTT files
        verbose (bool): Whether to print detailed information
        
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
    
    # Get VTT files to process
    if single_file:
        single_file_path = input_path / single_file
        if not single_file_path.exists():
            print(f"Error: File '{single_file_path}' does not exist", file=sys.stderr)
            return 0
        vtt_files = [single_file_path]
        if verbose:
            print(f"Processing single file: {single_file_path.name}")
    else:
        vtt_files = list(input_path.glob('*.vtt'))
        if verbose:
            print(f"Found {len(vtt_files)} VTT files to process")
    
    if not vtt_files:
        print("No VTT files found to process", file=sys.stderr)
        return 0
    
    success_count = 0
    
    # Open output file in write mode
    with open(output_path, 'w', encoding='utf-8') as outfile:
        for vtt_file in vtt_files:
            if process_vtt_file(vtt_file, outfile, verbose):
                success_count += 1
    
    print(f"Successfully processed {success_count} out of {len(vtt_files)} files")
    print(f"Output written to: {output_path.absolute()}")
    
    return success_count


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert WebVTT subtitle files to plain text and combine them",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--input-dir',
        default='.',
        help="Directory containing VTT files"
    )
    
    parser.add_argument(
        '-o', '--output-file',
        default='combined_transcripts.txt',
        help="Output file name"
    )
    
    parser.add_argument(
        '-f', '--file',
        help="Process a single VTT file instead of all files in the directory"
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Display detailed processing information"
    )
    
    return parser.parse_args()


def main():
    """
    Main entry point for the script.
    """
    args = parse_arguments()
    
    success_count = process_vtt_files(
        input_dir=args.input_dir,
        output_file=args.output_file,
        single_file=args.file,
        verbose=args.verbose
    )
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
