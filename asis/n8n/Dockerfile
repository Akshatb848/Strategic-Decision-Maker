FROM n8nio/n8n:latest

USER root
RUN npm install -g n8n-nodes-langfuse || true

# Custom entrypoint: imports all workflow JSONs from /workflows on first boot
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER node

ENV N8N_PORT=5678 \
    N8N_PROTOCOL=http \
    N8N_HOST=0.0.0.0 \
    # Regular mode — no separate worker container required
    EXECUTIONS_MODE=regular \
    NODE_ENV=production \
    N8N_SKIP_SETUP_WIZARD=true \
    N8N_SKIP_WEBHOOK_DEREGISTRATION_SHUTDOWN=true

EXPOSE 5678

ENTRYPOINT ["/entrypoint.sh"]
