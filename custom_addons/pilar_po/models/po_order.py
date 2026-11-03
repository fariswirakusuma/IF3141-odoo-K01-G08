from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

STATUS_SELECTION = [
    ("bukti_diterima", "Bukti Diterima"),
    ("dalam_pemeriksaan", "Dalam Pemeriksaan"),
    ("dikembalikan", "Dikembalikan"),
    ("menunggu_keputusan", "Menunggu Keputusan"),
    ("ditunda", "Ditunda"),
    ("disahkan", "Disahkan"),
    ("dibatalkan", "Dibatalkan"),
]

INSPECTION_STATES = ("bukti_diterima", "dalam_pemeriksaan", "dikembalikan")
DECISION_STATES = ("menunggu_keputusan", "ditunda")
FINAL_STATES = ("disahkan", "dibatalkan")


class PilarPoOrder(models.Model):
    _name = "pilar.po"
    _description = "Purchase Order PT Pilar Agrosinergi Nusantara"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "submitted_at desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Nomor PO", required=True, copy=False,
        default=lambda self: _("New"),
    )
    customer_id = fields.Many2one(
        "pilar.customer", string="Pelanggan", required=True, tracking=True
    )
    customer_segment = fields.Selection(
        related="customer_id.customer_type", string="Segmen Pelanggan",
        store=True, readonly=True,
    )
    customer_phone = fields.Char(
        related="customer_id.contact_phone", string="Kontak Pelanggan",
        readonly=True,
    )
    delivery_address = fields.Text(string="Alamat Pengiriman")
    delivery_date = fields.Date(string="Tanggal Pengiriman", tracking=True)
    telegram_sender = fields.Char(string="Pengirim Telegram")
    notes = fields.Text(string="Catatan Pesanan")

    created_by = fields.Many2one(
        "res.users", string="Dibuat Oleh",
        default=lambda self: self.env.user, readonly=True,
    )
    config_id = fields.Many2one(
        "pilar.po.config", string="Konfigurasi",
        default=lambda self: self.env["pilar.po.config"].get_config(),
    )

    state = fields.Selection(
        STATUS_SELECTION, string="Status PO", default="bukti_diterima",
        required=True, tracking=True, index=True,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Tinggi")], string="Tingkat Prioritas", default="0"
    )

    submitted_at = fields.Datetime(
        string="Waktu Diterima", default=fields.Datetime.now, required=True
    )
    stage_started_at = fields.Datetime(
        string="Mulai Tahap", default=fields.Datetime.now, required=True
    )
    created_at = fields.Datetime(
        string="Dibuat Pada", related="create_date", readonly=True
    )
    updated_at = fields.Datetime(
        string="Diperbarui Pada", related="write_date", readonly=True
    )

    version_ids = fields.One2many(
        "pilar.po.version", "po_id", string="Versi Dokumen"
    )
    current_version_id = fields.Many2one(
        "pilar.po.version", string="Versi Aktif",
        compute="_compute_current_version", store=True, readonly=True,
    )
    version = fields.Integer(
        string="Versi PO", compute="_compute_current_version", store=True
    )

    item_ids = fields.One2many(
        "pilar.po.item", "po_id", string="Baris Pesanan",
        domain=[("is_current_version", "=", True)],
    )
    evidence_ids = fields.One2many(
        "pilar.po.evidence", "po_id", string="Bukti Transaksi"
    )
    approval_ids = fields.One2many(
        "pilar.approval.decision", "po_id", string="Keputusan Persetujuan"
    )
    audit_ids = fields.One2many(
        "pilar.audit.log", "po_id", string="Riwayat & Audit"
    )
    validation_ids = fields.One2many(
        "pilar.po.validation", compute="_compute_validation_ids",
        string="Riwayat Validasi",
    )
    latest_validation_id = fields.Many2one(
        "pilar.po.validation", string="Validasi Terakhir",
        compute="_compute_latest_validation", readonly=True,
    )
    validation_result = fields.Selection(
        [("pending", "Belum Diperiksa"), ("lolos", "Lolos Validasi"),
         ("bermasalah", "Bermasalah")],
        string="Hasil Validasi", compute="_compute_latest_validation",
    )
    validation_message = fields.Text(
        string="Catatan Validasi", compute="_compute_latest_validation"
    )
    checked_by = fields.Many2one("res.users", string="Diperiksa Oleh")
    checked_at = fields.Datetime(string="Waktu Pemeriksaan")
    decided_by = fields.Many2one(
        "res.users", string="Diputuskan Oleh", compute="_compute_decision"
    )
    decision_at = fields.Datetime(
        string="Waktu Keputusan", compute="_compute_decision"
    )

    return_reason = fields.Selection(
        [("bukti_tidak_terbaca", "Bukti tidak terbaca"),
         ("data_tidak_lengkap", "Data tidak lengkap"),
         ("data_tidak_sesuai", "Data tidak sesuai bukti")],
        string="Alasan Pengembalian",
    )
    return_note = fields.Text(string="Catatan Perbaikan")
    postpone_reason = fields.Text(string="Alasan Penundaan")
    cancel_reason = fields.Text(string="Alasan Pembatalan")

    evidence_preview = fields.Binary(
        string="Foto Bukti", compute="_compute_evidence_preview"
    )
    evidence_caption = fields.Char(
        string="Keterangan Bukti", compute="_compute_evidence_preview"
    )
    evidence_count = fields.Integer(
        string="Jumlah Bukti", compute="_compute_evidence_preview"
    )
    line_count = fields.Integer(string="Jumlah Baris", compute="_compute_line_summary")
    total_quantity = fields.Float(string="Total Kuantitas", compute="_compute_line_summary")

    stage_deadline = fields.Datetime(
        string="Batas Waktu Tahap", compute="_compute_deadline", store=True
    )
    is_overdue = fields.Boolean(
        string="Melewati Batas Waktu", compute="_compute_deadline", store=True
    )
    hours_late = fields.Float(
        string="Keterlambatan (jam)", compute="_compute_deadline", store=True
    )
    responsible_role = fields.Selection(
        [("staff_sales", "Staff Sales"), ("director", "Director of Operational")],
        string="Penanggung Jawab", compute="_compute_responsible_role", store=True,
    )
    aging_days = fields.Float(string="Umur PO (hari)", compute="_compute_aging")

    @api.depends("version_ids.is_current", "version_ids.version_number")
    def _compute_current_version(self):
        for order in self:
            version = order.version_ids.filtered("is_current")[:1]
            if not version:
                version = order.version_ids.sorted(
                    lambda item: (item.version_number, item.id)
                )[-1:]
            order.current_version_id = version
            order.version = version.version_number if version else 0

    @api.depends(
        "current_version_id",
        "current_version_id.validation_ids.validation_result",
        "current_version_id.validation_ids.validated_at",
    )
    def _compute_latest_validation(self):
        for order in self:
            validation = order.current_version_id.validation_ids.sorted(
                key=lambda item: (item.validated_at, item.id)
            )[-1:]
            order.latest_validation_id = validation
            order.validation_result = (
                validation.validation_result if validation else "pending"
            )
            order.validation_message = (
                validation.validation_details if validation else False
            )

    @api.depends("current_version_id", "current_version_id.validation_ids")
    def _compute_validation_ids(self):
        for order in self:
            order.validation_ids = order.current_version_id.validation_ids

    @api.depends(
        "approval_ids.decision_type",
        "approval_ids.decision_at",
        "approval_ids.user_id",
    )
    def _compute_decision(self):
        for order in self:
            decision = order.approval_ids.filtered(
                lambda item: item.decision_type in ("setuju", "tunda")
            ).sorted(key=lambda item: (item.decision_at, item.id))[-1:]
            order.decided_by = decision.user_id if decision else False
            order.decision_at = decision.decision_at if decision else False

    @api.depends("evidence_ids.image", "evidence_ids.file_name", "evidence_ids.message_text")
    def _compute_evidence_preview(self):
        for order in self:
            evidence = order.evidence_ids[:1]
            order.evidence_preview = evidence.image or False
            order.evidence_caption = (
                evidence.file_name or evidence.message_text
                if evidence else False
            )
            order.evidence_count = len(order.evidence_ids)

    @api.depends("item_ids.quantity")
    def _compute_line_summary(self):
        for order in self:
            items = order.item_ids.filtered("is_current_version")
            order.line_count = len(items)
            order.total_quantity = sum(items.mapped("quantity"))

    @api.depends("state", "stage_started_at", "submitted_at")
    def _compute_deadline(self):
        config = self.env["pilar.po.config"].get_config()
        now = fields.Datetime.now()
        for order in self:
            start = order.stage_started_at or order.submitted_at or now
            if order.state in INSPECTION_STATES:
                deadline = start + timedelta(hours=config.inspection_sla_duration)
            elif order.state in DECISION_STATES:
                deadline = start + timedelta(hours=config.sla_duration)
            else:
                deadline = False
            order.stage_deadline = deadline
            order.is_overdue = bool(deadline and now > deadline)
            order.hours_late = (
                max((now - deadline).total_seconds() / 3600.0, 0.0)
                if deadline else 0.0
            )

    @api.depends("submitted_at")
    def _compute_aging(self):
        now = fields.Datetime.now()
        for order in self:
            order.aging_days = max(
                (now - (order.submitted_at or now)).total_seconds() / 86400.0, 0.0
            )

    @api.depends("state")
    def _compute_responsible_role(self):
        for order in self:
            order.responsible_role = (
                "director" if order.state in DECISION_STATES else "staff_sales"
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                seq = self.env["ir.sequence"].next_by_code("pilar.po") or "PO"
                vals["name"] = seq
            if not vals.get("config_id"):
                vals["config_id"] = self.env["pilar.po.config"].get_config().id
            if not vals.get("created_by"):
                vals["created_by"] = self.env.user.id
        orders = super().create(vals_list)
        for order in orders:
            order._ensure_current_version()
            order._log_audit(
                "PO dibuat dari bukti Telegram", False, order.state,
                reason="Draf PO otomatis dibuat saat bukti diterima.",
            )
        return orders

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ("delivery_date", "delivery_address")):
            for order in self:
                version = order.current_version_id
                if version:
                    version.write({
                        "delivery_date": order.delivery_date,
                        "delivery_address": order.delivery_address,
                    })
        return res

    def _ensure_current_version(self):
        self.ensure_one()
        version = self.version_ids.filtered("is_current")[:1]
        if not version:
            version = self.env["pilar.po.version"].create({
                "po_id": self.id,
                "created_by": (self.created_by or self.env.user).id,
                "delivery_date": self.delivery_date,
                "delivery_address": self.delivery_address,
                "is_current": True,
            })
        return version

    def _log_audit(self, action_type, old_status, new_status, reason=False,
                   old_value=False, new_value=False, duration_hours=0.0,
                   version=None):
        self.ensure_one()
        version = version or self.current_version_id
        labels = dict(STATUS_SELECTION)
        self.env["pilar.audit.log"].create({
            "po_id": self.id,
            "version_id": version.id if version else False,
            "user_id": self.env.user.id,
            "action_type": action_type,
            "old_value": old_value,
            "new_value": new_value,
            "old_status": labels.get(old_status, old_status) if old_status else False,
            "new_status": labels.get(new_status, new_status) if new_status else False,
            "reason": reason,
            "duration_hours": duration_hours,
        })

    def _set_state(self, new_state, action, reason=False, version=None):
        self.ensure_one()
        old_state = self.state
        duration = 0.0
        if self.stage_started_at:
            duration = (
                fields.Datetime.now() - self.stage_started_at
            ).total_seconds() / 3600.0
        self.write({"state": new_state, "stage_started_at": fields.Datetime.now()})
        self._log_audit(action, old_state, new_state, reason=reason,
                        duration_hours=duration, version=version)

    def action_start_check(self):
        for order in self:
            if order.state != "bukti_diterima":
                raise UserError(_("PO ini tidak berada pada status Bukti Diterima."))
            order._set_state("dalam_pemeriksaan", "Mulai pemeriksaan PO")
        return True

    def action_validate(self):
        for order in self:
            version = order._ensure_current_version()
            config = order.config_id or self.env["pilar.po.config"].get_config()
            problems = []
            if not order.customer_id:
                problems.append("Pelanggan belum diisi.")
            if not version.delivery_address:
                problems.append("Alamat pengiriman belum diisi.")
            if not version.delivery_date:
                problems.append("Tanggal pengiriman belum diisi.")
            elif version.delivery_date < fields.Date.today():
                problems.append("Tanggal pengiriman sudah lewat.")
            if not version.item_ids:
                problems.append("PO belum memiliki baris komoditas.")
            for item in version.item_ids:
                if not item.commodity_name:
                    problems.append("Ada baris tanpa nama komoditas.")
                if item.quantity <= 0:
                    problems.append(
                        f"Kuantitas {item.commodity_name or 'baris'} harus lebih dari 0."
                    )
                if not item.unit_name:
                    problems.append(
                        f"Satuan {item.commodity_name or 'baris'} belum diisi."
                    )
            duplicate = self.search([
                ("id", "!=", order.id),
                ("customer_id", "=", order.customer_id.id),
                ("delivery_date", "=", version.delivery_date),
                ("state", "!=", "dibatalkan"),
            ], limit=1)
            if duplicate:
                problems.append(
                    f"Kemungkinan PO ganda dengan {duplicate.name} untuk pelanggan "
                    "dan tanggal yang sama."
                )
            result = "bermasalah" if problems else "lolos"
            details = (
                "\n".join(f"- {problem}" for problem in problems)
                if problems else
                "Seluruh kolom wajib terisi dan sesuai. PO siap diteruskan."
            )
            validation = self.env["pilar.po.validation"].create({
                "version_id": version.id,
                "config_id": config.id,
                "validation_result": result,
                "validation_details": details,
            })
            order.write({
                "checked_by": self.env.user.id,
                "checked_at": validation.validated_at,
            })
            order._log_audit(
                "Pemeriksaan otomatis: " + ("bermasalah" if problems else "lolos"),
                order.state, order.state,
                reason=details,
                version=version,
            )
        return True

    def action_submit_decision(self):
        for order in self:
            if order.validation_result != "lolos":
                raise UserError(_("PO belum lolos validasi sehingga belum dapat diteruskan."))
            order.write({
                "checked_by": self.env.user.id,
                "checked_at": fields.Datetime.now(),
            })
            order._set_state(
                "menunggu_keputusan", "Diteruskan ke Director of Operational",
                "PO lengkap dan menunggu keputusan pengesahan.",
            )
            order.message_post(body=_("PO diteruskan ke antrean keputusan."))
        return True

    def action_approve(self):
        for order in self:
            if not (self.env.su or self.env.user.has_group("base.group_system")
                    or self.env.user.has_group("pilar_po.group_po_director")):
                raise UserError(_(
                    "Pengesahan PO hanya dapat dilakukan Director of Operational."
                ))
            if order.state not in DECISION_STATES:
                raise UserError(_("PO ini tidak berada pada tahap keputusan."))
            self.env["pilar.approval.decision"].create({
                "po_id": order.id,
                "user_id": self.env.user.id,
                "decision_type": "setuju",
                "reason": "PO sah menjadi dasar operasional, tagihan, dan pengiriman.",
            })
            order.write({"postpone_reason": False})
            order._set_state(
                "disahkan", "PO disahkan",
                "PO sah menjadi dasar operasional, tagihan, dan pengiriman.",
            )
            order.message_post(body=_("PO disahkan oleh Director of Operational."))
        return True

    def action_postpone(self):
        for order in self:
            if not (self.env.su or self.env.user.has_group("base.group_system")
                    or self.env.user.has_group("pilar_po.group_po_director")):
                raise UserError(_(
                    "Penundaan PO hanya dapat dilakukan Director of Operational."
                ))
            if order.state not in DECISION_STATES:
                raise UserError(_("PO ini tidak berada pada tahap keputusan."))
            if not order.postpone_reason:
                raise UserError(_("Alasan penundaan wajib diisi."))
            self.env["pilar.approval.decision"].create({
                "po_id": order.id,
                "user_id": self.env.user.id,
                "decision_type": "tunda",
                "reason": order.postpone_reason,
            })
            order._set_state("ditunda", "PO ditunda", order.postpone_reason)
        return True

    def action_return(self):
        for order in self:
            if order.state in FINAL_STATES:
                raise UserError(_("PO yang sudah disahkan atau dibatalkan tidak dapat dikembalikan."))
            if not order.return_reason:
                raise UserError(_("Alasan pengembalian wajib dipilih."))
            reason = order.return_note or dict(
                order._fields["return_reason"].selection
            ).get(order.return_reason)
            self.env["pilar.approval.decision"].create({
                "po_id": order.id,
                "user_id": self.env.user.id,
                "decision_type": "kembalikan",
                "reason": reason,
            })
            order._set_state("dikembalikan", "PO dikembalikan untuk diperbaiki", reason)
        return True

    def action_cancel(self):
        for order in self:
            if order.state == "dibatalkan":
                raise UserError(_("PO sudah dibatalkan."))
            if not order.cancel_reason:
                raise UserError(_("Alasan pembatalan wajib diisi."))
            if order.state == "disahkan" and not self.env.user.has_group(
                "pilar_po.group_po_director"
            ):
                raise UserError(_(
                    "Pembatalan PO yang sudah disahkan hanya dapat dilakukan "
                    "Director of Operational."
                ))
            self.env["pilar.approval.decision"].create({
                "po_id": order.id,
                "user_id": self.env.user.id,
                "decision_type": "batal",
                "reason": order.cancel_reason,
            })
            order._set_state("dibatalkan", "PO dibatalkan", order.cancel_reason)
        return True

    def action_resubmit(self):
        for order in self:
            if order.state != "dikembalikan":
                raise UserError(_("Hanya PO berstatus Dikembalikan yang dapat diperbaiki."))
            current = order.current_version_id or order._ensure_current_version()
            version = self.env["pilar.po.version"].create({
                "po_id": order.id,
                "created_by": self.env.user.id,
                "version_number": current.version_number + 1,
                "delivery_date": current.delivery_date,
                "delivery_address": current.delivery_address,
                "correction_note": order.return_note,
                "is_current": True,
            })
            for item in current.item_ids:
                self.env["pilar.po.item"].create({
                    "po_id": order.id,
                    "version_id": version.id,
                    "commodity_name": item.commodity_name,
                    "quantity": item.quantity,
                    "unit_name": item.unit_name,
                    "quality_specification": item.quality_specification,
                })
            order.write({"return_reason": False, "return_note": False})
            order._set_state(
                "dalam_pemeriksaan", "Perbaikan PO diterima",
                f"Perbaikan versi {version.version_number} diterima dari pelanggan.",
                version=version,
            )
        return True

    def action_view_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Riwayat & Audit PO"),
            "res_model": "pilar.audit.log",
            "view_mode": "tree,form",
            "domain": [("po_id", "=", self.id)],
            "context": {"default_po_id": self.id},
        }
