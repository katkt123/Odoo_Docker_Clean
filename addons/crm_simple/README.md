# CRM Simple (Odoo 19)

A tiny example module that extends **CRM Leads** with 2 custom fields:
- `HK Reference` (Char)
- `HK Note` (Text)

## Why this module exists

Odoo already ships the core module named **`crm`**.
In this repo there was a folder `addons/crm/` with an empty `__manifest__.py`, which can:
- shadow Odoo's real `crm` addon, and/or
- break module loading

So this custom module uses a unique technical name: **`crm_simple`**.

## Install / Upgrade

- Install from Apps: search `CRM Simple`

Or CLI (inside container):

```bash
odoo -c /etc/odoo/odoo.conf -d odoo_clean -i crm_simple --stop-after-init
# upgrade after changes
odoo -c /etc/odoo/odoo.conf -d odoo_clean -u crm_simple --stop-after-init
```
