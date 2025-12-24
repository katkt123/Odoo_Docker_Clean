FROM odoo:19.0

USER root
RUN python3 -m pip install --no-cache-dir --break-system-packages qifparse
USER odoo
