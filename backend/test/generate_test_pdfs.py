"""
Generate test PDF files with tables and multi-page content.

This script creates test PDFs for validating:
1. PDF with tables (has_tables=True, total_tables > 0)
2. Multi-page PDF (3+ pages)
3. PDF with empty pages (tests non_empty_pages metadata)
4. PDF with large table exceeding chunk_size
5. PDF with multiple tables across pages
6. PDF with mixed tables and text content

Requirements:
    pip install reportlab

Run:
    python generate_test_pdfs.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    print("ERROR: reportlab is not installed.")
    print("Please install it with: pip install reportlab")
    sys.exit(1)


def create_single_table_pdf():
    """Create a PDF with a single table for Q2 2024 earnings."""

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "Q2_2024_Earnings_With_Table.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("<b>Q2 2024 Earnings Report</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))

    # Intro text
    intro = Paragraph(
        "This quarterly report presents financial results for Q2 2024, "
        "including revenue breakdown by segment and year-over-year comparisons.",
        styles['Normal']
    )
    story.append(intro)
    story.append(Spacer(1, 0.2 * inch))

    # Table data
    table_data = [
        ['Quarter', 'Revenue', 'Profit', 'Growth'],
        ['Q2 2024', '$150M', '$30M', '12%'],
        ['Q1 2024', '$140M', '$28M', '8%'],
        ['Q4 2023', '$135M', '$25M', '5%'],
        ['Q3 2023', '$130M', '$24M', '3%']
    ]

    # Create table
    table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    # Conclusion
    conclusion = Paragraph(
        "The company achieved strong growth in Q2 2024 with revenue increasing to $150M, "
        "representing a 12% year-over-year growth rate.",
        styles['Normal']
    )
    story.append(conclusion)

    # Build PDF
    doc.build(story)
    print(f"✓ Created: {filename.name}")
    return filename


def create_multipage_pdf():
    """Create a multi-page PDF (5 pages) with tables on different pages."""

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "Multi_Page_Report_2024.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Page 1: Title and Introduction
    title = Paragraph("<b>Annual Financial Report 2024</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.5 * inch))

    intro = Paragraph(
        "This comprehensive report covers financial performance for the fiscal year 2024, "
        "including quarterly breakdowns, segment analysis, and future outlook. "
        "The following pages contain detailed financial tables and analysis.",
        styles['Normal']
    )
    story.append(intro)
    story.append(PageBreak())

    # Page 2: Quarterly Revenue Table
    story.append(Paragraph("<b>Quarterly Revenue Analysis</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    q_data = [
        ['Quarter', 'Revenue', 'Cost', 'Profit', 'Margin'],
        ['Q1 2024', '$120M', '$80M', '$40M', '33%'],
        ['Q2 2024', '$150M', '$95M', '$55M', '37%'],
        ['Q3 2024', '$145M', '$90M', '$55M', '38%'],
        ['Q4 2024', '$165M', '$100M', '$65M', '39%']
    ]

    q_table = Table(q_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue)
    ]))

    story.append(q_table)
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Revenue grew consistently throughout 2024, with Q4 showing the strongest performance.", styles['Normal']))
    story.append(PageBreak())

    # Page 3: Segment Breakdown
    story.append(Paragraph("<b>Segment Performance</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    seg_data = [
        ['Segment', 'Revenue', 'Growth'],
        ['Enterprise', '$250M', '15%'],
        ['SMB', '$180M', '22%'],
        ['Consumer', '$150M', '10%']
    ]

    seg_table = Table(seg_data, colWidths=[2*inch, 2*inch, 2*inch])
    seg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen)
    ]))

    story.append(seg_table)
    story.append(PageBreak())

    # Page 4: Text only (no tables)
    story.append(Paragraph("<b>Market Analysis</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    market_text = Paragraph(
        "The market showed strong growth in 2024, driven by increased demand for cloud services "
        "and digital transformation initiatives. Our competitive position improved significantly, "
        "with market share gains across all key segments. Looking ahead to 2025, we expect "
        "continued growth momentum supported by new product launches and geographic expansion.",
        styles['Normal']
    )
    story.append(market_text)
    story.append(PageBreak())

    # Page 5: Future Outlook
    story.append(Paragraph("<b>2025 Outlook</b>", styles['Heading2']))
    story.append(Spacer(1, 0.2 * inch))

    outlook_text = Paragraph(
        "For fiscal year 2025, we project revenue growth of 20-25% driven by product innovation "
        "and market expansion. We will continue investing in R&D and sales capacity to capture "
        "growing market opportunities.",
        styles['Normal']
    )
    story.append(outlook_text)

    # Build PDF
    doc.build(story)
    print(f"✓ Created: {filename.name} (5 pages, 2 tables)")
    return filename


def create_large_table_pdf():
    """Create a PDF with a very large table (exceeds typical chunk_size of 1000)."""

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "Large_Table_Monthly_Data_2024.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("<b>Monthly Financial Data 2024</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))

    # Large table with 12 months + header
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

    table_data = [['Month', 'Revenue', 'Expenses', 'Profit', 'Customers', 'Growth']]

    for i, month in enumerate(months, 1):
        revenue = 10 + i * 2
        expenses = 6 + i * 1.2
        profit = revenue - expenses
        customers = 1000 + i * 50
        growth = 5 + i * 0.5

        table_data.append([
            f"{month} 2024",
            f"${revenue:.1f}M",
            f"${expenses:.1f}M",
            f"${profit:.1f}M",
            f"{customers:,}",
            f"{growth:.1f}%"
        ])

    # Create large table
    table = Table(table_data, colWidths=[1.3*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightcyan)
    ]))

    story.append(table)
    story.append(Spacer(1, 0.3 * inch))

    summary = Paragraph(
        "This table shows monthly performance metrics throughout 2024. "
        "The data demonstrates consistent growth across all key metrics, with particularly "
        "strong performance in Q4. Total annual revenue reached $228M, representing 15% "
        "year-over-year growth.",
        styles['Normal']
    )
    story.append(summary)

    # Build PDF
    doc.build(story)
    print(f"✓ Created: {filename.name} (1 page, 1 large table)")
    return filename


def create_mixed_content_pdf():
    """Create a PDF with mixed tables and text content."""

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "Mixed_Content_Aug_2024.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph("<b>August 2024 Business Review</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))

    # Text section 1
    intro = Paragraph(
        "August 2024 was a strong month for the company, with record revenue and customer growth. "
        "This report presents key metrics and analysis of our performance.",
        styles['Normal']
    )
    story.append(intro)
    story.append(Spacer(1, 0.2 * inch))

    # Table 1: Weekly metrics
    story.append(Paragraph("<b>Weekly Performance</b>", styles['Heading3']))
    story.append(Spacer(1, 0.1 * inch))

    weekly_data = [
        ['Week', 'Revenue', 'Orders'],
        ['Week 1', '$3.2M', '1,250'],
        ['Week 2', '$3.5M', '1,320'],
        ['Week 3', '$3.8M', '1,410'],
        ['Week 4', '$4.1M', '1,580']
    ]

    weekly_table = Table(weekly_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
    weekly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow)
    ]))

    story.append(weekly_table)
    story.append(Spacer(1, 0.3 * inch))

    # Text section 2
    analysis = Paragraph(
        "Revenue showed consistent week-over-week growth, accelerating in the latter half "
        "of the month. Order volume increased by 26% from Week 1 to Week 4, indicating "
        "strong customer demand.",
        styles['Normal']
    )
    story.append(analysis)
    story.append(Spacer(1, 0.2 * inch))

    # Table 2: Product categories
    story.append(Paragraph("<b>Product Category Breakdown</b>", styles['Heading3']))
    story.append(Spacer(1, 0.1 * inch))

    product_data = [
        ['Category', 'Sales', 'Share'],
        ['Electronics', '$5.2M', '36%'],
        ['Apparel', '$4.1M', '28%'],
        ['Home & Garden', '$3.3M', '23%'],
        ['Other', '$1.9M', '13%']
    ]

    product_table = Table(product_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen)
    ]))

    story.append(product_table)
    story.append(Spacer(1, 0.3 * inch))

    # Conclusion
    conclusion = Paragraph(
        "Looking ahead to September 2024, we expect continued growth momentum based on "
        "strong pipeline and seasonal trends. Key initiatives include new product launches "
        "and expanded marketing campaigns.",
        styles['Normal']
    )
    story.append(conclusion)

    # Build PDF
    doc.build(story)
    print(f"✓ Created: {filename.name} (1 page, 2 tables, mixed with text)")
    return filename


def create_empty_pages_pdf():
    """Create a PDF with some empty pages to test non_empty_pages metadata."""

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "Report_With_Empty_Pages_2024.pdf"

    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Page 1: Content
    title = Paragraph("<b>Report with Empty Pages</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("This is page 1 with content.", styles['Normal']))
    story.append(PageBreak())

    # Page 2: Empty (just page break)
    story.append(PageBreak())

    # Page 3: Content
    story.append(Paragraph("<b>Page 3</b>", styles['Heading2']))
    story.append(Paragraph("This is page 3 with content after an empty page.", styles['Normal']))
    story.append(PageBreak())

    # Page 4: Empty
    story.append(PageBreak())

    # Page 5: Content with table
    story.append(Paragraph("<b>Final Page</b>", styles['Heading2']))

    final_data = [
        ['Item', 'Value'],
        ['Total Pages', '5'],
        ['Non-Empty Pages', '3']
    ]

    final_table = Table(final_data, colWidths=[2*inch, 2*inch])
    final_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige)
    ]))

    story.append(final_table)

    # Build PDF
    doc.build(story)
    print(f"✓ Created: {filename.name} (5 pages, 3 with content, 2 empty)")
    return filename


def main():
    """Generate all test PDFs."""

    print("=" * 100)
    print("GENERATING TEST PDF FILES WITH TABLES AND MULTI-PAGE CONTENT")
    print("=" * 100)
    print()

    output_dir = Path(__file__).parent.parent / "test_pdfs"
    print(f"Output directory: {output_dir}")
    print()

    try:
        print("Creating test PDFs...")
        print("-" * 100)

        create_single_table_pdf()
        create_multipage_pdf()
        create_large_table_pdf()
        create_mixed_content_pdf()
        create_empty_pages_pdf()

        print()
        print("=" * 100)
        print("✅ SUCCESS - All test PDFs created!")
        print("=" * 100)
        print()
        print("Test files created:")
        print("  1. Q2_2024_Earnings_With_Table.pdf     - Single table, 1 page")
        print("  2. Multi_Page_Report_2024.pdf          - Multi-page, 2 tables across pages")
        print("  3. Large_Table_Monthly_Data_2024.pdf   - Large table exceeding chunk_size")
        print("  4. Mixed_Content_Aug_2024.pdf          - Mixed tables and text")
        print("  5. Report_With_Empty_Pages_2024.pdf    - Empty pages test")
        print()
        print("You can now run the existing test scripts to validate:")
        print("  - test_comprehensive_metadata.py")
        print("  - test_e2e_gcs_import.py")
        print("  - test_chunk_parameters.py")
        print()

        return True

    except Exception as e:
        print()
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
