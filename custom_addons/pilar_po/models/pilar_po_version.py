from odoo import api, fields, models


class PilarPoVersion(models.Model):
    _name = "pilar.po.version"
    _description = "Versi Dokumen Purchase Order"
    _order = "po_id, version_number desc"

    po_id = fields.Many2one(
        "pilar.po", string="Purchase Order", required=True,
        ondelete="cascade", index=True,
    )
    created_by = fields.Many2one(
        "res.users", string="Dibuat Oleh",
        default=lambda self: self.env.user, required=True,
    )
    version_number = fields.Integer(string="Nomor Versi", default=1, required=True)
    delivery_date = fields.Date(string="Tanggal Pengiriman")
    delivery_address = fields.Text(string="Alamat Pengiriman")
    correction_note = fields.Text(string="Catatan Perbaikan")
    is_current = fields.Boolean(string="Versi Aktif", default=False)
    created_at = fields.Datetime(
        string="Dibuat Pada", default=fields.Datetime.now, required=True
    )

    item_ids = fields.One2many("pilar.po.item", "version_id", string="Baris Pesanan")
    validation_ids = fields.One2many(
        "pilar.po.validation", "version_id", string="Hasil Validasi"
    )

    _sql_constraints = [
        ("po_version_unique", "unique(po_id, version_number)",
         "Nomor versi PO harus unik untuk setiap PO."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            po = self.env["pilar.po"].browse(vals.get("po_id"))
            if po:
                if not vals.get("version_number"):
                    vals["version_number"] = max(
                        po.version_ids.mapped("version_number") or [0]
                    ) + 1
                if not vals.get("delivery_date"):
                    vals["delivery_date"] = po.delivery_date
                if not vals.get("delivery_address"):
                    vals["delivery_address"] = po.delivery_address
                if "is_current" not in vals:
                    vals["is_current"] = not po.version_ids.filtered("is_current")
        versions = super().create(vals_list)
        for version in versions:
            if version.is_current:
                version.po_id.version_ids.filtered(
                    lambda other: other != version
                ).write({"is_current": False})
        return versions

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_current"):
            for version in self:
                version.po_id.version_ids.filtered(
                    lambda other: other != version
                ).write({"is_current": False})
        return res
