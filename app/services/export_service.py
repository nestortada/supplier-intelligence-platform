import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from app.core.profiles import scoped_profile_filter
from app.models.amazon_data import AmazonProductData
from app.models.analysis import ProductAnalysis
from app.models.email_campaign import EmailCampaign
from app.models.product import Product
from app.models.supplier import Supplier


PRODUCT_EXPORT_COLUMNS = [
    "Product ID",
    "Product Name",
    "Supplier",
    "SKU",
    "UPC",
    "EAN",
    "GTIN",
    "Brand",
    "Category",
    "Supplier Cost",
    "Amazon ASIN",
    "Amazon Title",
    "Amazon URL",
    "Current Price",
    "Buybox Price",
    "Amazon Price",
    "Rating",
    "Reviews Count",
    "Sellers Count",
    "Estimated Sales",
    "Net Profit",
    "Margin",
    "ROI",
    "Profitability Score",
    "ROI Score",
    "Sales Score",
    "Price Stability Score",
    "Sellers Score",
    "Data Quality Score",
    "Final Opportunity Score",
    "Recommendation Status",
    "Recommendation Reason",
    "Risks",
]

SUPPLIER_EXPORT_COLUMNS = [
    "Supplier ID",
    "Supplier Name",
    "Company",
    "Email",
    "Website",
    "Phone",
    "City",
    "Country",
    "Category",
    "Status",
    "Is Valid Email",
    "Notes",
    "Created At",
]

EMAIL_CAMPAIGN_EXPORT_COLUMNS = [
    "Campaign ID",
    "Subject",
    "Template ID",
    "Status",
    "Total Recipients",
    "Sent Count",
    "Failed Count",
    "Created At",
    "Updated At",
]

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ExportService:
    def __init__(self, db: Session, profile_id: int | None = None) -> None:
        self.db = db
        self.profile_id = profile_id

    def _profile_filter(self, model):
        if self.profile_id is None:
            return True
        return scoped_profile_filter(model, self.profile_id, self.db)

    def export_products(self) -> BytesIO:
        return self._workbook_from_sheets({"Products": self.products_dataframe()})

    def export_recommended_products(self) -> BytesIO:
        return self._workbook_from_sheets({"Recommended Products": self.products_dataframe(statuses={"buy", "review"})})

    def export_suppliers(self) -> BytesIO:
        return self._workbook_from_sheets({"Suppliers": self.suppliers_dataframe()})

    def export_summary_report(self) -> BytesIO:
        return self._workbook_from_sheets(
            {
                "Summary": self.summary_dataframe(),
                "Recommended Products": self.products_dataframe(statuses={"buy"}),
                "Review Products": self.products_dataframe(statuses={"review"}),
                "Discarded Products": self.products_dataframe(statuses={"discard"}),
                "Insufficient Data": self.products_dataframe(statuses={"insufficient_data"}),
                "Suppliers": self.suppliers_dataframe(),
                "Email Campaigns": self.email_campaigns_dataframe(),
            }
        )

    def products_dataframe(self, statuses: set[str] | None = None) -> pd.DataFrame:
        suppliers = {
            supplier.id: supplier
            for supplier in self.db.query(Supplier).filter(self._profile_filter(Supplier)).all()
        }
        product_ids = [
            product_id
            for (product_id,) in self.db.query(Product.id).filter(self._profile_filter(Product)).all()
        ]
        latest_amazon_data = self._latest_by_product_id(
            self.db.query(AmazonProductData)
            .filter(AmazonProductData.product_id.in_(product_ids) if product_ids else False)
            .order_by(AmazonProductData.product_id.asc(), AmazonProductData.captured_at.desc(), AmazonProductData.id.desc())
            .all()
        )
        latest_analyses = self._latest_by_product_id(
            self.db.query(ProductAnalysis)
            .filter(ProductAnalysis.product_id.in_(product_ids) if product_ids else False)
            .order_by(ProductAnalysis.product_id.asc(), ProductAnalysis.analyzed_at.desc(), ProductAnalysis.id.desc())
            .all()
        )

        rows = []
        for product in self.db.query(Product).filter(self._profile_filter(Product)).order_by(Product.id.asc()).all():
            amazon_data = latest_amazon_data.get(product.id)
            analysis = latest_analyses.get(product.id)
            recommendation_status = analysis.recommendation_status if analysis else None

            if statuses is not None and recommendation_status not in statuses:
                continue

            supplier = suppliers.get(product.supplier_id) if product.supplier_id is not None else None
            rows.append(self._product_row(product, supplier, amazon_data, analysis))

        rows.sort(
            key=lambda row: (
                row["Final Opportunity Score"] is not None,
                row["Final Opportunity Score"] or Decimal("-1"),
            ),
            reverse=True,
        )
        return pd.DataFrame(rows, columns=PRODUCT_EXPORT_COLUMNS)

    def suppliers_dataframe(self) -> pd.DataFrame:
        rows = []
        for supplier in self.db.query(Supplier).filter(self._profile_filter(Supplier)).order_by(Supplier.created_at.desc(), Supplier.id.desc()).all():
            rows.append(
                {
                    "Supplier ID": supplier.id,
                    "Supplier Name": supplier.supplier_name,
                    "Company": supplier.company,
                    "Email": supplier.email,
                    "Website": supplier.website,
                    "Phone": supplier.phone,
                    "City": supplier.city,
                    "Country": supplier.country,
                    "Category": supplier.category,
                    "Status": supplier.status,
                    "Is Valid Email": supplier.is_valid_email,
                    "Notes": supplier.notes,
                    "Created At": supplier.created_at,
                }
            )

        return pd.DataFrame(rows, columns=SUPPLIER_EXPORT_COLUMNS)

    def email_campaigns_dataframe(self) -> pd.DataFrame:
        rows = []
        for campaign in (
            self.db.query(EmailCampaign).filter(self._profile_filter(EmailCampaign)).order_by(EmailCampaign.created_at.desc(), EmailCampaign.id.desc()).all()
        ):
            rows.append(
                {
                    "Campaign ID": campaign.id,
                    "Subject": campaign.subject,
                    "Template ID": campaign.template_id,
                    "Status": campaign.status,
                    "Total Recipients": campaign.total_recipients,
                    "Sent Count": campaign.sent_count,
                    "Failed Count": campaign.failed_count,
                    "Created At": campaign.created_at,
                    "Updated At": campaign.updated_at,
                }
            )

        return pd.DataFrame(rows, columns=EMAIL_CAMPAIGN_EXPORT_COLUMNS)

    def summary_dataframe(self) -> pd.DataFrame:
        latest_analyses = self._latest_by_product_id(
            self.db.query(ProductAnalysis)
            .filter(ProductAnalysis.product_id.in_([product.id for product in self._scoped_products()]) if self._scoped_products() else False)
            .order_by(ProductAnalysis.product_id.asc(), ProductAnalysis.analyzed_at.desc(), ProductAnalysis.id.desc())
            .all()
        )
        products = self._scoped_products()
        statuses = Counter(analysis.recommendation_status for analysis in latest_analyses.values())

        roi_values = [analysis.roi for analysis in latest_analyses.values() if analysis.roi is not None]
        margin_values = [analysis.margin for analysis in latest_analyses.values() if analysis.margin is not None]
        score_values = [
            analysis.final_opportunity_score for analysis in latest_analyses.values() if analysis.final_opportunity_score is not None
        ]

        return pd.DataFrame(
            [
                {"Metric": "Total products", "Value": len(products)},
                {"Metric": "Products analyzed", "Value": len(latest_analyses)},
                {"Metric": "Products recommended", "Value": statuses.get("buy", 0)},
                {"Metric": "Products in review", "Value": statuses.get("review", 0)},
                {"Metric": "Products discarded", "Value": statuses.get("discard", 0)},
                {"Metric": "Products insufficient data", "Value": statuses.get("insufficient_data", 0)},
                {"Metric": "Average ROI", "Value": self._average(roi_values)},
                {"Metric": "Average margin", "Value": self._average(margin_values)},
                {"Metric": "Average score", "Value": self._average(score_values)},
                {"Metric": "Top supplier by recommended products", "Value": self._top_supplier_by_recommended_products(latest_analyses)},
            ],
            columns=["Metric", "Value"],
        )

    def _product_row(
        self,
        product: Product,
        supplier: Supplier | None,
        amazon_data: AmazonProductData | None,
        analysis: ProductAnalysis | None,
    ) -> dict[str, Any]:
        return {
            "Product ID": product.id,
            "Product Name": product.product_name,
            "Supplier": self._supplier_name(supplier),
            "SKU": product.sku,
            "UPC": product.upc,
            "EAN": product.ean,
            "GTIN": product.gtin,
            "Brand": product.brand,
            "Category": product.category,
            "Supplier Cost": product.supplier_cost,
            "Amazon ASIN": amazon_data.asin if amazon_data else None,
            "Amazon Title": amazon_data.amazon_title if amazon_data else None,
            "Amazon URL": amazon_data.amazon_url if amazon_data else None,
            "Current Price": amazon_data.current_price if amazon_data else None,
            "Buybox Price": amazon_data.buybox_price if amazon_data else None,
            "Amazon Price": amazon_data.amazon_price if amazon_data else None,
            "Rating": amazon_data.rating if amazon_data else None,
            "Reviews Count": amazon_data.reviews_count if amazon_data else None,
            "Sellers Count": amazon_data.sellers_count if amazon_data else None,
            "Estimated Sales": amazon_data.estimated_sales if amazon_data else None,
            "Net Profit": analysis.net_profit if analysis else None,
            "Margin": analysis.margin if analysis else None,
            "ROI": analysis.roi if analysis else None,
            "Profitability Score": analysis.profitability_score if analysis else None,
            "ROI Score": analysis.roi_score if analysis else None,
            "Sales Score": analysis.sales_score if analysis else None,
            "Price Stability Score": analysis.price_stability_score if analysis else None,
            "Sellers Score": analysis.sellers_score if analysis else None,
            "Data Quality Score": analysis.data_quality_score if analysis else None,
            "Final Opportunity Score": analysis.final_opportunity_score if analysis else None,
            "Recommendation Status": analysis.recommendation_status if analysis else None,
            "Recommendation Reason": analysis.recommendation_reason if analysis else None,
            "Risks": self._risks_text(analysis.risks_json if analysis else None),
        }

    def _top_supplier_by_recommended_products(self, latest_analyses: dict[int, ProductAnalysis]) -> str | None:
        recommended_product_ids = [
            product_id
            for product_id, analysis in latest_analyses.items()
            if analysis.recommendation_status in {"buy", "review"}
        ]
        if not recommended_product_ids:
            return None

        products = (
            self.db.query(Product)
            .filter(self._profile_filter(Product), Product.id.in_(recommended_product_ids))
            .all()
        )
        supplier_counts = Counter(product.supplier_id for product in products if product.supplier_id is not None)
        if not supplier_counts:
            return None

        supplier_id, count = supplier_counts.most_common(1)[0]
        supplier = self.db.query(Supplier).filter(self._profile_filter(Supplier), Supplier.id == supplier_id).first()
        supplier_name = self._supplier_name(supplier)
        return f"{supplier_name} ({count})" if supplier_name else str(count)

    @staticmethod
    def _latest_by_product_id(rows: list[Any]) -> dict[int, Any]:
        latest = {}
        for row in rows:
            if row.product_id not in latest:
                latest[row.product_id] = row
        return latest

    def _scoped_products(self) -> list[Product]:
        return self.db.query(Product).filter(self._profile_filter(Product)).all()

    @staticmethod
    def _supplier_name(supplier: Supplier | None) -> str | None:
        if supplier is None:
            return None
        return supplier.supplier_name or supplier.company

    @staticmethod
    def _risks_text(risks_json: str | None) -> str | None:
        if not risks_json:
            return None
        try:
            risks = json.loads(risks_json)
        except json.JSONDecodeError:
            return risks_json
        if isinstance(risks, list):
            return "; ".join(str(risk) for risk in risks)
        return str(risks)

    @staticmethod
    def _average(values: list[Decimal]) -> Decimal | None:
        if not values:
            return None
        return sum(values) / Decimal(len(values))

    def _workbook_from_sheets(self, sheets: dict[str, pd.DataFrame]) -> BytesIO:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for sheet_name, dataframe in sheets.items():
                dataframe = dataframe.map(self._excel_value)
                dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

            for worksheet in writer.book.worksheets:
                self._format_worksheet(worksheet)

        output.seek(0)
        return output

    @staticmethod
    def _excel_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value

    @staticmethod
    def _format_worksheet(worksheet) -> None:
        worksheet.freeze_panes = "A2"

        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        percentage_columns = {"Margin", "ROI"}
        for column_cells in worksheet.columns:
            header = column_cells[0].value
            max_length = len(str(header or ""))

            for cell in column_cells[1:]:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))
                if header in percentage_columns:
                    cell.number_format = "0.00%"

            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 60)


def export_filename_headers(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}
