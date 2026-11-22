# The container of control/chrome/ci/Dockerfile plus what pack.py signs with (brief 18c-b, item 2).
# A distribution package, never a pip one. The proof itself runs with --network none.
ARG BASE=aresos-chrome-fixture
FROM ${BASE}
RUN apt-get update -qq && apt-get install -y --no-install-recommends python3-cryptography && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["bash","control/chrome/ci/install/run.sh"]
