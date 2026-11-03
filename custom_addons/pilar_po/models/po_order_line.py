from odoo import api, fields, models


class PilarPoItem(models.Model):
    _name = "pilar.po.item"
    _description = "Baris Komoditas Purchase Order"
    _order = "po_id, version_id, id"

    po_id = fields.Many2one(
        "pilar.po", string="PO", required=True, ondelete="cascade", index=True
    )
    version_id = fields.Many2one(
        "pilar.po.version", string="Versi PO", required=True,
        ondelete="cascade", index=True,
    )
    commodity_name = fields.Char(string="Nama Komoditas", required=True)
    quantity = fields.Float(string="Kuantitas", default=1.0, required=True)
    unit_name = fields.Char(string="Satuan", default="kg", required=True)
    quality_specification = fields.Char(string="Spesifikasi Mutu")

    order_state = fields.Selection(
        related="po_id.state", string="Status PO", store=True, readonly=True
    )
    customer_id = fields.Many2one(
        "pilar.customer", string="Pelanggan",
        related="po_id.customer_id", store=True, readonly=True,
    )
    delivery_date = fields.Date(
        string="Tanggal Kirim", related="version_id.delivery_date",
        store=True, readonly=True,
    )
    is_current_version = fields.Boolean(
        string="Versi Aktif", related="version_id.is_current",
        store=True, readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            version = self.env["pilar.po.version"].browse(vals.get("version_id"))
            if not version and vals.get("po_id"):
                po = self.env["pilar.po"].browse(vals["po_id"])
                version = po.current_version_id or po._ensure_current_version()
                vals["version_id"] = version.id
            if version and not vals.get("po_id"):
                vals["po_id"] = version.po_id.id
        return super().create(vals_list)
