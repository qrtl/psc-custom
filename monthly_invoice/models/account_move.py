import calendar

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


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


class AccountMove(models.Model):
    _inherit = "account.move"

    monthly_invoices = fields.One2many(
        "account.move.line",
        "monthly_partner_id",
        string="Monthly invoices",
        compute="_compute_monthly",
    )
    monthly_sum_without_tax = fields.Float(
        "Total without tax", compute="_compute_monthly_total_without_tax"
    )
    monthly_sum_with_tax = fields.Float("Total", compute="_compute_monthly_total")
    monthly_tax = fields.Float("Total Tax", compute="_compute_monthly_tax")
    customer_balance = fields.Float("Overall Balance", compute="_compute_balance")
    invoice_issue_date = fields.Date(
        compute="_compute_invoice_issue_date",
        help="The date the monthly invoice is supposed to be issued on.",
    )

    def _get_partner_address(self, partner):
        """This method intends to return the address (up to street) in one line
        without spaces.
        """
        self.ensure_one()
        res = ""
        if partner.state_id:
            res += partner.state_id.name
        if partner.city:
            res += partner.city
        if partner.street:
            res += partner.street
        return res

    def _get_commitment(self, origin):
        commit = self.env["sale.order"].search([("name", "=", self.invoice_origin)])[
            "commitment_date"
        ]
        return commit

    def _get_subject(self, lines):
        for line in lines:
            try:
                subject = self.env["sale.order"].search(
                    [("name", "=", line.move_id.invoice_origin)]
                )[0]["subject"]
                if subject:
                    return subject
            except:
                return " "

    def _compute_monthly_total(self):
        for single_invoice in self:
            single_invoice.monthly_sum_with_tax = sum(
                line.price_total for line in single_invoice.monthly_invoices
            )

    def _compute_monthly_tax(self):
        for single_invoice in self:
            single_invoice.monthly_tax = (
                single_invoice.monthly_sum_with_tax
                - single_invoice.monthly_sum_without_tax
            )

    def _compute_monthly_total_without_tax(self):
        for single_invoice in self:
            single_invoice.monthly_sum_without_tax = sum(
                line.price_subtotal for line in single_invoice.monthly_invoices
            )

    def _compute_invoice_issue_date(self):
        for inv in self:
            if inv.invoice_date:
                inv.invoice_issue_date = inv.invoice_date + relativedelta(day=31)

    @api.onchange("invoice_date", "partner_id", "monthly_invoices")
    def _onchange_invoice_date(self):
        """ Warn if there is no invoice date and sales date"""
        sale_order = self.env["sale.order"].search([("name", "=", self.invoice_origin)])
        if not self.invoice_date and not sale_order.date_order and self.partner_id:
            return {"warning": {"title": "エラー", "message": "御請求書の日付日が入っていません!"}}

    def _compute_monthly_with_group(self):
        for single_invoice in self:
            first_day, last_day = get_month_day_range(single_invoice.invoice_date)
            single_invoice.grouped_by_delivery = single_invoice.env[
                "account.move"
            ].read_group(
                [
                    ["partner_id", "=", single_invoice.partner_id.id],
                    ["type", "=", "out_invoice"],
                    ["invoice_date", ">=", first_day],
                    ["invoice_date", "<=", last_day],
                ],
                [
                    "partner_shipping_id",
                    "amount_total",
                    "partner_id",
                    "amount_untaxed",
                    "amount_tax",
                ],
                ["partner_shipping_id"],
            )

            single_invoice.group_lines = single_invoice.monthly_invoices.read_group(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("account_internal_type", "!=", "receivable"),
                    ("payment_id", "=", False),
                    ("account_internal_type", "!=", "payable"),
                    ("credit", "!=", "0"),
                    ("tax_line_id", "=", False),
                    ["date", ">=", first_day],
                    ["date", "<=", last_day],
                ],
                ["product_id", "quantity", "partner_id", "price_unit", "price_total"],
                ["product_id"],
            )
            return single_invoice.group_lines

    def _compute_monthly(self):
        # self._compute_monthly_with_group()
        for single_invoice in self:
            all_sales_lines_of_this_customer = single_invoice.env[
                "account.move.line"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("account_internal_type", "!=", "receivable"),
                    ("payment_id", "=", False),
                    ("account_internal_type", "!=", "payable"),
                    ("credit", "!=", "0"),
                    ("tax_line_id", "=", False),
                ],
                order="date asc",
            )

            # try:
            #     same_month_sales_lines = all_sales_lines_of_this_customer.filtered(lambda
            #                                                                        r: True if r.date.month == single_invoice.invoice_date.month and r.date.year == single_invoice.invoice_date.year else False)
            #
            # except:
            try:
                # sale_order = self.env['sale.order'].search(([('name', '=', single_invoice.invoice_origin)]))
                first_day, last_day = get_month_day_range(single_invoice.invoice_date)
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(
                    lambda r: True
                    if r.move_id.date <= last_day and r.move_id.date >= first_day
                    else False
                )
            #     print(len(same_month_sales_lines))
            #     # single_invoice.invoice_date = sale_order.date_order
            except:
                single_invoice.monthly_invoices = single_invoice.invoice_line_ids
                return {"error": {"title": "エラー", "message": "御請求書の日付日が入っていません!"}}

            if len(same_month_sales_lines) == 0:
                same_month_sales_lines = single_invoice.invoice_line_ids
            single_invoice.monthly_invoices = same_month_sales_lines

    def _compute_balance(self):
        for single_invoice in self:
            single_invoice.payments_of_the_customer = single_invoice.env[
                "account.payment"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("payment_date", "<=", single_invoice.invoice_date),
                ]
            )
            single_invoice.expenses_of_the_customer = single_invoice.env[
                "account.move"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("type", "=", "out_invoice"),
                    ("invoice_date", "<=", single_invoice.invoice_date),
                ]
            )
            balance = sum(
                line.amount for line in single_invoice.payments_of_the_customer
            ) - sum(
                line.amount_total for line in single_invoice.expenses_of_the_customer
            )
            single_invoice.customer_balance = -balance if balance != 0 else balance

    def print_monthly(self):
        for single_invoice in self:
            all_sales_lines_of_this_customer = single_invoice.env[
                "account.move.line"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("account_internal_type", "!=", "receivable"),
                    ("payment_id", "=", False),
                    ("account_internal_type", "!=", "payable"),
                    ("tax_line_id", "=", False),
                ],
                order="date asc",
            )
            # keep only the ones of the same month as this invoice
            try:
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(
                    lambda r: True
                    if r.date.month == single_invoice.invoice_date.month
                    and r.date.year == single_invoice.invoice_date.year
                    else False
                )

            except:
                sale_order = self.env["sale.order"].search(
                    [("name", "=", single_invoice.invoice_origin)]
                )
                same_month_sales_lines = all_sales_lines_of_this_customer.filtered(
                    lambda r: True
                    if r.date.month == sale_order.date_order.month
                    and r.date.year == sale_order.date_order.year
                    else False
                )
                if len(same_month_sales_lines) == 0:
                    same_month_sales_lines = single_invoice.invoice_line_ids
            single_invoice.monthly_invoices = same_month_sales_lines
            single_invoice.payments_of_the_customer = single_invoice.env[
                "account.payment"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("payment_date", "<=", single_invoice.invoice_date),
                ]
            )
            single_invoice.expenses_of_the_customer = single_invoice.env[
                "account.move"
            ].search(
                [
                    ("partner_id", "=", single_invoice.partner_id.id),
                    ("type", "=", "out_invoice"),
                    ("invoice_date", "<=", single_invoice.invoice_date),
                ]
            )

            single_invoice.customer_balance = sum(
                line.amount for line in single_invoice.payments_of_the_customer
            ) - sum(
                line.amount_total for line in single_invoice.expenses_of_the_customer
            )

            return single_invoice.env.ref(
                "monthly_invoice.report_monthly_invoice_print"
            ).report_action(single_invoice)
