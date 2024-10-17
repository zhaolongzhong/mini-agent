import re
from pathlib import Path

import docker

from .utils import close_logger, setup_logger

ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

DOCKERFILE_BASE = """
# Use an official Python runtime as a parent image
FROM --platform={platform} ubuntu:22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user named nonroot
RUN adduser --disabled-password --gecos 'Nonroot User' nonroot

# Install system dependencies
RUN apt-get update && apt-get install -yq --fix-missing\
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    python-is-python3 \
    jq \
    curl \
    sudo \
    vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-l", "-c"]

# Set work directory
WORKDIR /home

# Copy project files, include entrypoint.sh
COPY . /home

# Change ownership of /home to nonroot
RUN chown -R nonroot:nonroot /home

# Switch to nonroot user
USER nonroot

# Add ~/.local/bin to PATH
ENV PATH="/home/nonroot/.local/bin:$PATH"
"""


def list_images(client: docker.DockerClient):
    """
    List all images from the Docker client.
    """
    return {tag for i in client.images.list(all=True) for tag in i.tags}


def get_dockerfile_base(platform: str = "arm64") -> str:
    if "arm64" in platform:
        platform = "linux/arm64/v8"
    elif "x86_64" in platform:
        platform = "linux/x86_64"
    return DOCKERFILE_BASE.format(platform=platform)


def build_image(
    client: docker.DockerClient,
    image_name: str,
    build_dir: Path,
    force_build: bool = False,
):
    existing_images = list_images(client)
    if not force_build:
        if image_name in existing_images or f"{image_name}:latest" in existing_images:
            return
    else:
        print(f"Force build: {image_name}")
    logger = setup_logger(image_name, build_dir / "build_image.log")

    try:
        logger.debug(f"Start build image ...{image_name}, existing_images: {existing_images}")
        dockerfile = get_dockerfile_base()
        dockerfile_path = build_dir / "Dockerfile"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile)

        response = client.api.build(
            path=str(build_dir),
            tag=image_name,
            rm=True,
            forcerm=True,
            decode=True,
            nocache=False,
        )
        buildlog = ""
        for chunk in response:
            if "stream" in chunk:
                # Remove ANSI escape sequences from the log
                chunk_stream = ansi_escape.sub("", chunk["stream"])
                logger.info(chunk_stream.strip())
                buildlog += chunk_stream
            elif "errorDetail" in chunk:
                logger.error(f"Error: {ansi_escape.sub('', chunk['errorDetail']['message'])}")
                raise docker.errors.BuildError(chunk["errorDetail"]["message"], buildlog)
        logger.info("Image built successfully.")
    except docker.errors.BuildError as e:
        logger.error(f"docker.errors.BuildError during {image_name}: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error building image {image_name}: {e}")
        raise e
    finally:
        close_logger(logger)
