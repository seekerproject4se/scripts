import os
import ast
import sys

class ModuleAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()
        self.issues = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)

def analyze_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=filepath)
    analyzer = ModuleAnalyzer()
    analyzer.visit(tree)
    return analyzer.imports, analyzer.issues

def find_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def main(directory):
    python_files = find_python_files(directory)
    all_imports = set()
    all_issues = []

    for filepath in python_files:
        imports, issues = analyze_file(filepath)
        all_imports.update(imports)
        all_issues.extend(issues)

    print("Imports found across the project:")
    for imp in sorted(all_imports):
        print(f"  - {imp}")

    if all_issues:
        print("\nIssues found:")
        for issue in all_issues:
            print(f"  - {issue}")
    else:
        print("\nNo issues found!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fixer.py <directory>")
    else:
        main(sys.argv[1])
