import csv
import hashlib

from odoo import api, fields, models


class stock_picking(models.Model):
    _inherit = "stock.picking"
    arrival_date = fields.Char("必着日", compute="_compute_order_arrival")
    commitment_date = fields.Date("出荷日", compute="_compute_order_commitment")
    print_partner_id = fields.Many2one(
        "res.partner", "発送元", compute="_compute_order_print_partner"
    )

    @api.depends("origin")
    def _compute_order_arrival(self):
        for delivery in self:
            order = self.env["sale.order"].search([("name", "=", delivery.origin)])
            if order:
                delivery.arrival_date = order.arrival_date
            else:
                delivery.arrival_date = ""

    @api.depends("origin")
    def _compute_order_print_partner(self):
        for delivery in self:
            order = self.env["sale.order"].search([("name", "=", delivery.origin)])
            if order:
                delivery.print_partner_id = order.print_partner_id
            else:
                delivery.print_partner_id = ""

    @api.depends("origin")
    def _compute_order_commitment(self):
        for delivery in self:
            order = self.env["sale.order"].search([("name", "=", delivery.origin)])
            if order:
                delivery.commitment_date = order.commitment_date
            else:
                delivery.commitment_date = ""

    def _get_order_data(self, field_name):
        try:
            sale_order = self.env["sale.order"].search([("name", "=", self.origin)])[0]
            return sale_order["client_order_ref"]

        except:
            return ""


class res_partner(models.Model):
    _inherit = "res.partner"
    fax = fields.Char("Fax")
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        default=lambda self: self.env["res.country"].search([("code", "=", "JP")]),
        help="Apply only if delivery or invoicing country match.",
    )
    vat = fields.Char("Tax ID", compute="_compute_reference")

    def _compute_reference(self):
        for partner in self:
            customer_info = str(partner.phone) + str(partner.name) + str(partner.id)
            partner.vat = (
                int(hashlib.sha256(customer_info.encode("utf-8")).hexdigest(), 16)
                % 10 ** 8
            )


class sale_order(models.Model):
    _inherit = "sale.order"
    print_partner_id = fields.Many2one("res.partner", "発送元")
    date_order = fields.Date("オーダー日", required=True)
    arrival_date = fields.Char("必着日")
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
        default=lambda self: self.env["product.pricelist"].search(
            ["|", ("name", "=", "一般小売価格"), ("name", "=", "Public Pricelist")]
        ),
    )
    subject = fields.Char("件名")

    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped("state")):
            raise UserError(
                _("It is not allowed to confirm an order in the following states: %s")
                % (", ".join(self._get_forbidden_state_confirm()))
            )

        for order in self.filtered(
            lambda order: order.partner_id not in order.message_partner_ids
        ):
            order.message_subscribe([order.partner_id.id])
        self.write({"state": "sale", "date_order": self.date_order})
        self._action_confirm()
        if self.env.user.has_group("sale.group_auto_done_setting"):
            self.action_done()
        return True


class product_name(models.Model):
    _inherit = "product.product"
    _order = "name"

    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get("name", "")
            code = (
                self._context.get("display_default_code", True)
                and d.get("default_code", False)
                or False
            )
            if code:
                name = "%s" % (name)
            return (d["id"], name)

        partner_id = self._context.get("partner_id")
        if partner_id:
            partner_ids = [
                partner_id,
                self.env["res.partner"].browse(partner_id).commercial_partner_id.id,
            ]
        else:
            partner_ids = []
        company_id = self.env.context.get("company_id")

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(["name", "default_code", "product_tmpl_id"], load=False)

        product_template_ids = self.sudo().mapped("product_tmpl_id").ids

        if partner_ids:
            supplier_info = (
                self.env["product.supplierinfo"]
                .sudo()
                .search(
                    [
                        ("product_tmpl_id", "in", product_template_ids),
                        ("name", "in", partner_ids),
                    ]
                )
            )
            # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
            # Use `load=False` to not call `name_get` for the `product_tmpl_id` and `product_id`
            supplier_info.sudo().read(
                ["product_tmpl_id", "product_id", "product_name", "product_code"],
                load=False,
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = (
                product.product_template_attribute_value_ids._get_combination_name()
            )

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(
                    product.product_tmpl_id, []
                )
                sellers = [
                    x
                    for x in product_supplier_info
                    if x.product_id and x.product_id == product
                ]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [
                        x for x in sellers if x.company_id.id in [company_id, False]
                    ]
            if sellers:
                for s in sellers:
                    seller_variant = (
                        s.product_name
                        and (
                            variant
                            and "%s (%s)" % (s.product_name, variant)
                            or s.product_name
                        )
                        or False
                    )
                    mydict = {
                        "id": product.id,
                        "name": seller_variant or name,
                        "default_code": s.product_code or product.default_code,
                    }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                    "id": product.id,
                    "name": name,
                    "default_code": product.default_code,
                }
                result.append(_name_get(mydict))
        return result


class ebidden_csv(models.AbstractModel):
    _name = "report.stock.ebidden_csv"
    _inherit = "report.report_csv.abstract"

    def generate_csv_report(self, writer, data, lines):
        writer.writeheader()
        for obj in lines:
            shipping_partner_id = obj.sale_id.partner_shipping_id
            print_partner_id = (
                obj.sale_id.print_partner_id
                if obj.sale_id.print_partner_id
                else obj.company_id
            )
            partner_street2 = (
                str(obj.partner_id.street2) if obj.partner_id.street2 else " "
            )
            shipping_partner_street2 = (
                str(shipping_partner_id.street2) if shipping_partner_id.street2 else " "
            )
            partner_vat = str(obj.partner_id.vat) if obj.partner_id.vat else "N/A"
            (
                product_code1,
                product_code2,
                product_code3,
                product_code4,
                product_code5,
            ) = [" ", " ", " ", " ", " "]
            try:
                product_code1 = str(obj.move_lines[0].product_id.default_code)
            except:
                pass
            try:
                product_code2 = str(obj.move_lines[1].product_id.default_code)
            except:
                pass
            try:
                product_code3 = str(obj.move_lines[2].product_id.default_code)
            except:
                pass
            try:
                product_code4 = str(obj.move_lines[3].product_id.default_code)
            except:
                pass
            try:
                product_code5 = str(obj.move_lines[4].product_id.default_code)
            except:
                pass

            writer.writerow(
                {
                    "在庫伝票No": str(obj.name),  # document
                    "配送先電話番号": str(shipping_partner_id.phone)
                    .replace("+81", "0", 1)
                    .replace(" ", "")
                    .replace("-", ""),  # partner shipping_id phone
                    "配送先郵便番号": str(shipping_partner_id.zip),  # partner shipping_id zip
                    "都道府県": str(
                        shipping_partner_id.state_id.name
                    ),  # partner shipping_id state
                    "市区町村＋町名番地": str(shipping_partner_id.city)
                    + ""
                    + str(
                        shipping_partner_id.street
                    ),  # partner shipping_id city, street
                    "建物名": str(shipping_partner_street2),  # partner shipping_id street2
                    "名称": str(shipping_partner_id.name),  # partner shipping_id name
                    "お届け先名称２": " ",  # #NA
                    "顧客参照": str(
                        obj.sale_id.client_order_ref
                    ),  # partner shipping_id client_order_ref
                    "お客様コード ": " ",  # NA
                    "部署・担当者 ": " ",  # NA
                    "荷送人電話番号": " ",  # NA
                    "ご依頼主電話番号": str(print_partner_id.phone)
                    .replace("+81", "0", 1)
                    .replace(" ", "")
                    .replace("-", ""),  # print_partner_id phone
                    "ご依頼主郵便番号": str(print_partner_id.zip),  # print_partner_id zip
                    "ご依頼主住所１": str(print_partner_id.state_id.name),  # print_partner_id
                    "ご依頼主住所２": str(print_partner_id.city)
                    + ""
                    + str(print_partner_id.street)
                    + ""
                    + str(print_partner_id.street2),  # print_partner_id
                    "ご依頼主名称１": str(print_partner_id.name),
                    "ご依頼主名称２": " ",
                    "荷姿コード": " ",
                    "品名１": product_code1,  # partner shipping_id client_order_ref
                    "品名２": product_code2,  # partner shipping_id client_order_ref
                    "品名３": product_code3,  # partner shipping_id client_order_ref
                    "品名４": product_code4,  # partner shipping_id client_order_ref
                    "品名５": product_code5,  # partner shipping_id client_order_ref
                    "出荷個数": " ",  # partner shipping_id client_order_ref
                    "便種（スピードで選択）": " ",  # partner shipping_id client_order_ref
                    "便種（商品）": " ",  # partner shipping_id client_order_ref
                    "配達日": str(
                        obj.commitment_date
                    ),  # partner shipping_id client_order_ref
                    "配達指定時間帯": " ",  # partner shipping_id client_order_ref
                    "配達指定時間（時分）": " ",  # partner shipping_id client_order_ref
                    "代引金額": " ",
                    "消費税": " ",
                    "決済種別": " ",
                    "保険金額": " ",
                    "保険金額印字": " ",
                    "指定シール①": " ",
                    "指定シール②": " ",
                    "指定シール③": " ",
                    "営業店止め": " ",
                    "ＳＲＣ区分": " ",
                    "営業店コード": " ",
                    "元着区分": " ",
                }
            )

    def csv_report_options(self):
        res = super().csv_report_options()
        # res['fieldnames'].append('お客様管理ナンバー')
        res["fieldnames"].append("在庫伝票No")
        res["fieldnames"].append("配送先電話番号")
        res["fieldnames"].append("配送先郵便番号")
        res["fieldnames"].append("都道府県")
        res["fieldnames"].append("市区町村＋町名番地")
        res["fieldnames"].append("建物名")
        res["fieldnames"].append("名称")
        res["fieldnames"].append("お届け先名称２")
        res["fieldnames"].append("顧客参照")
        res["fieldnames"].append("お客様コード ")
        res["fieldnames"].append("部署・担当者 ")
        res["fieldnames"].append("荷送人電話番号")
        res["fieldnames"].append("ご依頼主電話番号")
        res["fieldnames"].append("ご依頼主郵便番号")
        res["fieldnames"].append("ご依頼主住所１")
        res["fieldnames"].append("ご依頼主住所２")
        res["fieldnames"].append("ご依頼主名称１")
        res["fieldnames"].append("ご依頼主名称２")
        res["fieldnames"].append("荷姿コード")
        res["fieldnames"].append("品名１")
        res["fieldnames"].append("品名２")
        res["fieldnames"].append("品名３")
        res["fieldnames"].append("品名４")
        res["fieldnames"].append("品名５")
        res["fieldnames"].append("出荷個数")
        res["fieldnames"].append("便種（スピードで選択）")
        res["fieldnames"].append("便種（商品）")
        res["fieldnames"].append("配達日")
        res["fieldnames"].append("配達指定時間帯")
        res["fieldnames"].append("配達指定時間（時分）")
        res["fieldnames"].append("代引金額")
        res["fieldnames"].append("消費税")
        res["fieldnames"].append("決済種別")
        res["fieldnames"].append("保険金額")
        res["fieldnames"].append("保険金額印字")
        res["fieldnames"].append("指定シール①")
        res["fieldnames"].append("指定シール②")
        res["fieldnames"].append("指定シール③")
        res["fieldnames"].append("営業店止め")
        res["fieldnames"].append("ＳＲＣ区分")
        res["fieldnames"].append("営業店コード")
        res["fieldnames"].append("元着区分")
        res["delimiter"] = ","
        res["quoting"] = csv.QUOTE_ALL
        return res
