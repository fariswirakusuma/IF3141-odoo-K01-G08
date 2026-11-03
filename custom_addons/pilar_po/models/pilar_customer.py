from odoo import fields, models


class PilarCustomer(models.Model):
    _name = "pilar.customer"
    _description = "Pelanggan Purchase Order"
    _order = "customer_name"
    _rec_name = "customer_name"

    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_type = fields.Selection(
        [("mbg", "Dapur SPPG MBG"), ("horeca", "Horeca")],
        string="Tipe Pelanggan", required=True, default="mbg",
    )
    telegram_chat_id = fields.Char(string="Telegram Chat ID")
    contact_name = fields.Char(string="Nama Kontak")
    contact_phone = fields.Char(string="Telepon Kontak")
    is_active = fields.Boolean(string="Aktif", default=True)

    po_ids = fields.One2many("pilar.po", "customer_id", string="Purchase Order")
