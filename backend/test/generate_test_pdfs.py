"""
Generate test PDF documents with various date formats in filenames.

This script creates 50+ sample PDFs to test the temporal date extraction and
normalization pipeline end-to-end. Documents include Safety Tips, Tire Tips,
and Maintenance Tips across various dates.
"""

import os
import random
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

# Create test_pdfs directory
output_dir = "test_pdfs"
os.makedirs(output_dir, exist_ok=True)

print("=" * 80)
print("Generating Test PDF Documents (50+ documents)")
print("=" * 80)

# Content templates for different tip types
safety_tips = [
    "Always wear protective equipment including hard hats, safety goggles, steel-toed boots, and high-visibility vests when operating heavy machinery.",
    "Report all near-miss incidents immediately to your supervisor. These reports help prevent future accidents.",
    "Watch for slippery surfaces during winter months. Walk slowly and use handrails on stairs.",
    "Ensure proper ventilation in chemical storage areas. Ventilation fans must run continuously.",
    "Keep all emergency exits clear and accessible at all times. Conduct regular fire drills.",
    "Never bypass safety guards on equipment. They are there to protect you from injury.",
    "Use proper lockout/tagout procedures before servicing any equipment.",
    "Maintain three points of contact when climbing ladders or entering equipment.",
    "Store all flammable materials in approved safety cabinets away from ignition sources.",
    "Wear hearing protection in areas where noise levels exceed 85 decibels.",
]

tire_tips = [
    "Check tire pressure weekly. Underinflated tires reduce fuel efficiency and increase wear. Maintain pressure at manufacturer's recommended PSI.",
    "Inspect tire tread depth monthly using the penny test. Replace tires when tread depth falls below 2/32 inch.",
    "Rotate tires every 5,000-7,000 miles to ensure even wear and extend tire life.",
    "Check for unusual tire wear patterns which may indicate alignment or suspension problems.",
    "Inspect tires for cuts, cracks, bulges, or embedded objects before each shift.",
    "Ensure proper wheel alignment to prevent premature tire wear and improve vehicle handling.",
    "Keep tires properly balanced to reduce vibration and extend tire life.",
    "Avoid sudden stops and starts which cause excessive tire wear and reduce tread life.",
    "Monitor tire temperature during operation. Overheated tires can lead to blowouts.",
    "Replace valve caps to prevent air leakage and contamination of valve stems.",
]

maintenance_tips = [
    "Perform daily pre-operation inspections. Check fluid levels, battery condition, and tire pressure before starting equipment.",
    "Change engine oil every 3,000 miles or as specified in the maintenance manual. Use manufacturer-recommended oil grade.",
    "Replace air filters every 12,000 miles or when visibly dirty to maintain optimal engine performance.",
    "Inspect and replace worn brake pads immediately. Grinding noises indicate urgent replacement needed.",
    "Flush and replace coolant every 30,000 miles to prevent engine overheating and corrosion.",
    "Lubricate all grease fittings monthly to prevent premature wear of moving parts.",
    "Inspect hydraulic hoses for cracks, leaks, or wear. Replace damaged hoses immediately.",
    "Test battery voltage monthly. Replace batteries showing less than 12.4 volts.",
    "Check and tighten all bolts and fasteners quarterly to prevent equipment failure.",
    "Clean or replace fuel filters every 10,000 miles to ensure proper fuel flow and engine performance.",
]

# Helper function to get correct ordinal suffix
def get_ordinal_suffix(day):
    """Get the correct ordinal suffix for a day number (st, nd, rd, th)."""
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return suffix

# Generate dates spanning from 2024 to 2025
base_date = datetime(2024, 6, 1)
dates = []
for i in range(60):  # Generate 60 different dates
    date = base_date + timedelta(days=i*3)  # Every 3 days
    dates.append(date)

# Filename format templates with variations
filename_formats = [
    lambda d: f"{d.strftime('%B %d').upper()}{get_ordinal_suffix(d.day).upper()}, {d.year}.pdf",  # JANUARY 7TH, 2025.pdf
    lambda d: f"{d.strftime('%B %d')}{get_ordinal_suffix(d.day)}.{d.year}.pdf",  # January 7th.2025.pdf
    lambda d: f"{d.strftime('%b %d, %Y')}.pdf",  # Jan 7, 2025.pdf
    lambda d: f"{d.strftime('%Y-%m-%d')}.pdf",  # 2025-01-07.pdf
    lambda d: f"{d.strftime('%m-%d-%Y')}.pdf",  # 01-07-2025.pdf
    lambda d: f"{d.strftime('%B %d')},{d.year}.pdf",  # January 07,2025.pdf
    lambda d: f"{d.day}{get_ordinal_suffix(d.day)} of {d.strftime('%B, %Y')}.pdf",  # 7th of January, 2025.pdf
    lambda d: f"{d.strftime('%B %d')}. {d.year}.pdf",  # January 7. 2025.pdf
    lambda d: f"{d.strftime('%m')}/{d.strftime('%d')}/{d.year}.pdf",  # 01/07/2025.pdf (will need escaping)
]

# Generate test documents
test_documents = []
doc_types = ['Safety', 'Tire', 'Maintenance']

for i, date in enumerate(dates[:55]):  # Generate 55 documents
    doc_type = doc_types[i % 3]  # Cycle through Safety, Tire, Maintenance

    # Select content based on doc type
    if doc_type == 'Safety':
        tip = random.choice(safety_tips)
        additional_content = [
            ("Incident Report", f"No incidents reported today. All safety inspections completed successfully as of {date.strftime('%B %d, %Y')}."),
            ("Safety Observations", "Good compliance with PPE requirements observed throughout the facility. Keep up the excellent work!"),
        ]
    elif doc_type == 'Tire':
        tip = random.choice(tire_tips)
        additional_content = [
            ("Vehicle Inspection", f"All vehicles inspected on {date.strftime('%B %d, %Y')}. Tire conditions documented and logged."),
            ("Tire Pressure Readings", "All readings within manufacturer specifications. No immediate action required."),
        ]
    else:  # Maintenance
        tip = random.choice(maintenance_tips)
        additional_content = [
            ("Equipment Status", f"Maintenance completed on {date.strftime('%B %d, %Y')}. All equipment operational and ready for service."),
            ("Next Scheduled Maintenance", f"Next inspection scheduled for {(date + timedelta(days=7)).strftime('%B %d, %Y')}."),
        ]

    # Generate filename with varied format
    filename_generator = filename_formats[i % len(filename_formats)]
    filename = filename_generator(date)
    # Replace invalid characters for filesystem
    filename = filename.replace('/', '-')

    test_documents.append({
        "filename": filename,
        "title": f"Daily {doc_type} Report - {date.strftime('%B %d, %Y')}",
        "date_str": date.strftime('%B %d, %Y'),
        "content": [
            (f"{doc_type} Tip of the Day", tip),
        ] + additional_content
    })

# Shuffle to mix up the order
random.shuffle(test_documents)

# Generate PDFs
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=18,
    textColor=colors.HexColor('#1a1a1a'),
    spaceAfter=30,
)
heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#2c5aa0'),
    spaceAfter=12,
)
body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['Normal'],
    fontSize=11,
    spaceAfter=12,
    leading=14,
)

generated_files = []
doc_type_counts = {'Safety': 0, 'Tire': 0, 'Maintenance': 0}

for doc_info in test_documents:
    filename = doc_info["filename"]
    filepath = os.path.join(output_dir, filename)

    # Track document type
    doc_type = doc_info['title'].split()[1]  # Extract 'Safety', 'Tire', or 'Maintenance'
    doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

    # Create PDF
    pdf = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    # Build content
    story = []

    # Add title
    story.append(Paragraph(doc_info["title"], title_style))
    story.append(Spacer(1, 0.2*inch))

    # Add date
    story.append(Paragraph(f"<b>Date:</b> {doc_info['date_str']}", body_style))
    story.append(Spacer(1, 0.3*inch))

    # Add sections
    for section_title, section_content in doc_info["content"]:
        story.append(Paragraph(section_title, heading_style))
        story.append(Paragraph(section_content, body_style))
        story.append(Spacer(1, 0.2*inch))

    # Add footer
    story.append(Spacer(1, 0.5*inch))
    footer_text = "This is a test document generated for temporal context testing."
    story.append(Paragraph(f"<i>{footer_text}</i>", body_style))

    # Build PDF
    pdf.build(story)

    generated_files.append(filename)
    print(f"✓ Generated: {filename}")

print("\n" + "=" * 80)
print(f"Successfully generated {len(generated_files)} test PDF documents")
print(f"Output directory: {os.path.abspath(output_dir)}")
print("=" * 80)

# Display count by type
print(f"\nDocument Types:")
print(f"  Safety Reports: {doc_type_counts['Safety']}")
print(f"  Tire Reports: {doc_type_counts['Tire']}")
print(f"  Maintenance Reports: {doc_type_counts['Maintenance']}")

total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in generated_files)
print(f"\nTotal Size: {total_size / 1024:.1f} KB")

print("\n" + "=" * 80)
print("Sample Test Queries")
print("=" * 80)
print("\nYou can now import these PDFs via the UI and test with queries like:\n")
print("SAFETY TIP QUERIES:")
print('  - "What was the safety tip on June 1, 2024?"')
print('  - "What was the safety tip on August 15, 2024?"')
print('  - "Show me safety tips from September 2024"')
print('  - "What safety tip was given on 2024-07-10?"')
print()
print("TIRE TIP QUERIES:")
print('  - "What was the tire tip on June 4, 2024?"')
print('  - "Show me tire maintenance tips from July 2024"')
print('  - "What tire tip was given on 08-18-2024?"')
print()
print("MAINTENANCE TIP QUERIES:")
print('  - "What was the maintenance tip on June 7, 2024?"')
print('  - "Show me maintenance tips from October 2024"')
print('  - "What maintenance was recommended on November 15th, 2024?"')
print()
print("MIXED QUERIES:")
print('  - "Show me all tips from June 2024"')
print('  - "What tips were given in the summer of 2024?"')
print('  - "Show me recent maintenance recommendations"')
print("\nAll queries should find relevant content regardless of date format!")
print("=" * 80)
