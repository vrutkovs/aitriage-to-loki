#!/usr/bin/env bash
set -euo pipefail
set -o xtrace
BASE_DIR="${BASE_DIR:-/tmp/loki_logs}"
mkdir -p "${BASE_DIR}"

if [ -z "${1}" ]; then
	echo "Usage: unpack.sh <cluster_<id>_logs.tar url>"
	exit 1
fi
LOG_TAR_URL="${1}"
LOG_FILENAME="$(echo $LOG_TAR_URL | grep / | cut -d/ -f6-)"
if [ -z "${LOG_FILENAME}" ]; then
	echo "Invalid log filaname found"
	exit 1
fi

LOG_TAR_PATH="${BASE_DIR}/${LOG_FILENAME}"
rm -rf "${LOG_TAR_PATH}" || true
curl -Ls -o "${LOG_TAR_PATH}" "${1}"

echo "Extracting files from ${LOG_TAR_PATH}"

CLUSTER_ID=$(echo ${LOG_TAR_PATH} | awk -F "cluster_|_logs.tar" '{print $2}')

if [ -z ${CLUSTER_ID} ]; then
  echo "Failed to parse CLUSTER_ID from ${LOG_TAR_PATH}"
  exit 1
fi

WORK_DIR=${BASE_DIR}/cluster_${CLUSTER_ID}_logs
rm -rf ${WORK_DIR}
mkdir -p ${WORK_DIR}
pushd ${WORK_DIR}

  tar -xvf ${LOG_TAR_PATH} -C ${WORK_DIR}

  #Extract hosts/controller tar.gz
  for f in ${WORK_DIR}/*.tar.gz
  do
    echo "Extracting ${f}"
    tar -C ${WORK_DIR} -xvzf ${f}
    #remove the tar file from work dir
    rm -rf ${f}

  done


  #Extract internal tar.gz (must-gather/log-bundle)
  for f in `find ${WORK_DIR} | grep tar.gz`
  do
    echo "Extracting ${f}"
    tar -C ${WORK_DIR} -xvzf ${f}
    #remove the tar file from work dir
    rm -rf ${f}
  done
popd

#Start loki / promtail / grafana pod
rm -rf "${BASE_DIR}/podman"
cp -rvf "$(pwd)/podman" "${BASE_DIR}/podman"
mkdir -p "${BASE_DIR}/promtail-data"
mkdir -p "${BASE_DIR}/loki-data"

sed -i "s;foo;${BASE_DIR};g" "${BASE_DIR}/podman/pod.yml"
podman pod rm -f aitriage-to-loki || true
podman play kube "${BASE_DIR}/podman/pod.yml"

echo "Open Grafana at http://localhost:3000/explore?orgId=1&left=%7B%22datasource%22:%22Loki%22,%22queries%22:%5B%7B%22refId%22:%22A%22%7D%5D,%22range%22:%7B%22from%22:%22now-24h%22,%22to%22:%22now%22%7D%7D"
