from odoo import fields, models


class PilarAuditLog(models.Model):
    _name = "pilar.audit.log"
    _description = "Riwayat Status dan Audit PO"
    _order = "created_at desc, id desc"

    po_id = fields.Many2one(
        "pilar.po", string="PO", required=True, ondelete="cascade", index=True
    )
    version_id = fields.Many2one(
        "pilar.po.version", string="Versi PO", ondelete="set null", index=True
    )
    user_id = fields.Many2one(
        "res.users", string="Pengguna",
        default=lambda self: self.env.user, required=True,
    )
    action_type = fields.Char(string="Tipe Aktivitas", required=True)
    old_value = fields.Text(string="Nilai Sebelum")
    new_value = fields.Text(string="Nilai Sesudah")
    old_status = fields.Char(string="Status Sebelum")
    new_status = fields.Char(string="Status Sesudah")
    reason = fields.Text(string="Alasan")
    created_at = fields.Datetime(
        string="Waktu", default=fields.Datetime.now, required=True
    )
    duration_hours = fields.Float(string="Durasi Tahap (jam)")
