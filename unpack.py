import os
import os.path
import sys
import re
import tarfile
import tempfile
import json
import hashlib
import shutil
import urllib.request
from subprocess import run

if len(sys.argv) < 2:
    print("Usage: unpack.py http://assisted-logs-collector.usersys.redhat.com/files/<log collector hash>")
    sys.exit(1)


class CollectorURLs:
    clusterEventsJSON = None
    clusterLogs = None
    infraEnvJSON = None

def newCollectorUrls(url_base):
    cURL = CollectorURLs()

    cluster_events_pattern = re.compile(r'cluster_\S+_events.json')
    infraenv_events_pattern = re.compile(r'infraenv_\S+_events.json')

    with urllib.request.urlopen(url_base) as response:
        data = response.read()
        encoding = response.info().get_content_charset('utf-8')
        JSON_object = json.loads(data.decode(encoding))
        for fileObj in JSON_object:
            name = fileObj.get("name")
            if not name:
                continue
            if name.endswith("_logs.tar"):
                cURL.clusterLogs = url_base + "/" + name
            if cluster_events_pattern.match(name):
                cURL.clusterEventsJSON = url_base + "/" + name
            if infraenv_events_pattern.match(name):
                cURL.infraEnvJSON = url_base + "/" + name

    if not cURL.clusterEventsJSON:
        raise Exception("Failed to find cluster events JSON")
    if not cURL.clusterLogs:
        raise Exception("Failed to find cluster logs archive")
    if not cURL.infraEnvJSON:
        raise Exception("Failed to find infra events JSON")
    return cURL

collectorURLs = newCollectorUrls(sys.argv[1])

dest_dir = tempfile.mkdtemp(prefix="loki_logs_")
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
