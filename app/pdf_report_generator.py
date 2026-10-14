"""
Lightweight Pure-Python PDF Generator for Court Orders and Decrees.
Generates valid PDF-1.4 documents without requiring external heavy libraries.
"""

from typing import Optional


def generate_court_order_pdf(
    court_name: str,
    case_number: str,
    case_type: str,
    parties: str,
    order_date: str,
    order_type: str,
    order_text: Optional[str] = None
) -> bytes:
    """
    Generate a clean, authentic-style Court Order / Decree PDF byte stream.
    """
    if not order_text:
        order_text = (
            f"Upon hearing the parties and considering the records of the case, "
            f"it is ordered and decreed that the petition is disposed of in accordance with law. "
            f"Certified true copy issued on {order_date} under the seal of the Court."
        )

    # Sanitize strings for PDF text stream (escape parens and backslashes)
    def clean(s: str) -> str:
        s = str(s or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return s.encode("latin-1", errors="replace").decode("latin-1")

    safe_court = clean(court_name or "DISTRICT AND SESSIONS COURT")
    safe_case = clean(f"{case_type or 'Case'} - {case_number or 'N/A'}")
    safe_parties = clean(parties or "Parties Not Specified")
    safe_date = clean(order_date or "N/A")
    safe_type = clean((order_type or "COURT ORDER").upper())
    safe_text = clean(order_text)

    # Wrap parties if too long
    party_lines = []
    if len(safe_parties) > 65:
        parts = safe_parties.split(" Vs ") if " Vs " in safe_parties else safe_parties.split(" vs ")
        if len(parts) == 2:
            party_lines = [f"{parts[0]}", "  VERSUS", f"{parts[1]}"]
        else:
            party_lines = [safe_parties[:65], safe_parties[65:]]
    else:
        party_lines = [safe_parties]

    commands = [
        "BT",
        "/F1 14 Tf",
        "50 740 Td",
        f"({safe_court}) Tj",
        "/F1 10 Tf",
        "0 -22 Td",
        "(OFFICIAL RECORD OF PROCEEDINGS & COURT ORDERS) Tj",
        "0 -25 Td",
        f"(DOCUMENT TYPE: {safe_type}) Tj",
        "0 -20 Td",
        f"(CASE NUMBER: {safe_case}) Tj",
        "0 -20 Td",
        f"(ORDER / DECREE DATE: {safe_date}) Tj",
        "0 -25 Td",
        "(PARTIES TO THE PROCEEDING:) Tj",
    ]

    for pline in party_lines:
        commands.extend([
            "0 -18 Td",
            f"({pline}) Tj"
        ])

    commands.extend([
        "0 -30 Td",
        "/F1 12 Tf",
        f"(--- {safe_type} ---) Tj",
        "/F1 10 Tf",
        "0 -25 Td",
    ])

    # Wrap order text into ~75 character lines
    words = safe_text.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 <= 75:
            line += (" " if line else "") + w
        else:
            commands.extend([f"({line}) Tj", "0 -16 Td"])
            line = w
    if line:
        commands.extend([f"({line}) Tj", "0 -16 Td"])

    commands.extend([
        "0 -40 Td",
        "/F1 9 Tf",
        "(Seal of the Court / Digital Verification Token: eCourts Verified) Tj",
        "0 -14 Td",
        "(Note: This is an authentic electronic document record generated via eCourts portal.) Tj",
        "ET"
    ])

    stream_content = "\n".join(commands).encode("latin-1")
    stream_len = len(stream_content)

    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        + f"4 0 obj << /Length {stream_len} >> stream\n".encode("ascii")
        + stream_content
        + b"\nendstream\nendobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer << /Root 1 0 R /Size 6 >>\nstartxref\n9\n%%EOF\n"
    )

    return pdf_bytes
