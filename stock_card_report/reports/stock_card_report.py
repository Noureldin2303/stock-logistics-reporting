# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class StockCardView(models.TransientModel):
  _name = "stock.card.view"
  _description = "Stock Card View"
  _order = "date"

  date = fields.Datetime()
  product_id = fields.Many2one(comodel_name="product.product")
  product_qty = fields.Float()
  product_price = fields.Float()
  product_uom_qty = fields.Float()
  product_uom = fields.Many2one(comodel_name="uom.uom")
  reference = fields.Char()
  location_id = fields.Many2one(comodel_name="stock.location")
  location_dest_id = fields.Many2one(comodel_name="stock.location")
  is_initial = fields.Boolean()
  product_in = fields.Float()
  product_out = fields.Float()
  picking_id = fields.Many2one(comodel_name="stock.picking")

  @api.depends("reference", "picking_id.origin")
  def _compute_display_name(self):
    for rec in self:
      rec.display_name = (f"{rec.reference} ({rec.picking_id.origin})"
                          if rec.picking_id.origin else rec.reference)


class StockCardReport(models.TransientModel):
  _name = "report.stock.card.report"
  _description = "Stock Card Report"

  # Filters fields, used for data computation
  date_from = fields.Date()
  date_to = fields.Date()
  product_ids = fields.Many2many(comodel_name="product.product")
  location_ids = fields.Many2many(comodel_name="stock.location")
  all_locations = fields.Boolean()
  product_price = fields.Char(string="Sales Price")

  # Data fields, used to browse report data
  results = fields.Many2many(
      comodel_name="stock.card.view",
      compute="_compute_results",
      help="Use compute fields, so there is nothing store in database",
  )

  def _compute_results(self):
    self.ensure_one()
    date_from = self.date_from or "0001-01-01"
    date_to = self.date_to or fields.Date.context_today(self)
    location_model = self.env["stock.location"]
    if self.all_locations:
      locations = location_model.search([("usage", "in", ("internal", "transit"))])
    else:
      locations = (location_model.search([("id", "child_of", self.location_ids.ids)])
                   if self.location_ids else location_model)
    if not locations or not self.product_ids:
      self.results = []
      return
    location_ids = tuple(locations.ids)
    self._cr.execute(
        """
         SELECT move.date, move.product_id, line.quantity as product_qty,
            move.price_unit as product_price, move.product_uom_qty,
            move.product_uom, move.reference,
            line.location_id, line.location_dest_id,
            case when line.location_dest_id in %s
              then line.quantity else 0 end as product_in,
            case when line.location_id in %s
              then line.quantity else 0 end as product_out,
                case when move.date < %s then True else False end as is_initial,
                move.picking_id
          FROM stock_move move
          JOIN stock_move_line line on line.move_id = move.id
          WHERE ((line.location_dest_id in %s and line.location_id not in %s)
            or (line.location_id in %s and line.location_dest_id not in %s))
                and move.state = 'done' and move.product_id in %s
                and CAST(move.date AS date) <= %s
            ORDER BY move.date, move.reference
        """,
        (
            location_ids,
            location_ids,
            date_from,
            location_ids,
            location_ids,
            location_ids,
            location_ids,
            tuple(self.product_ids.ids),
            date_to,
        ),
    )
    stock_card_results = self._cr.dictfetchall()
    report_line = self.env["stock.card.view"]
    self.results = [report_line.new(line).id for line in stock_card_results]

  def _get_initial(self, product_line):
    product_input_qty = sum(product_line.mapped("product_in"))
    product_output_qty = sum(product_line.mapped("product_out"))
    return product_input_qty - product_output_qty

  def print_report(self, report_type="qweb"):
    self.ensure_one()
    action = (self.env.ref("stock_card_report.action_stock_card_report_xlsx") if report_type
              == "xlsx" else self.env.ref("stock_card_report.action_stock_card_report_pdf"))
    return action.report_action(self, config=False)

  def _get_html(self):
    result = {}
    rcontext = {}
    report = self.browse(self._context.get("active_id"))
    if report:
      rcontext["o"] = report
      result["html"] = self.env["ir.qweb"]._render(
          "stock_card_report.report_stock_card_report_html", rcontext)
    return result

  @api.model
  def get_html(self, given_context=None):
    return self.with_context(**(given_context or {}))._get_html()
