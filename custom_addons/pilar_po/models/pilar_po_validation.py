from odoo import fields, models


class PilarPoValidation(models.Model):
    _name = "pilar.po.validation"
    _description = "Hasil Validasi Versi PO"
    _order = "validated_at desc, id desc"

    version_id = fields.Many2one(
        "pilar.po.version", string="Versi PO", required=True,
        ondelete="cascade", index=True,
    )
    config_id = fields.Many2one(
        "pilar.po.config", string="Konfigurasi", required=True
    )
    validation_result = fields.Selection(
        [("lolos", "Lolos"), ("bermasalah", "Bermasalah")],
        string="Hasil Validasi", required=True,
    )
    validation_details = fields.Text(string="Rincian Validasi")
    validated_at = fields.Datetime(
        string="Divalidasi Pada", default=fields.Datetime.now, required=True
    )
