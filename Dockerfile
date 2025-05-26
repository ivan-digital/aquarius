FROM aquarius-base AS builder

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
RUN mkdir -p /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update
RUN apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && rm -rf /var/lib/apt/lists/*

ARG DOCKER_GID=0
RUN if ! getent group poetry > /dev/null; then addgroup --system poetry; fi
RUN if ! id -u poetry > /dev/null 2>&1; then \
    useradd --system --gid poetry --home-dir /home/poetry --shell /bin/bash --create-home poetry; \
    fi

RUN usermod -aG docker poetry
RUN usermod -aG sudo poetry
RUN echo 'poetry ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

RUN if ! getent group poetry > /dev/null; then groupadd poetry; fi
RUN if ! id -u poetry > /dev/null 2>&1; then useradd -r -g poetry -s /bin/false poetry; fi

RUN mkdir -p /home/poetry/.config && \
    mkdir -p /home/poetry/.cache && \
    chown -R poetry:poetry /home/poetry/.config /home/poetry/.cache

WORKDIR /app
RUN mkdir -p /app && chown -R poetry:poetry /app

USER poetry

COPY --chown=poetry:poetry pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.in-project true --local

RUN poetry install --no-interaction --no-ansi --no-root

COPY --chown=poetry:poetry config.yaml .

ARG COMPONENT
COPY --chown=poetry:poetry app ./app

RUN poetry install --no-interaction --no-ansi

ENV APP_COMPONENT=${COMPONENT}
CMD ["poetry", "run", "python", "-m", "app.main"]
