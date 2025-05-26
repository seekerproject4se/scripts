import difflib

def compare_files(file1_path, file2_path):
    with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
        file1_lines = file1.readlines()
        file2_lines = file2.readlines()

    diff = difflib.unified_diff(file1_lines, file2_lines, fromfile='search86.py', tofile='search86b.py')

    for line in diff:
        print(line, end='')

if __name__ == '__main__':
    file1_path = 'search86.py'  # Path to the first file
    file2_path = 'search86b.py'  # Path to the second file
    compare_files(file1_path, file2_path)
