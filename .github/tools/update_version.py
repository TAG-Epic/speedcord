"""
Created by Epic at 9/4/20
"""
from pathlib import Path
from subprocess import check_output

version_file = Path("speedcord/values.py")
last_hash_file = Path(".github/tools/last_publish_hash.hash")


with last_hash_file.open("r+") as f:
    last_hash = f.read()

new_hash = check_output("sha256sum dist/*.egg").decode("utf-8").split(" ")[0]
if last_hash == new_hash:
    exit(0)
with last_hash_file.open("w+") as f:
    f.write(new_hash)

last_commit = check_output(["git", "log", "-1", "--pretty=%B"]).decode("utf-8")

is_major = last_commit.lower().startswith("major:")

with version_file.open("r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("version = "):
        version_text = line[len("version = "):]
        old_version = eval(version_text)
        old_version_splitted = old_version.split(".")
        version_tuple = [int(i) for i in old_version_splitted]
        if is_major:
            version_tuple[1] += 1
        else:
            version_tuple[2] += 1
        new_version = f"version = \"{'.'.join([str(i) for i in version_tuple])}\""
        new_lines.append(new_version)
    else:
        new_lines.append(line)

with version_file.open("w") as f:
    f.writelines(new_lines)
