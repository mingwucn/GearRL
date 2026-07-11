FROM mambaorg/micromamba:2.4.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment-ai.yml /tmp/environment-ai.yml
COPY --chown=$MAMBA_USER:$MAMBA_USER requirements-ai-pip.txt /tmp/requirements-ai-pip.txt
RUN cd /tmp && micromamba create --yes --name ai --file /tmp/environment-ai.yml && micromamba clean --all --yes

WORKDIR /workspace
COPY --chown=$MAMBA_USER:$MAMBA_USER . /workspace

ENTRYPOINT ["micromamba", "run", "--no-capture-output", "-n", "ai", "python", "main.py"]
