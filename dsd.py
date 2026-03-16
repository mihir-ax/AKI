import os

# Extensions to include
EXTENSIONS = (".ts", ".tsx", ".jsx", ".js", ".html", ".css", ".json", ".cjs", ".py")

# Ignore folders & files
IGNORE_DIRS = {"node_modules", "dist", ".git", "music", "venv", "__pycache__"}
IGNORE_FILES = {"package-lock.json", "a.txt"}

ROOT_DIR = os.getcwd()
OUTPUT_FILE = os.path.join(ROOT_DIR, "project_dump.txt")

def print_tree(start_path, file):
    for root, dirs, files in os.walk(start_path):
        # Remove ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        level = root.replace(start_path, "").count(os.sep)
        indent = "│   " * level + "├── "
        file.write(f"{indent}{os.path.basename(root)}/\n")

        subindent = "│   " * (level + 1) + "├── "
        for f in files:
            if f not in IGNORE_FILES:
                file.write(f"{subindent}{f}\n")

def write_files_content(start_path, file):
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for name in files:
            if name in IGNORE_FILES:
                continue

            if name.endswith(EXTENSIONS):
                full_path = os.path.join(root, name)
                relative_path = os.path.relpath(full_path, start_path)

                file.write("\n" + "="*80 + "\n")
                file.write(f"FILE PATH: {relative_path}\n")
                file.write("="*80 + "\n")

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        file.write(content + "\n")
                except Exception as e:
                    file.write(f"Error reading file: {e}\n")

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write("PROJECT TREE STRUCTURE\n")
        file.write("="*80 + "\n")
        print_tree(ROOT_DIR, file)

        file.write("\n\nFILE CONTENT DUMP\n")
        file.write("="*80 + "\n")
        write_files_content(ROOT_DIR, file)

    print("✅ project_dump.txt created successfully!")

if __name__ == "__main__":
    main()
