"""
Created by Epic at 9/4/20
"""
from pathlib import Path
from subprocess import check_output
import hashlib

version_file = Path("speedcord/values.py")
last_hash_file = Path(".github/tools/last_publish_hash.hash")

with last_hash_file.open("r+") as f:
    last_hash = f.read()


def get_hash(file):
    hash_md5 = hashlib.md5()
    with file.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


dist_path = Path("dist/")

dist_output = list(dist_path.glob("*"))[0]

new_hash = get_hash(dist_output)
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
    new_lines.append("\n")

with version_file.open("w") as f:
    f.writelines(new_lines)
