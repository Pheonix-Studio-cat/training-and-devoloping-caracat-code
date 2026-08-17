# Container for the Caracat Code Space.
#
# The build context is assembled by .github/workflows/sync-to-space.yml, which
# copies src/, interface/ and prompts/ next to this file. Nothing is duplicated
# in git: the personality and the page have exactly one source.

FROM python:3.12-slim

# Hugging Face runs Spaces as uid 1000. Creating that user here means the files
# are owned by the account that will run them, rather than by root.
RUN useradd --create-home --uid 1000 caracat
USER caracat
WORKDIR /home/caracat/app

# The only dependency. Everything else in this project is standard library --
# which is why this image needs no build tools and no lockfile.
RUN pip install --no-cache-dir --user "PyYAML>=6.0"

COPY --chown=caracat:caracat src/ ./src/
COPY --chown=caracat:caracat interface/ ./interface/
COPY --chown=caracat:caracat prompts/ ./prompts/
COPY --chown=caracat:caracat app.py ./app.py

ENV PYTHONPATH=/home/caracat/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/caracat/.local/bin:$PATH \
    PORT=7860

EXPOSE 7860

CMD ["python", "app.py"]
