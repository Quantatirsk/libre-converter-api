#!/bin/bash
set -e

IMAGE="quantatrisk/libre-converter-api"
TAG="${1:-latest}"
PLATFORMS="linux/amd64,linux/arm64"

echo "Building ${IMAGE}:${TAG} for ${PLATFORMS}"

# Create buildx builder if not exists
if ! docker buildx inspect multiarch >/dev/null 2>&1; then
    echo "Creating buildx builder..."
    docker buildx create --name multiarch --use
fi

docker buildx use multiarch

# Build and push multi-platform image
docker buildx build \
    --platform "${PLATFORMS}" \
    --tag "${IMAGE}:${TAG}" \
    --push \
    .

echo "Done: ${IMAGE}:${TAG}"
