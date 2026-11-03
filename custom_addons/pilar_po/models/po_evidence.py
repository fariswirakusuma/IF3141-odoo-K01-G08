from odoo import fields, models


class PilarPoEvidence(models.Model):
    _name = "pilar.po.evidence"
    _description = "Bukti Transaksi PO"
    _order = "received_at desc, id desc"

    po_id = fields.Many2one(
        "pilar.po", string="PO", required=True, ondelete="cascade", index=True
    )
    telegram_message_id = fields.Char(string="ID Pesan Telegram")
    sender_telegram_id = fields.Char(string="ID Pengirim Telegram")
    message_text = fields.Text(string="Teks Pesan")
    file_path = fields.Char(string="Path File")
    file_name = fields.Char(string="Nama File")
    evidence_type = fields.Selection(
        [("foto", "Foto"), ("dokumen", "Dokumen"), ("teks", "Teks")],
        string="Jenis Bukti", default="foto", required=True,
    )
    received_at = fields.Datetime(
        string="Diterima Pada", default=fields.Datetime.now, required=True
    )
    image = fields.Binary(string="Foto Bukti", attachment=True)
