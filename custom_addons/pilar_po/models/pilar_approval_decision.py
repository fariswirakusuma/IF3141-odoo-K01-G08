from odoo import fields, models


class PilarApprovalDecision(models.Model):
    _name = "pilar.approval.decision"
    _description = "Keputusan Persetujuan PO"
    _order = "decision_at desc, id desc"

    po_id = fields.Many2one(
        "pilar.po", string="Purchase Order", required=True,
        ondelete="cascade", index=True,
    )
    user_id = fields.Many2one(
        "res.users", string="Pengambil Keputusan",
        default=lambda self: self.env.user, required=True,
    )
    decision_type = fields.Selection(
        [
            ("setuju", "Disetujui"),
            ("tunda", "Ditunda"),
            ("kembalikan", "Dikembalikan"),
            ("batal", "Dibatalkan"),
        ],
        string="Jenis Keputusan", required=True,
    )
    reason = fields.Text(string="Alasan")
    decision_at = fields.Datetime(
        string="Waktu Keputusan", default=fields.Datetime.now, required=True
    )
