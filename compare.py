import difflib

def detailed_diff(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        file1_lines = f1.readlines()
        file2_lines = f2.readlines()

    diff = difflib.ndiff(file1_lines, file2_lines)
    for line in diff:
        # Output all the lines, including unchanged lines with context
        if line.startswith('- ') or line.startswith('+ ') or line.startswith('? '):
            print(line.rstrip())

file1 = 'search80.py'
file2 = 'search79.py'
detailed_diff(file1, file2)
