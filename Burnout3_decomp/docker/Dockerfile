# Build image for the Burnout 3 matching decomp.
# Build with --platform linux/amd64 so wibo can run the Windows CodeWarrior compiler (Rosetta/QEMU on Apple Silicon).
FROM ubuntu:24.04

ARG WIBO_VERSION=1.2.0
ARG OBJDIFF_VERSION=v3.8.2

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        binutils-mips-linux-gnu ca-certificates curl git ninja-build python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/local/bin/wibo \
        https://github.com/decompals/wibo/releases/download/${WIBO_VERSION}/wibo-i686 \
    && chmod +x /usr/local/bin/wibo \
    && curl -fsSL -o /usr/local/bin/objdiff-cli \
        https://github.com/encounter/objdiff/releases/download/${OBJDIFF_VERSION}/objdiff-cli-linux-x86_64 \
    && chmod +x /usr/local/bin/objdiff-cli

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /work
