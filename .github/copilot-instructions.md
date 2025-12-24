# Copilot instructions (docker_odoo_clean)

## Big picture
- This repo is an **Odoo 19** deployment running in Docker Compose: Postgres 15 (`db`) + Odoo (`odoo`). See [docker-compose.yml](../docker-compose.yml) and [Dockerfile](../Dockerfile).
- Custom Odoo addons live in `addons/` and are mounted into the container at `/mnt/extra-addons`.
- Runtime state is persisted via bind mounts:
  - `postgres_data/` (Postgres data directory)
  - `odoo_data/` (Odoo filestore, sessions, etc.)

## Local dev workflow (Windows)
- Start/stop:
  - `docker compose up -d`
  - `docker compose logs -f odoo`
  - `docker compose restart odoo`
- **Database is pinned to a single name**: `Odoo`.
  - Config in [config/odoo.conf](../config/odoo.conf): `db_name=Odoo`, `dbfilter=^Odoo$`, `list_db=False`.
  - Result: no database selector; requests always hit DB `Odoo`.
- Initialize modules into an empty DB (from [README.md](../README.md)):
  - `docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf --db_host db --db_port 5432 --db_user odoo --db_password odoo_pwd -d Odoo -i website,website_sale,smileliving --stop-after-init`
- Upgrade a specific module after code changes:
  - `docker compose exec -T odoo odoo -c /etc/odoo/odoo.conf -d Odoo -u <module_name> --stop-after-init`

## Addon conventions (Odoo)
- Each addon follows standard Odoo layout:
  - `__manifest__.py` (dependencies, `data` XML/CSV, and `assets` bundles)
  - `models/`, `views/`, `security/`, `data/`, `wizard/`, `report/`, `static/`
- Example manifests with patterns:
  - Backend asset bundling and external deps: [addons/base_accounting_kit/__manifest__.py](../addons/base_accounting_kit/__manifest__.py)
  - Post init hooks: [addons/base_account_budget/__manifest__.py](../addons/base_account_budget/__manifest__.py)
  - Frontend website assets: [addons/smileliving/__manifest__.py](../addons/smileliving/__manifest__.py)
- When adding new JS/CSS/QWeb assets, prefer registering them via the module’s `assets` section (e.g. `web.assets_backend` / `web.assets_frontend`) rather than ad-hoc injection.

## Web client / JS patterns (Odoo 17+ style)
- JS modules use the modern Odoo/OWL module system (`/** @odoo-module **/`).
- Custom views/controllers are registered via the registry:
  - View registration example: [addons/base_accounting_kit/static/src/js/KanbanController.js](../addons/base_accounting_kit/static/src/js/KanbanController.js)
    - `registry.category("views").add("custom_kanban", customKanbanView)`
    - Uses OWL state (`useState`) and services (`useService("orm")`, `useService("action")`).
- When calling server methods from JS, this repo typically uses `this.orm.call(<model>, <method>, <args>)`.

## Helper scripts
- To copy an external module folder into `addons/` on Windows, use [copy_module.ps1](../copy_module.ps1):
  - `./copy_module.ps1 -SourcePath "C:\path\to\module"`

## Dependencies
- Odoo container image is built from `odoo:19.0` and extended for Python deps in [Dockerfile](../Dockerfile).
- Some addons declare Python `external_dependencies` (example: `openpyxl`, `ofxparse`, `qifparse` in [addons/base_accounting_kit/__manifest__.py](../addons/base_accounting_kit/__manifest__.py)).
  - If import errors occur at runtime, add missing packages to the Docker image (update [Dockerfile](../Dockerfile) and rebuild with `docker compose build`).

## What not to change casually
- Avoid editing `postgres_data/` and `odoo_data/` by hand; treat them as local runtime state.
- Keep the fixed DB name behavior unless you also update [config/odoo.conf](../config/odoo.conf) and docs; many workflows assume DB `Odoo`.
