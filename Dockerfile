FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/app/.cache/hf_public \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    PORT=7860

WORKDIR /app
RUN useradd --uid 1000 --create-home user
COPY --chown=user:user . /app
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.1+cpu'
RUN pip install --no-cache-dir -r requirements-deploy.txt
RUN mkdir -p /app/data /app/.cache /app/tmp && chown -R user:user /app/data /app/.cache /app/tmp
USER user

# Both public model snapshots are pinned. The release bundle contains the
# extracted source corpus, frozen index, gold and saved retrieval results.
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python scripts/prepare_models.py
RUN python scripts/public_data.py fetch
RUN python -c "from ncd_gemma.retrieval import verify_data; verify_data()"

EXPOSE 7860
# Load the CPU encoder/index before accepting questions so the first visitor
# does not time out while waiting for a 1-5 minute cold start.
CMD ["sh", "-c", "python -c 'from ncd_gemma.server import get_agent; get_agent()' && exec python -m ncd_gemma.cli serve --host 0.0.0.0 --port ${PORT:-7860}"]
