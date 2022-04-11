import os
import os.path
import shutil
from subprocess import run

dest_dir = os.path.join("/tmp", "aitriage-loki")
print(f"Re-creating {dest_dir}")
shutil.rmtree(dest_dir, ignore_errors=True, onerror=None)
os.makedirs(os.path.join(dest_dir, "promtail-data"))

for subpath in ["promtail-data", "loki-data"]:
    subdir = os.path.join(dest_dir, subpath)
    shutil.rmtree(subdir, ignore_errors=True, onerror=None)
    os.makedirs(subdir)

print(f"Starting loki pod")
podman_files_dir = os.path.join(dest_dir, "podman")
shutil.rmtree(podman_files_dir, ignore_errors=True, onerror=None)
shutil.copytree("podman", podman_files_dir)
pod_path = os.path.join(dest_dir, "podman/pod.yml")
run(["sed", "-i", f"s;foo;{dest_dir};g", pod_path])

run(["podman", "pod", "rm", "-f", "aitriage-to-loki"])
run(["podman", "play", "kube", pod_path])

print(f"Grafana URL: http://localhost:3000/explore")
