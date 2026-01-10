# =============================================================================
# InfraIQ Demo Container
# =============================================================================

FROM autonops/infraiq:latest

USER root

# Install ttyd
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim less tree curl \
    && curl -fsSL https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd \
    && rm -rf /var/lib/apt/lists/*

# Make infraiq home directory traversable and files readable/executable
RUN chmod o+x /home/infraiq && \
    chmod -R o+rX /home/infraiq/.local

# Create wrapper script that sets environment and calls real infraiq
RUN echo '#!/bin/bash' > /usr/local/bin/infraiq && \
    echo 'export PYTHONPATH="/home/infraiq/.local/lib/python3.11/site-packages:$PYTHONPATH"' >> /usr/local/bin/infraiq && \
    echo 'exec /home/infraiq/.local/bin/infraiq "$@"' >> /usr/local/bin/infraiq && \
    chmod +x /usr/local/bin/infraiq

# Create demo user
RUN useradd -m -s /bin/bash demo && \
    mkdir -p /home/demo/.infraiq && \
    chown -R demo:demo /home/demo

# Copy demo data
COPY --chown=demo:demo data/ /home/demo/demo-data/
COPY --chown=demo:demo samples/ /home/demo/samples/
COPY --chown=demo:demo motd.txt /etc/motd
COPY --chown=demo:demo bashrc /home/demo/.bashrc

USER demo
WORKDIR /home/demo

EXPOSE 7681

ENTRYPOINT []
CMD ["ttyd", "-W", "-t", "fontSize=14", "-t", "theme={'background':'#0a0a0a','foreground':'#e0e0e0'}", "bash", "-l"]
