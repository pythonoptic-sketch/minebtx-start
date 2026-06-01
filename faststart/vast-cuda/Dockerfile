FROM nvidia/cuda:12.6.3-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
  && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash miner

COPY entrypoint.sh /usr/local/bin/btx-faststart-entrypoint
RUN chmod 0755 /usr/local/bin/btx-faststart-entrypoint

USER miner
WORKDIR /home/miner

ENV PATH="/home/miner/.local/bin:/home/miner/.dexbtx-miner/bin:${PATH}" \
    INSTALLER_URL="https://drinknile.com/install.sh" \
    BTX_SOLVER_BACKEND="cuda" \
    BTX_WORKER="vast-cuda"

ENTRYPOINT ["/usr/local/bin/btx-faststart-entrypoint"]
