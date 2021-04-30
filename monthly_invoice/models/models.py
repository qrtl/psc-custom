# -*- coding: utf-8 -*-
import json, csv, datetime, calendar, hashlib
from odoo import models, fields, api


def get_month_day_range(date):
    """
    For a date 'date' returns the start and end date for the month of 'date'.

    Month with 31 days:
    >>> date = datetime.date(2011, 7, 27)
    >>> get_month_day_range(date)
    (datetime.date(2011, 7, 1), datetime.date(2011, 7, 31))

    Month with 28 days:
    >>> date = datetime.date(2011, 2, 15)
    >>> get_month_day_range(date)
    (datetime.date(2011, 2, 1), datetime.date(2011, 2, 28))
    """
    first_day = date.replace(day=1)
    last_day = date.replace(day=calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day


class account_move_monthly(models.Model):
    _inherit = 'account.move.line'
    monthly_partner_id = fields.Many2one('res.partner', string='Partner Monthly', ondelete='restrict')

    def _get_order_data(self, field_name):
        try:
            if field_name is "scheduled_date":
                delivery = self.env['stock.picking'].search([("origin", "=", self.move_id[0].invoice_origin),
                                                             ("state", "!=", "cancel")])[0]
                return delivery[field_name] + datetime.timedelta(days=1)

            sale_order = self.env['sale.order'].search([("name", "=", self.move_id[0].invoice_origin)])[0]
            return sale_order[field_name]

        except:
            return ""


class stock_picking(models.Model):
    _inherit = "stock.picking"
    arrival_date = fields.Char("必着日", compute="_compute_order_arrival")
    commitment_date = fields.Date("出荷日", compute="_compute_order_commitment")
    print_partner_id = fields.Many2one('res.partner', '発送元', compute="_compute_order_print_partner")

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
            sale_order = self.env['sale.order'].search([("name", "=", self.origin)])[0]
            return sale_order["client_order_ref"]

        except:
            return ""


class account_move(models.Model):
    _inherit = "account.move"

    monthly_invoices = fields.One2many('account.move.line', "monthly_partner_id", string='Monthly invoices',
                                       compute='_compute_monthly')
    monthly_sum_without_tax = fields.Float("Total without tax", compute="_compute_monthly_total_without_tax")
    monthly_sum_with_tax = fields.Float("Total", compute="_compute_monthly_total")
    monthly_tax = fields.Float("Total Tax", compute="_compute_monthly_tax")
    customer_balance = fields.Float("Overall Balance", compute="_compute_balance")

    @staticmethod
    def _get_month(month):
        return str(0) + str(month) if month < 10 else str(month)

    def _get_commitment(self, origin):
        commit = self.env['sale.order'].search([('name', '=', self.invoice_origin)])["commitment_date"]
        return commit

    def _get_subject(self, lines):
        for line in lines:
            try:
                subject = self.env["sale.order"].search([("name", "=", line.move_id.invoice_origin)])[0]["subject"]
                if subject:
                    return subject
            except:
                return " "

    def _compute_monthly_total(self):
        for single_invoice in self:
            single_invoice.monthly_sum_with_tax = sum(line.price_total for line in single_invoice.monthly_invoices)

    def _compute_monthly_tax(self):
        for single_invoice in self:
            single_invoice.monthly_tax = single_invoice.monthly_sum_with_tax - single_invoice.monthly_sum_without_tax

    def _compute_monthly_total_without_tax(self):
        for single_invoice in self:
            single_invoice.monthly_sum_without_tax = sum(
                line.price_subtotal for line in single_invoice.monthly_invoices)

    @api.onchange('invoice_date', 'partner_id', 'monthly_invoices')
    def _onchange_invoice_date(self):
        """ Warn if there is no invoice date and sales date"""
        sale_order = self.env['sale.order'].search(([('name', '=', self.invoice_origin)]))
        if not self.invoice_date and not sale_order.date_order and self.partner_id:
            return {
                'warning': {
                    'title': 'エラー',
                    'message': "御請求書の日付日が入っていません!"
                }
            }

    def _compute_monthly_with_group(self):
        for single_invoice in self:
            first_day, last_day = get_month_day_range(single_invoice.invoice_date)
            single_invoice.grouped_by_delivery = single_invoice.env["account.move"].read_group([["partner_id", "=",
                                                                                                 single_invoice.partner_id.id],
                                                                                                ["type", "=",
                                                                                                 "out_invoice"],
                                                                                                ["invoice_date", ">=",
                                                                                                 first_day],
                                                                                                ["invoice_date", "<=",
                                                                                                 last_day]
                                                                                                ],
                                                                                               ["partner_shipping_id",
                                                                                                "amount_total",
                                                                                                "partner_id",
                                                                                                "amount_untaxed",
                                                                                                "amount_tax"],
                                                                                               ["partner_shipping_id"])

            single_invoice.group_lines = single_invoice.monthly_invoices.read_group(
                [("partner_id", "=", single_invoice.partner_id.id), ("account_internal_type", "!=", "receivable"),
                 ("payment_id", "=", False),
                 ("account_internal_type", "!=", "payable"),
                 ("credit", "!=", "0"),
                 ("tax_line_id", "=", False),
                 ["date", ">=", first_day],
                 ["date", "<=", last_day]],
                ["product_id", "quantity", "partner_id",
                 "price_unit", "price_total"],
                ["product_id"])
            print(single_invoice.group_lines)
            for group in single_invoice.group_lines:
                print('>>>>>>', group['product_id'][1], group['quantity'])
            return single_invoice.group_lines



            # print(single_invoice.grouped_by_delivery)

    def _compute_monthly(self):
        # self._compute_monthly_with_group()
        for single_invoice in self:
            all_sales_lines_of_this_customer = single_invoice.env["account.move.line"].search(
                [("partner_id", "=", single_invoice.partner_id.id), ("account_internal_type", "!=", "receivable"),
                 ("payment_id", "=", False),
                 ("account_internal_type", "!=", "payable"),
                 ("credit", "!=", "0"),
                 ("tax_line_id", "=", False)], order='date asc')

            # try:
            #     same_month_sales_lines = all_sales_lines_of_this_customer.filtered(lambda
            #                                                                        r: True if r.date.month == single_invoice.invoice_date.month and r.date.year == single_invoice.invoice_date.year else False)
            #
            # except:
            try:
                # sale_order = self.env['sale.order'].search(([('name', '=', single_invoice.invoice_origin)]))
                first_day, last_day = get_month_day_range(single_invoice.invoice_date)
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(lambda
                                                                                       r: True if r.move_id.date <= last_day and
                                                                                                  r.move_id.date >= first_day else False)
            #     print(len(same_month_sales_lines))
            #     # single_invoice.invoice_date = sale_order.date_order
            except:
                single_invoice.monthly_invoices = single_invoice.invoice_line_ids
                return {
                    'error': {
                        'title': 'エラー',
                        'message': "御請求書の日付日が入っていません!"
                    }
                }

            if len(same_month_sales_lines) == 0:
                same_month_sales_lines = single_invoice.invoice_line_ids
            single_invoice.monthly_invoices = same_month_sales_lines

    def _compute_balance(self):
        for single_invoice in self:
            single_invoice.payments_of_the_customer = single_invoice.env["account.payment"].search(
                [("partner_id", "=", single_invoice.partner_id.id),
                 ("payment_date", "<=", single_invoice.invoice_date)]
            )
            single_invoice.expenses_of_the_customer = single_invoice.env["account.move"].search(
                [("partner_id", "=", single_invoice.partner_id.id),
                 ("type", "=", "out_invoice"),
                 ("invoice_date", "<=", single_invoice.invoice_date)])
            balance = sum(line.amount for line in single_invoice.payments_of_the_customer) - sum(
                line.amount_total for line in single_invoice.expenses_of_the_customer)
            single_invoice.customer_balance = - balance if balance != 0 else balance

    def print_monthly(self):
        for single_invoice in self:
            all_sales_lines_of_this_customer = single_invoice.env["account.move.line"].search(
                [("partner_id", "=", single_invoice.partner_id.id), ("account_internal_type", "!=", "receivable"),
                 ("payment_id", "=", False),
                 ("account_internal_type", "!=", "payable"),
                 ("tax_line_id", "=", False)], order='date asc'
            )
            # keep only the ones of the same month as this invoice
            try:
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(lambda
                                                                                       r: True if r.date.month == single_invoice.invoice_date.month and r.date.year == single_invoice.invoice_date.year else False)

            except:
                sale_order = self.env['sale.order'].search(([('name', '=', single_invoice.invoice_origin)]))
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(lambda
                                                                                       r: True if r.date.month == sale_order.date_order.month and r.date.year == sale_order.date_order.year else False)
                if len(same_month_sales_lines) == 0:
                    same_month_sales_lines = single_invoice.invoice_line_ids
            single_invoice.monthly_invoices = same_month_sales_lines
            print(same_month_sales_lines.partner_id.name)
            print(single_invoice.partner_id.id, len(all_sales_lines_of_this_customer), len(same_month_sales_lines))
            single_invoice.payments_of_the_customer = single_invoice.env["account.payment"].search(
                [("partner_id", "=", single_invoice.partner_id.id),
                 ("payment_date", "<=", single_invoice.invoice_date)]
            )
            single_invoice.expenses_of_the_customer = single_invoice.env["account.move"].search([("partner_id", "=",
                                                                                                  single_invoice.partner_id.id),
                                                                                                 ("type", "=",
                                                                                                  "out_invoice"),
                                                                                                 ("invoice_date", "<=",
                                                                                                  single_invoice.invoice_date)])

            single_invoice.customer_balance = sum(
                line.amount for line in single_invoice.payments_of_the_customer) - sum(
                line.amount_total for line in single_invoice.expenses_of_the_customer)
            print("The balance is ", single_invoice.customer_balance)

            return single_invoice.env.ref("monthly_invoice.report_monthly_invoice_print").report_action(single_invoice)

    @staticmethod
    def last_working_day_of_month(year, month):
        def _on_weekend(weekend_date):
            offset = max(1, (weekend_date.weekday() + 6) % 7 - 3)
            timedelta = datetime.timedelta(offset)
            most_recent = weekend_date - timedelta
            return most_recent.day

        temporary_day = calendar.monthrange(year, month)[1]

        # return temporary_day if datetime.date(year, month, temporary_day).weekday() <= 5 else \
        #     _on_weekend(datetime.date(year, month, temporary_day))
        return temporary_day


class res_partner(models.Model):
    _inherit = 'res.partner'
    fax = fields.Char("Fax")
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env['res.country'].search(
        ([('code', '=', "JP")])),
                                 help="Apply only if delivery or invoicing country match.")
    vat = fields.Char("Tax ID", compute="_compute_reference")

    def _compute_reference(self):
        for partner in self:
            customer_info = str(partner.phone) + str(partner.name) + str(partner.id)
            partner.vat = int(hashlib.sha256(customer_info.encode('utf-8')).hexdigest(), 16) % 10 ** 8



class sale_order(models.Model):
    _inherit = 'sale.order'
    print_partner_id = fields.Many2one('res.partner', '発送元')
    date_order = fields.Date("オーダー日", required=True)
    arrival_date = fields.Char("必着日")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist',
                                   default=lambda self: self.env['product.pricelist'].search(
                                       (['|', ('name', '=', "一般小売価格"),
                                         ('name', '=', 'Public Pricelist')])),
                                   )
    subject = fields.Char("件名")

    def action_confirm(self):
        if self._get_forbidden_state_confirm() & set(self.mapped('state')):
            raise UserError(_(
                'It is not allowed to confirm an order in the following states: %s'
            ) % (', '.join(self._get_forbidden_state_confirm())))

        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'date_order': self.date_order
        })
        self._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True


class product_name(models.Model):
    _inherit = 'product.product'
    _order = 'name'

    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                name = '%s' % (name)
            return (d['id'], name)

        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
        company_id = self.env.context.get('company_id')

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")

        result = []

        # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
        # Use `load=False` to not call `name_get` for the `product_tmpl_id`
        self.sudo().read(['name', 'default_code', 'product_tmpl_id'], load=False)

        product_template_ids = self.sudo().mapped('product_tmpl_id').ids

        if partner_ids:
            supplier_info = self.env['product.supplierinfo'].sudo().search([
                ('product_tmpl_id', 'in', product_template_ids),
                ('name', 'in', partner_ids),
            ])
            # Prefetch the fields used by the `name_get`, so `browse` doesn't fetch other fields
            # Use `load=False` to not call `name_get` for the `product_tmpl_id` and `product_id`
            supplier_info.sudo().read(['product_tmpl_id', 'product_id', 'product_name', 'product_code'], load=False)
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)
        for product in self.sudo():
            variant = product.product_template_attribute_value_ids._get_combination_name()

            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                product_supplier_info = supplier_info_by_template.get(product.product_tmpl_id, [])
                sellers = [x for x in product_supplier_info if x.product_id and x.product_id == product]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                # Filter out sellers based on the company. This is done afterwards for a better
                # code readability. At this point, only a few sellers should remain, so it should
                # not be a performance issue.
                if company_id:
                    sellers = [x for x in sellers if x.company_id.id in [company_id, False]]
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                            variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                    ) or False
                    mydict = {
                        'id': product.id,
                        'name': seller_variant or name,
                        'default_code': s.product_code or product.default_code,
                    }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                    'id': product.id,
                    'name': name,
                    'default_code': product.default_code,
                }
                result.append(_name_get(mydict))
        return result


class ebidden_csv(models.AbstractModel):
    _name = 'report.stock.ebidden_csv'
    _inherit = 'report.report_csv.abstract'

    def generate_csv_report(self, writer, data, lines):
        writer.writeheader()
        for obj in lines:
            shipping_partner_id = obj.sale_id.partner_shipping_id
            print_partner_id = obj.sale_id.print_partner_id if obj.sale_id.print_partner_id else obj.company_id
            partner_street2 = str(obj.partner_id.street2) if obj.partner_id.street2 else " "
            shipping_partner_street2 = str(shipping_partner_id.street2) if shipping_partner_id.street2 else " "
            partner_vat = str(obj.partner_id.vat) if obj.partner_id.vat else "N/A"
            product_code1, product_code2, product_code3, product_code4, product_code5 = [" ", " ", " ", " ", " "]
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

            writer.writerow({
                '在庫伝票No': str(obj.name),  # document
                '配送先電話番号': str(shipping_partner_id.phone).replace("+81", "0", 1).replace(" ", "").replace("-", ""),  # partner shipping_id phone
                '配送先郵便番号': str(shipping_partner_id.zip),  # partner shipping_id zip
                '都道府県': str(shipping_partner_id.state_id.name),  # partner shipping_id state
                '市区町村＋町名番地': str(shipping_partner_id.city) + "" + str(shipping_partner_id.street),  # partner shipping_id city, street
                '建物名': str(shipping_partner_street2),  # partner shipping_id street2
                '名称': str(shipping_partner_id.name),  # partner shipping_id name
                'お届け先名称２': " ",  # #NA
                '顧客参照': str(obj.sale_id.client_order_ref),  # partner shipping_id client_order_ref
                'お客様コード ': " ",  # NA
                '部署・担当者 ': " ",  # NA
                '荷送人電話番号': " ",  # NA
                'ご依頼主電話番号': str(print_partner_id.phone).replace("+81", "0", 1).replace(" ", "").replace("-", ""),  # print_partner_id phone
                'ご依頼主郵便番号': str(print_partner_id.zip),  # print_partner_id zip
                'ご依頼主住所１': str(print_partner_id.state_id.name),  # print_partner_id
                'ご依頼主住所２': str(print_partner_id.city) + "" + str(print_partner_id.street) + "" + str(print_partner_id.street2),  # print_partner_id
                'ご依頼主名称１': str(print_partner_id.name),
                'ご依頼主名称２': " ",
                '荷姿コード': " ",
                '品名１': product_code1,  # partner shipping_id client_order_ref
                '品名２': product_code2,  # partner shipping_id client_order_ref
                '品名３': product_code3,  # partner shipping_id client_order_ref
                '品名４': product_code4,  # partner shipping_id client_order_ref
                '品名５': product_code5,  # partner shipping_id client_order_ref
                '出荷個数': " ",  # partner shipping_id client_order_ref
                '便種（スピードで選択）': " ",  # partner shipping_id client_order_ref
                '便種（商品）': " ",  # partner shipping_id client_order_ref
                '配達日': str(obj.commitment_date),  # partner shipping_id client_order_ref
                '配達指定時間帯': " ",  # partner shipping_id client_order_ref
                '配達指定時間（時分）': " ",  # partner shipping_id client_order_ref
                '代引金額': " ",
                '消費税':  " ",
                '決済種別':  " ",
                '保険金額':  " ",
                '保険金額印字':  " ",
                '指定シール①': " ",
                '指定シール②': " ",
                '指定シール③': " ",
                '営業店止め': " ",
                'ＳＲＣ区分': " ",
                '営業店コード': " ",
                '元着区分': " "
            })

    def csv_report_options(self):
        res = super().csv_report_options()
        # res['fieldnames'].append('お客様管理ナンバー')
        res['fieldnames'].append('在庫伝票No')
        res['fieldnames'].append('配送先電話番号')
        res['fieldnames'].append('配送先郵便番号')
        res['fieldnames'].append('都道府県')
        res['fieldnames'].append('市区町村＋町名番地')
        res['fieldnames'].append('建物名')
        res['fieldnames'].append('名称')
        res['fieldnames'].append('お届け先名称２')
        res['fieldnames'].append('顧客参照')
        res['fieldnames'].append('お客様コード ')
        res['fieldnames'].append('部署・担当者 ')
        res['fieldnames'].append('荷送人電話番号')
        res['fieldnames'].append('ご依頼主電話番号')
        res['fieldnames'].append('ご依頼主郵便番号')
        res['fieldnames'].append('ご依頼主住所１')
        res['fieldnames'].append('ご依頼主住所２')
        res['fieldnames'].append('ご依頼主名称１')
        res['fieldnames'].append('ご依頼主名称２')
        res['fieldnames'].append('荷姿コード')
        res['fieldnames'].append('品名１')
        res['fieldnames'].append('品名２')
        res['fieldnames'].append('品名３')
        res['fieldnames'].append('品名４')
        res['fieldnames'].append('品名５')
        res['fieldnames'].append('出荷個数')
        res['fieldnames'].append('便種（スピードで選択）')
        res['fieldnames'].append('便種（商品）')
        res['fieldnames'].append('配達日')
        res['fieldnames'].append('配達指定時間帯')
        res['fieldnames'].append('配達指定時間（時分）')
        res['fieldnames'].append('代引金額')
        res['fieldnames'].append('消費税')
        res['fieldnames'].append('決済種別')
        res['fieldnames'].append('保険金額')
        res['fieldnames'].append('保険金額印字')
        res['fieldnames'].append('指定シール①')
        res['fieldnames'].append('指定シール②')
        res['fieldnames'].append('指定シール③')
        res['fieldnames'].append('営業店止め')
        res['fieldnames'].append('ＳＲＣ区分')
        res['fieldnames'].append('営業店コード')
        res['fieldnames'].append('元着区分')
        res['delimiter'] = ','
        res['quoting'] = csv.QUOTE_ALL
        return res
