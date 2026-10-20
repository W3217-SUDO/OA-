# 构建时由管理员传入 node:22-bookworm-slim@sha256:...，运行配置同样固定镜像摘要。
ARG RUNNER_BASE
FROM ${RUNNER_BASE}
ARG RUNNER_BASE
RUN printf '%s' "$RUNNER_BASE" | grep -Eq '@sha256:[a-f0-9]{64}$' \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3 bash ca-certificates \
    && ln -s /usr/local/bin/node /usr/bin/node \
    && rm -rf /var/lib/apt/lists/*
LABEL com.huzhi.skill-runner="1"
ENV HOME=/work TMPDIR=/tmp LANG=C.UTF-8 PATH=/usr/bin:/bin
USER 65534:65534
WORKDIR /work
ENTRYPOINT ["/usr/bin/node"]
