FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --chown=appuser:appuser server.py /app/server.py
USER 10001
EXPOSE 8080
CMD ["python", "/app/server.py"]
