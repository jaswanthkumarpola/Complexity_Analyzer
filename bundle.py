import os

def bundle_project(source_dir, output_file):
    # Directories to skip (keeps the context window clean)
    ignore_dirs = {
        '.git', '.venv', 'venv', 'env', '__pycache__', 
        'node_modules', 'mlruns', '.idea', '.vscode'
    }
    
    # File extensions to skip (binaries, data files, models)
    ignore_exts = {
        '.pyc', '.pdf', '.png', '.jpg', '.jpeg', '.zip', 
        '.tar', '.gz', '.pkl', '.h5', '.sqlite', '.db', '.csv', '.exe'
    }

    print(f"Bundling project from {os.path.abspath(source_dir)}...")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(source_dir):
            # Modify dirs in-place to prevent os.walk from descending into ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                # Skip the output file itself and any ignored extensions
                if ext in ignore_exts or file == output_file or file == 'bundle.py':
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)

                try:
                    # Attempt to read as a text file
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()

                    # Write LLM-friendly separators and file paths
                    outfile.write(f"{'='*50}\n")
                    outfile.write(f"File: {rel_path}\n")
                    outfile.write(f"{'='*50}\n")
                    
                    # Use markdown code blocks for clean syntax highlighting
                    lang = ext.lstrip('.') if ext else 'text'
                    outfile.write(f"```{lang}\n")
                    outfile.write(content)
                    
                    # Ensure the block ends cleanly
                    if not content.endswith('\n'):
                        outfile.write('\n')
                    outfile.write("```\n\n")
                    
                except UnicodeDecodeError:
                    # Failsafe for binary files missing from the ignore_exts list
                    print(f"Skipped binary/unreadable file: {rel_path}")
                except Exception as e:
                    print(f"Error reading {rel_path}: {e}")

    print(f"Success! Project bundled into: {output_file}")

if __name__ == "__main__":
    # Bundles the current directory into 'claude_context.txt'
    bundle_project('.', 'claude_context.txt')