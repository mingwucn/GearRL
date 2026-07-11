FROM mambaorg/micromamba:2.4.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment-ai.lock /tmp/environment-ai.lock
COPY --chown=$MAMBA_USER:$MAMBA_USER requirements-ai-pip.txt /tmp/requirements-ai-pip.txt
RUN micromamba create --yes --name ai --file /tmp/environment-ai.lock \
    && micromamba run --name ai python -m pip install --require-hashes --only-binary=:all: --requirement /tmp/requirements-ai-pip.txt \
    && micromamba clean --all --yes

WORKDIR /workspace
COPY --chown=$MAMBA_USER:$MAMBA_USER . /workspace

ENTRYPOINT ["micromamba", "run", "--no-capture-output", "--name", "ai"]
CMD ["make", "paper-verify"]
