FROM n8nio/n8n:latest
USER root
RUN npm install -g n8n-nodes-langfuse || true
USER node
ENV N8N_PORT=5678 \
    N8N_PROTOCOL=http \
    N8N_HOST=0.0.0.0 \
    EXECUTIONS_MODE=queue \
    QUEUE_BULL_REDIS_HOST=redis \
    NODE_ENV=production
EXPOSE 5678
