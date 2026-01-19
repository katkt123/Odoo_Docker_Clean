1. Start docker
2. Open terminal -> Docker-compose up
3. Open config/odoo.conf -> Paste : addons_path = /usr/lib/python3/dist-packages/odoo/addons,/var/lib/odoo/.local/share/Odoo/addons/19.0,/usr/lib/python3/dist-packages/addons,/mnt/extra-addons
4. Docker-compose start odoo -> docker-compose up -d -> start

## Run

### 1) Start containers

`docker compose up -d`

### 2) Fixed database name (IMPORTANT)

This project is configured to use a single fixed Postgres database: `odoo_clean`.

- Config: `config/odoo.conf` sets `db_name=odoo_clean`, `dbfilter=^odoo_clean$`, and `list_db=False`.
- Result: there is no database selector screen; all web requests go to the same DB.

When you clone/pull this repo on another machine, you must also create/restore the database `odoo_clean`.

#### Initialize modules (empty DB)

If `odoo19` exists but has no modules installed, install required modules:

`docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf --db_host db --db_port 5432 --db_user odoo --db_password odoo_pwd -d odoo_clean -i website,website_sale,smileliving --stop-after-init`

#### Restore from a dump (recommended for same data)

Git does not include database data. To share the same website content, export a dump from the source machine and restore it into database `odoo_clean`.

IMPORTANT: Do not commit/copy the raw `postgres_data/` folder between machines. Use a Postgres dump/restore instead.

