# =============================================================================
# InfraIQ Demo Container
# =============================================================================

FROM autonops/infraiq:latest

USER root

# Install ttyd from GitHub releases (not in apt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    less \
    tree \
    curl \
    && curl -fsSL https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd \
    && rm -rf /var/lib/apt/lists/*

# Create demo user
RUN useradd -m -s /bin/bash demo && \
    mkdir -p /home/demo/.infraiq && \
    chown -R demo:demo /home/demo

# Copy demo data
COPY --chown=demo:demo data/ /home/demo/demo-data/
COPY --chown=demo:demo samples/ /home/demo/samples/
COPY --chown=demo:demo motd.txt /etc/motd
COPY --chown=demo:demo bashrc /home/demo/.bashrc

# Set up demo environment
USER demo
WORKDIR /home/demo

# Expose ttyd port
EXPOSE 7681

# Start ttyd with bash
CMD ["ttyd", "-W", "-t", "fontSize=14", "-t", "theme={'background':'#0a0a0a','foreground':'#e0e0e0'}", "bash", "-l"]