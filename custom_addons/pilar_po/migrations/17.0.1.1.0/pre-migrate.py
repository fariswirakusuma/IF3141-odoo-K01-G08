import logging

_logger = logging.getLogger(__name__)


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", ("public.%s" % table,))
    return bool(cr.fetchone()[0])


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def _rename_column(cr, table, old, new):
    if _column_exists(cr, table, old) and not _column_exists(cr, table, new):
        cr.execute(
            'ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, old, new)
        )


def migrate(cr, version):
    if not version or not _table_exists(cr, "pilar_po"):
        return

    _logger.info("Migrating pilar_po data to the Milestone 4 ERD model")

    # ------------------------------------------------------------------
    # Customer
    # ------------------------------------------------------------------
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS pilar_customer (
            id SERIAL PRIMARY KEY,
            customer_name VARCHAR NOT NULL,
            customer_type VARCHAR NOT NULL DEFAULT 'mbg',
            telegram_chat_id VARCHAR,
            contact_name VARCHAR,
            contact_phone VARCHAR,
            is_active BOOLEAN DEFAULT TRUE,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP
        )
        """
    )
    cr.execute(
        """
        INSERT INTO pilar_customer
            (id, customer_name, customer_type, contact_name, contact_phone,
             is_active, create_date, write_date)
        SELECT p.id, p.name,
               COALESCE((
                   SELECT mode() WITHIN GROUP (ORDER BY po.customer_segment)
                     FROM pilar_po po
                    WHERE po.customer_id = p.id
                      AND po.customer_segment IN ('mbg', 'horeca')
               ), 'mbg'),
               p.name, p.phone, TRUE, NOW(), NOW()
          FROM res_partner p
         WHERE p.id IN (
               SELECT DISTINCT customer_id
                 FROM pilar_po
                WHERE customer_id IS NOT NULL
         )
        ON CONFLICT (id) DO NOTHING
        """
    )
    cr.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('pilar_customer', 'id'),
            COALESCE((SELECT MAX(id) FROM pilar_customer), 1),
            TRUE
        )
        """
    )
    cr.execute(
        "ALTER TABLE pilar_po DROP CONSTRAINT IF EXISTS pilar_po_customer_id_fkey"
    )

    # ------------------------------------------------------------------
    # PO version
    # ------------------------------------------------------------------
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS pilar_po_version (
            id SERIAL PRIMARY KEY,
            po_id INTEGER NOT NULL,
            created_by INTEGER,
            version_number INTEGER NOT NULL DEFAULT 1,
            delivery_date DATE,
            delivery_address TEXT,
            correction_note TEXT,
            is_current BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP
        )
        """
    )
    cr.execute(
        """
        INSERT INTO pilar_po_version
            (po_id, created_by, version_number, delivery_date,
             delivery_address, is_current, created_at, create_date, write_date)
        SELECT po.id, COALESCE(po.create_uid, 1), 1, po.delivery_date,
               po.delivery_address, TRUE, COALESCE(po.submitted_at, NOW()),
               NOW(), NOW()
          FROM pilar_po po
         WHERE NOT EXISTS (
               SELECT 1 FROM pilar_po_version v WHERE v.po_id = po.id
         )
        """
    )
    cr.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('pilar_po_version', 'id'),
            COALESCE((SELECT MAX(id) FROM pilar_po_version), 1),
            TRUE
        )
        """
    )

    # ------------------------------------------------------------------
    # PO item (formerly PO line)
    # ------------------------------------------------------------------
    if _table_exists(cr, "pilar_po_line") and not _table_exists(cr, "pilar_po_item"):
        cr.execute("ALTER TABLE pilar_po_line RENAME TO pilar_po_item")
    if _table_exists(cr, "pilar_po_item"):
        _rename_column(cr, "pilar_po_item", "order_id", "po_id")
        for ddl in (
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS commodity_name VARCHAR",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS unit_name VARCHAR",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS quality_specification VARCHAR",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS version_id INTEGER",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS order_state VARCHAR",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS customer_id INTEGER",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS delivery_date DATE",
            "ALTER TABLE pilar_po_item ADD COLUMN IF NOT EXISTS is_current_version BOOLEAN",
        ):
            cr.execute(ddl)

        if _column_exists(cr, "pilar_po_item", "product_id"):
            cr.execute(
                """
                UPDATE pilar_po_item i
                   SET commodity_name = COALESCE(
                       pt.name->>'en_US', pt.name->>'id_ID', pt.name->>'id',
                       'Komoditas'
                   )
                  FROM product_product pp
                  JOIN product_template pt ON pt.id = pp.product_tmpl_id
                 WHERE i.product_id = pp.id
                   AND (i.commodity_name IS NULL OR i.commodity_name = '')
                """
            )
            cr.execute("ALTER TABLE pilar_po_item DROP COLUMN product_id CASCADE")
        cr.execute(
            """
            UPDATE pilar_po_item
               SET commodity_name = 'Komoditas'
             WHERE commodity_name IS NULL OR commodity_name = ''
            """
        )

        if _column_exists(cr, "pilar_po_item", "description"):
            cr.execute(
                """
                UPDATE pilar_po_item
                   SET quality_specification = description
                 WHERE quality_specification IS NULL
                """
            )
            cr.execute("ALTER TABLE pilar_po_item DROP COLUMN description CASCADE")

        if _column_exists(cr, "pilar_po_item", "uom_id"):
            cr.execute(
                """
                UPDATE pilar_po_item i
                   SET unit_name = COALESCE(
                       u.name->>'en_US', u.name->>'id_ID', u.name->>'id', 'unit'
                   )
                  FROM uom_uom u
                 WHERE i.uom_id = u.id
                   AND (i.unit_name IS NULL OR i.unit_name = '')
                """
            )
            cr.execute("ALTER TABLE pilar_po_item DROP COLUMN uom_id CASCADE")
        cr.execute(
            """
            UPDATE pilar_po_item
               SET unit_name = 'unit'
             WHERE unit_name IS NULL OR unit_name = ''
            """
        )

        cr.execute(
            """
            UPDATE pilar_po_item i
               SET version_id = v.id
              FROM pilar_po_version v
             WHERE i.po_id = v.po_id
               AND v.is_current = TRUE
               AND i.version_id IS NULL
            """
        )
        cr.execute(
            """
            UPDATE pilar_po_item i
               SET order_state = po.state,
                   customer_id = po.customer_id,
                   delivery_date = v.delivery_date,
                   is_current_version = v.is_current
              FROM pilar_po po
              JOIN pilar_po_version v
                ON v.po_id = po.id AND v.is_current = TRUE
             WHERE i.po_id = po.id
            """
        )
        cr.execute(
            "ALTER TABLE pilar_po_item "
            "DROP CONSTRAINT IF EXISTS pilar_po_line_customer_id_fkey"
        )
        for column in ("note", "needed_date"):
            cr.execute(
                'ALTER TABLE pilar_po_item DROP COLUMN IF EXISTS "%s" CASCADE'
                % column
            )

    # ------------------------------------------------------------------
    # Audit log (formerly PO history)
    # ------------------------------------------------------------------
    if _table_exists(cr, "pilar_po_history") and not _table_exists(cr, "pilar_audit_log"):
        cr.execute("ALTER TABLE pilar_po_history RENAME TO pilar_audit_log")
    if _table_exists(cr, "pilar_audit_log"):
        for old, new in (
            ("order_id", "po_id"),
            ("action", "action_type"),
            ("from_state", "old_status"),
            ("to_state", "new_status"),
            ("note", "reason"),
            ("timestamp", "created_at"),
        ):
            _rename_column(cr, "pilar_audit_log", old, new)
        cr.execute(
            "ALTER TABLE pilar_audit_log "
            "ADD COLUMN IF NOT EXISTS version_id INTEGER"
        )
        cr.execute(
            "ALTER TABLE pilar_audit_log ADD COLUMN IF NOT EXISTS old_value TEXT"
        )
        cr.execute(
            "ALTER TABLE pilar_audit_log ADD COLUMN IF NOT EXISTS new_value TEXT"
        )
        cr.execute(
            """
            UPDATE pilar_audit_log a
               SET version_id = v.id
              FROM pilar_po_version v
             WHERE a.po_id = v.po_id
               AND v.is_current = TRUE
               AND a.version_id IS NULL
            """
        )

    # ------------------------------------------------------------------
    # Transaction evidence
    # ------------------------------------------------------------------
    if _table_exists(cr, "pilar_po_evidence"):
        _rename_column(cr, "pilar_po_evidence", "order_id", "po_id")
        for ddl in (
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS telegram_message_id VARCHAR",
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS sender_telegram_id VARCHAR",
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS message_text TEXT",
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS file_path VARCHAR",
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS file_name VARCHAR",
            "ALTER TABLE pilar_po_evidence ADD COLUMN IF NOT EXISTS evidence_type VARCHAR DEFAULT 'foto'",
        ):
            cr.execute(ddl)
        if _column_exists(cr, "pilar_po_evidence", "name"):
            cr.execute(
                "UPDATE pilar_po_evidence SET file_name = name "
                "WHERE file_name IS NULL"
            )
        if _column_exists(cr, "pilar_po_evidence", "caption"):
            cr.execute(
                "UPDATE pilar_po_evidence SET message_text = caption "
                "WHERE message_text IS NULL"
            )
        cr.execute(
            "UPDATE pilar_po_evidence SET evidence_type = 'foto' "
            "WHERE evidence_type IS NULL"
        )
        cr.execute(
            "UPDATE pilar_po_evidence SET received_at = NOW() "
            "WHERE received_at IS NULL"
        )
        for column in ("name", "caption", "source", "sender_name"):
            cr.execute(
                'ALTER TABLE pilar_po_evidence DROP COLUMN IF EXISTS "%s" CASCADE'
                % column
            )

    # ------------------------------------------------------------------
    # Purchase order
    # ------------------------------------------------------------------
    if _table_exists(cr, "pilar_po"):
        cr.execute(
            "ALTER TABLE pilar_po DROP CONSTRAINT IF EXISTS pilar_po_customer_id_fkey"
        )
        for ddl in (
            "ALTER TABLE pilar_po ADD COLUMN IF NOT EXISTS created_by INTEGER",
            "ALTER TABLE pilar_po ADD COLUMN IF NOT EXISTS config_id INTEGER",
            "ALTER TABLE pilar_po ADD COLUMN IF NOT EXISTS current_version_id INTEGER",
        ):
            cr.execute(ddl)
        for column in ("customer_segment", "customer_phone"):
            cr.execute(
                'ALTER TABLE pilar_po DROP COLUMN IF EXISTS "%s" CASCADE' % column
            )
        cr.execute(
            "ALTER TABLE pilar_po ADD COLUMN IF NOT EXISTS customer_segment VARCHAR"
        )
        cr.execute(
            "ALTER TABLE pilar_po ADD COLUMN IF NOT EXISTS customer_phone VARCHAR"
        )
        cr.execute(
            """
            UPDATE pilar_po po
               SET customer_segment = c.customer_type,
                   customer_phone = c.contact_phone
              FROM pilar_customer c
             WHERE po.customer_id = c.id
            """
        )
        cr.execute(
            "UPDATE pilar_po SET created_by = create_uid WHERE created_by IS NULL"
        )
        cr.execute(
            """
            UPDATE pilar_po
               SET config_id = (
                   SELECT id FROM pilar_po_config ORDER BY id LIMIT 1
               )
             WHERE config_id IS NULL
            """
        )
        cr.execute(
            """
            UPDATE pilar_po po
               SET current_version_id = v.id
              FROM pilar_po_version v
             WHERE po.id = v.po_id
               AND v.is_current = TRUE
               AND po.current_version_id IS NULL
            """
        )
        cr.execute(
            "UPDATE pilar_po SET version = 1 "
            "WHERE version IS NULL OR version = 0"
        )

    # ------------------------------------------------------------------
    # System config
    # ------------------------------------------------------------------
    if _table_exists(cr, "pilar_po_config"):
        for ddl in (
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS updated_by INTEGER",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS config_version VARCHAR",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS required_fields TEXT",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS validation_rules TEXT",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS sla_duration DOUBLE PRECISION",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS inspection_sla_duration DOUBLE PRECISION",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS escalation_target INTEGER",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS effective_from DATE",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS effective_until DATE",
            "ALTER TABLE pilar_po_config ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
        ):
            cr.execute(ddl)
        cr.execute(
            """
            UPDATE pilar_po_config
               SET config_version = COALESCE(config_version, '1.0'),
                   effective_from = COALESCE(effective_from, CURRENT_DATE),
                   required_fields = COALESCE(
                       required_fields,
                       'Pelanggan, alamat pengiriman, tanggal pengiriman, '
                       'minimal satu baris komoditas, kuantitas > 0, satuan, '
                       'dan spesifikasi mutu.'
                   ),
                   validation_rules = COALESCE(
                       validation_rules,
                       'PO dinyatakan lolos bila seluruh isian wajib terisi, '
                       'kuantitas lebih dari nol, tanggal pengiriman belum '
                       'lewat, dan tidak ada PO ganda.'
                   ),
                   created_at = COALESCE(created_at, create_date, NOW()),
                   updated_by = COALESCE(updated_by, create_uid)
            """
        )
        if _column_exists(cr, "pilar_po_config", "decision_sla_hours"):
            cr.execute(
                "UPDATE pilar_po_config SET sla_duration = "
                "COALESCE(sla_duration, decision_sla_hours, 24)"
            )
        if _column_exists(cr, "pilar_po_config", "inspection_sla_hours"):
            cr.execute(
                "UPDATE pilar_po_config SET inspection_sla_duration = "
                "COALESCE(inspection_sla_duration, inspection_sla_hours, 8)"
            )
        if _column_exists(cr, "pilar_po_config", "escalation_user_id"):
            cr.execute(
                "UPDATE pilar_po_config SET escalation_target = "
                "COALESCE(escalation_target, escalation_user_id)"
            )

    _logger.info("pilar_po ERD data migration completed")
