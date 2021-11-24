#############
# Dependencies
#
#  This base stage just installs the dependencies required for production
#  without any development deps.
ARG PYTHON_VER=3.8
FROM l3pvap1561.1dc.com:8083/library/python:${PYTHON_VER} AS base

WORKDIR /usr/src/app

# Install poetry for dep management
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH="$PATH:/root/.poetry/bin"
RUN poetry config virtualenvs.create false

# Install project manifest
COPY pyproject.toml .

# Install poetry.lock from which to build
COPY poetry.lock .

# Install production dependencies
RUN poetry install --no-dev

############
# Unit Tests
#
# This test stage runs true unit tests (no outside services) at build time, as
# well as enforcing codestyle and performing fast syntax checks. It is built
# into an image with docker-compose for running the full test suite.
FROM base AS test

# Install dev dependencies
RUN poetry install

# Copy in the application source and everything not explicitly banned by
# .dockerignore
COPY . .

# Install paloalto_log_profile_update into the docker container
RUN poetry install

############
# Linting
#
# Runs all necessary linting and code checks
RUN echo 'Running Flake8' && \
    flake8 . && \
    echo 'Running Black' && \
    black --check --diff . && \
    echo 'Running Pylint' && \
    find . -name '*.py' | xargs pylint  && \
    echo 'Running Yamllint' && \
    yamllint . && \
    echo 'Running pydocstyle' && \
    pydocstyle . && \
    echo 'Running Bandit' && \
    bandit --recursive ./ --configfile .bandit.yml

RUN pytest --cov paloalto_log_profile_update --color yes -vvv tests

# Run full test suite including integration
ENTRYPOINT ["pytest"]

# Default to running colorful, verbose pytests
CMD ["--cov=paloalto_log_profile_update", "--color=yes", "-vvv"]

#############
# Final image
#
# This creates a runnable CLI container
FROM python:3.8-slim AS cli

WORKDIR /usr/src/app

COPY --from=base /usr/src/app /usr/src/app
COPY --from=base /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

COPY ./paloalto_log_profile_update .

ENTRYPOINT ["python"]
