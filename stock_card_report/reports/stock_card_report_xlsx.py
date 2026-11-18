# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (  # pylint: disable=import-error
    FORMATS, XLS_HEADERS,
)

_logger = logging.getLogger(__name__)


class ReportStockCardReportXlsx(models.AbstractModel):
  _name = "report.stock_card_report.report_stock_card_report_xlsx"
  _description = "Stock Card Report XLSX"
  _inherit = "report.report_xlsx.abstract"

  def generate_xlsx_report(self, workbook, data, objects):
    self._define_formats(workbook)
    for product in objects.product_ids:
      for ws_params in self._get_ws_params(workbook, data, product):
        ws_name = ws_params.get("ws_name")
        ws_name = self._check_ws_name(ws_name)
        worksheet = workbook.add_worksheet(ws_name)
        generate_ws_method = getattr(self, ws_params["generate_ws_method"])
        generate_ws_method(workbook, worksheet, ws_params, data, objects, product)

  def _get_ws_params(self, _workbook, _data, product):
    filter_template = {
        "1_date_from": {
            "header": {
                "value": "Date from"
            },
            "data": {
                "value": self._render("date_from"),
                "format": FORMATS["format_tcell_date_center"],
            },
        },
        "2_date_to": {
            "header": {
                "value": "Date to"
            },
            "data": {
                "value": self._render("date_to"),
                "format": FORMATS["format_tcell_date_center"],
            },
        },
        "3_location": {
            "header": {
                "value": "Location"
            },
            "data": {
                "value": self._render("location"),
                "format": FORMATS["format_tcell_center"],
            },
        },
        "4_sales_price": {
            "header": {
                "value": "Sales Price"
            },
            "data": {
                "value": self._render("sales_price"),
                "format": FORMATS["format_tcell_amount_right"],
            },
        },
    }
    initial_template = {
        "1_ref": {
            "data": {
                "value": "Initial",
                "format": FORMATS["format_tcell_center"]
            },
            "colspan": 5,
        },
        "2_balance": {
            "data": {
                "value": self._render("balance"),
                "format": FORMATS["format_tcell_amount_right"],
            }
        },
    }
    closing_template = {
        **initial_template,
        "1_ref": {
            **initial_template["1_ref"],
            "data": {
                **initial_template["1_ref"]["data"],
                "value": "Closing",
            },
        },
    }
    stock_card_template = {
        "1_date": {
            "header": {
                "value": "Date"
            },
            "data": {
                "value": self._render("date"),
                "format": FORMATS["format_tcell_date_left"],
            },
            "width": 25,
        },
        "2_cost": {
            "header": {
                "value": "Cost"
            },
            "data": {
                "value": self._render("cost")
            },
            "width": 18,
        },
        "3_reference": {
            "header": {
                "value": "Reference"
            },
            "data": {
                "value": self._render("reference"),
                "format": FORMATS["format_tcell_left"],
            },
            "width": 25,
        },
        "4_input": {
            "header": {
                "value": "In"
            },
            "data": {
                "value": self._render("input")
            },
            "width": 25,
        },
        "5_output": {
            "header": {
                "value": "Out"
            },
            "data": {
                "value": self._render("output")
            },
            "width": 25,
        },
        "6_balance": {
            "header": {
                "value": "Balance"
            },
            "data": {
                "value": self._render("balance")
            },
            "width": 25,
        },
    }

    ws_params = {
        "ws_name": product.name,
        "generate_ws_method": "_stock_card_report",
        "title": f"Stock Card - {product.name}",
        "wanted_list_filter": sorted(filter_template.keys()),
        "col_specs_filter": filter_template,
        "wanted_list_initial": sorted(initial_template.keys()),
        "col_specs_initial": initial_template,
        "wanted_list_closing": sorted(closing_template.keys()),
        "col_specs_closing": closing_template,
        "wanted_list": sorted(stock_card_template.keys()),
        "col_specs": stock_card_template,
    }
    return [ws_params]

  def _stock_card_report(self, _workbook, worksheet, ws_params, _data, objects, product):  # pylint: disable=too-many-arguments
    worksheet.set_portrait()
    worksheet.fit_to_pages(1, 0)
    worksheet.set_header(XLS_HEADERS["xls_headers"]["standard"])
    worksheet.set_footer(XLS_HEADERS["xls_footers"]["standard"])
    self._set_column_width(worksheet, ws_params)
    # Title
    row_pos = 0
    row_pos = self._write_ws_title(worksheet, row_pos, ws_params, True)
    # Filter Table
    row_pos = self._write_line(
        worksheet,
        row_pos,
        ws_params,
        col_specs_section="header",
        default_format=FORMATS["format_theader_blue_center"],
        col_specs="col_specs_filter",
        wanted_list="wanted_list_filter",
    )
    row_pos = self._write_line(
        worksheet,
        row_pos,
        ws_params,
        col_specs_section="data",
        render_space={
            "date_from": objects.date_from or "",
            "date_to": objects.date_to or "",
            "location": ("All Stock Locations" if objects.all_locations else ", ".join(
                objects.location_ids.mapped("display_name"))),
            "sales_price": product.list_price,
        },
        col_specs="col_specs_filter",
        wanted_list="wanted_list_filter",
    )
    row_pos += 1
    # Stock Card Table
    row_pos = self._write_line(
        worksheet,
        row_pos,
        ws_params,
        col_specs_section="header",
        default_format=FORMATS["format_theader_blue_center"],
    )
    worksheet.freeze_panes(row_pos, 0)
    balance = objects._get_initial(
        objects.results.filtered(lambda line: line.product_id == product and line.is_initial))
    row_pos = self._write_line(
        worksheet,
        row_pos,
        ws_params,
        col_specs_section="data",
        render_space={"balance": balance},
        col_specs="col_specs_initial",
        wanted_list="wanted_list_initial",
    )
    product_lines = objects.results.filtered(
        lambda line: line.product_id == product and not line.is_initial)
    for line in product_lines:
      balance += line.product_in - line.product_out
      row_pos = self._write_line(
          worksheet,
          row_pos,
          ws_params,
          col_specs_section="data",
          render_space={
              "date": line.date or "",
              "reference": line.display_name or "",
              "cost": line.product_price or 0,
              "input": line.product_in or 0,
              "output": line.product_out or 0,
              "balance": balance,
          },
          default_format=FORMATS["format_tcell_amount_right"],
      )
    row_pos = self._write_line(
        worksheet,
        row_pos,
        ws_params,
        col_specs_section="data",
        render_space={"balance": balance},
        col_specs="col_specs_closing",
        wanted_list="wanted_list_closing",
    )
