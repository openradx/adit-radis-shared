FROM gitpod/workspace-python-3.12

USER gitpod

ENV NVM_DIR $HOME/.nvm
ENV NVM_VERSION 0.39.7
ENV NODE_VERSION 20.12.2

# Node is not available in in the Gitpod Python image, so we install is manually
RUN mkdir $NVM_DIR && \ 
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v$NVM_VERSION/install.sh | bash && \
    . $NVM_DIR/nvm.sh && \
    nvm install $NODE_VERSION && \
    nvm alias default $NODE_VERSION && \
    nvm use default

RUN python3 -m pip install --user pipx && \
    python3 -m pipx ensurepath

RUN python3 -m pipx install invoke && \
    invoke --print-completion-script=bash >> $HOME/.bash_completion

RUN python3 -m pipx install playwright && playwright install --with-deps chromium

ENV NODE_PATH $NVM_DIR/v$NODE_VERSION/lib/node_modules
ENV PATH $NVM_DIR/versions/node/v$NODE_VERSION/bin:$PATH

# Poetry is already installed in the base Gitpod Python image,
# but we make sure uses the latest version and make bash completions available
RUN poetry self update && \
    poetry completions bash >> ~/.bash_completion
