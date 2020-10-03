"""
Created by Epic at 10/3/20
"""
from pathlib import Path

code_path = Path(".")
fails = 0


class ListWithDefault(list):
    def __getitem__(self, item: int):
        try:
            return super().__getitem__(item)
        except IndexError:
            return None


def uses_spaces_for_indents(_, line: str, __):
    return [None, "Space indentation is not allowed"][ListWithDefault(line)[0] == " "]


def scan(last_line: str, current_line: str, next_line: str, line_id: int, file_name: str):
    global fails
    checks = [uses_spaces_for_indents]

    for check in checks:
        check_result = check(last_line, current_line, next_line)
        if check_result is not None:
            print(f"L{line_id+1}-F-{file_name}: {check_result}")
            fails += 1


def process_file(file_contents, file_name: str):
    splitted = file_contents.split("\n")
    splitted = ListWithDefault(splitted)
    for line_id in range(len(splitted)):
        last_line = splitted[line_id - 1] or None
        current_line = splitted[line_id]
        next_line = splitted[line_id + 1] or None
        scan(last_line, current_line, next_line, line_id, file_name)


for file in code_path.glob("*.py"):
    with file.open() as f:
        process_file(f.read(), str(file))
exit(fails)
