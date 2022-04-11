import os
import os.path
import sys
import tarfile
import tempfile
import json
import hashlib
import shutil
import urllib.request
from subprocess import run

if len(sys.argv) < 2:
    print("Usage: unpack.py <log collector URL>")
    sys.exit(1)


class CollectorURLs:
    clusterEventsJSON = None
    clusterLogs = None
    infraEnvJSON = None

collector_url_base = os.path.abspath(sys.argv[1])
# TODO: implement me
#collectorURLs = NewCollectorURLs(collector_url_base)

collectorURLs = CollectorURLs()
collectorURLs.clusterEventsJSON = "http://assisted-logs-collector.usersys.redhat.com/files/2022-04-09_18:19:34_113b2bad-f09d-4b17-a37b-c06353df2253/cluster_113b2bad-f09d-4b17-a37b-c06353df2253_events.json"
collectorURLs.clusterLogs = "http://assisted-logs-collector.usersys.redhat.com/files/2022-04-09_18:19:34_113b2bad-f09d-4b17-a37b-c06353df2253/cluster_113b2bad-f09d-4b17-a37b-c06353df2253_logs.tar"
collectorURLs.infraEnvJSON = "http://assisted-logs-collector.usersys.redhat.com/files/2022-04-09_18:19:34_113b2bad-f09d-4b17-a37b-c06353df2253/infraenv_9edddd51-2060-47d6-9516-17cd66e2d20e_events.json"

dest_dir = tempfile.mkdtemp(prefix="loki_logs")
artifacts_dir = os.path.join(dest_dir, "artifacts")

print(f"Fetching files to {artifacts_dir}")
os.makedirs(artifacts_dir)

for field in ['clusterEventsJSON', 'clusterLogs', 'infraEnvJSON']:
    url = getattr(collectorURLs, field)
    filename = url.split("/")[-1]
    with urllib.request.urlopen(url) as response:
        dest_file = os.path.join(artifacts_dir, filename)
        with open(dest_file, mode="wb") as tmp_file:
            shutil.copyfileobj(response, tmp_file)
            print(f"Fetched {url} to {dest_file}")

if collectorURLs.clusterLogs:
    print(f"Unpacking logs")
    # extract the first tar file
    filename = collectorURLs.clusterLogs.split("/")[-1]
    logs_dst_dir = os.path.join(dest_dir, filename.split('.')[0])
    filepath = os.path.join(artifacts_dir, filename)
    file = tarfile.open(filepath)
    file.extractall(logs_dst_dir)
    file.close()

    for filename in os.listdir(logs_dst_dir):
        filepath = os.path.join(logs_dst_dir, filename)
        if not os.path.isfile(filepath):
            continue

        file = tarfile.open(filepath)
        print(f"{logs_dst_dir} - {filename} - {filepath}")
        file.extractall(logs_dst_dir)
        file.close()


print("Starting pod")
# Make sure configmap has path to dest_dir
shutil.copytree("podman", os.path.join(dest_dir, "podman"))
os.mkdir(os.path.join(dest_dir, "promtail-data"))
os.mkdir(os.path.join(dest_dir, "loki-data"))

pod_path = os.path.join(dest_dir, "podman/pod.yml")
run(["sed", "-i", f"s;foo;{dest_dir};g", pod_path])

run(["podman", "pod", "rm", "-f", "aitriage-to-loki"])
run(["podman", "play", "kube", pod_path])

print(f"Grafana URL: http://localhost:3000/explore")
