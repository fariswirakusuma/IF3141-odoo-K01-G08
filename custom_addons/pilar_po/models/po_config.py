from odoo import api, fields, models


class PilarPoConfig(models.Model):
    _name = "pilar.po.config"
    _description = "Pengaturan Validasi dan Persetujuan PO"
    _order = "id desc"

    name = fields.Char(string="Nama Konfigurasi", required=True, default="Konfigurasi PO")
    active = fields.Boolean(default=True)
    updated_by = fields.Many2one(
        "res.users", string="Diperbarui Oleh",
        default=lambda self: self.env.user,
    )
    config_version = fields.Char(string="Versi Konfigurasi", default="1.0", required=True)
    required_fields = fields.Text(
        string="Isian Wajib PO",
        default=(
            "Pelanggan, alamat pengiriman, tanggal pengiriman, minimal satu baris "
            "komoditas, kuantitas > 0, satuan, dan spesifikasi mutu."
        ),
    )
    validation_rules = fields.Text(
        string="Aturan Validasi",
        default=(
            "PO dinyatakan lolos bila seluruh isian wajib terisi, kuantitas lebih "
            "dari nol, tanggal pengiriman belum lewat, dan tidak ada PO ganda."
        ),
    )
    sla_duration = fields.Float(
        string="Batas Waktu Keputusan (jam)", default=24.0,
        help="Batas waktu Director of Operational memutuskan PO.",
    )
    inspection_sla_duration = fields.Float(
        string="Batas Waktu Pemeriksaan (jam)", default=8.0,
        help="Batas waktu Staff Sales memeriksa PO sejak bukti diterima.",
    )
    reminder_threshold = fields.Integer(
        string="Ambang Pengingat (%)", default=75,
        help="Pengingat dikirim saat durasi mencapai persentase batas waktu.",
    )
    reminder_channel = fields.Selection(
        [("telegram", "Telegram + Dalam Sistem"), ("internal", "Dalam Sistem")],
        string="Kanal Pengingat", default="telegram",
    )
    escalation_target = fields.Many2one(
        "res.users", string="Tujuan Eskalasi",
        default=lambda self: self.env.ref("base.user_admin", raise_if_not_found=False),
    )
    effective_from = fields.Date(
        string="Berlaku Mulai", default=fields.Date.context_today, required=True
    )
    effective_until = fields.Date(string="Berlaku Sampai")
    created_at = fields.Datetime(
        string="Dibuat Pada", default=fields.Datetime.now, required=True
    )

    @api.model
    def get_config(self):
        today = fields.Date.context_today(self)
        config = self.search([
            ("active", "=", True),
            "|", ("effective_from", "=", False),
            ("effective_from", "<=", today),
            "|", ("effective_until", "=", False),
            ("effective_until", ">=", today),
        ], limit=1, order="id desc")
        if not config:
            config = self.sudo().create({"name": "Konfigurasi PO"})
        return config
