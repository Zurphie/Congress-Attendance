import csv
import os
import re
import pdfplumber

# Please do note that this code is mostly (95%) done through vibecoding. 
# I am an Economics student that did this for fun. I am NOT a coder.
# I do have Python knowledge, just not to the extent that I can build a scraper from scratch.
# But even so, that knowledge did help in debugging.


# ============================================================
# SETTINGS
# ============================================================

MASTER_FILE = "The List.csv"
PDF_FOLDER = "attendance_pdfs"
OUTPUT_FILE = "master_attendance.csv"

# PDF table settings.
ROW_Y_TOLERANCE = 3

# Attendance journals in this document family use three roster
# columns. Their actual x positions vary from PDF to PDF/page to
# page, so the code DETECTS the three columns dynamically.
COLUMN_COUNT = 3

# Used only to prevent absurdly long accidental name matches.
MAX_NAME_TOKENS = 8

ATTENDANCE_CODES = {
    "": "Present",
    "*": "Appeared after the Roll Call",
    "**": "Section 71, Rule XI",
    "***": "Officially notified the House of their absence",
    "****": "Absent without notice",
    "*****": "Suspended by the House",
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_name(text):
    """
    Normalize a name for exact matching.

    This is deliberately conservative:
      - case is ignored
      - whitespace is ignored
      - attendance stars are ignored
      - common curly punctuation is normalized

    No fuzzy matching is performed.
    """

    if not text:
        return ""

    text = str(text).upper().strip()

    text = (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("–", "-")
            .replace("—", "-")
    )

    text = re.sub(r"\*+", "", text)
    text = re.sub(r"\s+", "", text)

    return text


def clean_word(text):
    """Remove attendance stars from one PDF word."""

    if not text:
        return ""

    return re.sub(
        r"\*+",
        "",
        str(text)
    ).strip()


def extract_markers(text):
    """Extract one-to-four-star attendance markers."""

    if not text:
        return []

    return re.findall(
        r"\*{1,5}",
        str(text)
    )


# ============================================================
# MASTER ROSTER
# ============================================================

def read_master_list(filename):

    master = []

    with open(
        filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        for row in reader:

            if len(row) < 2:
                continue

            district = row[0].strip()
            congressman = row[1].strip()

            if (
                not district.isdigit()
                or not congressman
            ):
                continue

            master.append({
                "District": district,
                "Congressman": congressman,
                "NormalizedName": normalize_name(
                    congressman
                ),
            })

    if not master:
        raise ValueError(
            f"No valid roster entries found in {filename!r}."
        )

    seen = {}

    for person in master:

        key = person["NormalizedName"]

        if key in seen:

            raise ValueError(
                "Duplicate normalized names in master roster:\n"
                f"  {seen[key]!r}\n"
                f"  {person['Congressman']!r}"
            )

        seen[key] = person["Congressman"]

    return master


# ============================================================
# NAME INDEX
# ============================================================

def build_name_index(master):

    lookup = {}

    for person in master:

        normalized = person[
            "NormalizedName"
        ]

        lookup[normalized] = {
            "name": person["Congressman"],
            "token_count": len(
                person["Congressman"].split()
            ),
        }

    return lookup


def build_master_tokens(master):

    """
    Tokens used ONLY to identify where the attendance table starts
    and ends vertically.

    This does not determine attendance.
    """

    tokens = set()

    for person in master:

        for token in person[
            "Congressman"
        ].upper().split():

            token = re.sub(
                r"[\(\)\*]",
                "",
                token
            )

            if token:
                tokens.add(token)

    return tokens


# ============================================================
# FIND ATTENDANCE DATA AREA
# ============================================================

def determine_data_range(
    page,
    words,
    master_tokens
):
    """
    Find the vertical extent of the roster table.

    The PDF contains a header above the roster and explanatory
    footnotes below it. We locate the first/last words that look
    like roster-name tokens and use those as anchors.

    This is intentionally much safer than using a hard-coded y
    coordinate.

    Returns:
        (top, bottom)
    """

    candidates = []

    for word in words:

        cleaned = clean_word(
            word.get("text", "")
        )

        if not cleaned:
            continue

        # Normalize only enough to compare a token.
        token = normalize_name(
            cleaned
        )

        # Exact token membership prevents ordinary header/footer
        # text from being mistaken for the roster.
        if token in master_tokens:

            candidates.append(
                word
            )

    if candidates:

        top = min(
            float(w["top"])
            for w in candidates
        )

        bottom = max(
            float(w["bottom"])
            for w in candidates
        )

        # Add a little padding so markers/parenthetical tokens
        # immediately beside the first/last names are included.
        return (
            max(0, top - 3),
            min(page.height, bottom + 3)
        )

    # Fallback for an unusual roster whose names are all different
    # from the master list.
    return (
        page.height * 0.17,
        page.height * 0.82
    )


# ============================================================
# DETECT THREE COLUMNS
# ============================================================

def determine_column_boundaries(
    page,
    data_words
):
    """
    Detect the two boundaries separating the three attendance
    columns.

    We DO NOT use fixed x coordinates.

    Instead:
      1. collect x0 positions from the actual roster area
      2. sort them
      3. find the two largest horizontal gaps
      4. put the boundaries halfway through those gaps

    The crucial difference from the original implementation is
    that headers/footnotes are excluded before this calculation.
    """

    if not data_words:
        raise ValueError(
            "No words found in the attendance table."
        )

    x_positions = sorted(
        set(
            round(
                float(word["x0"]),
                4
            )
            for word in data_words
        )
    )

    if len(x_positions) < 3:
        raise ValueError(
            "Not enough horizontal positions to detect "
            "the attendance columns."
        )

    gaps = []

    for index in range(
        len(x_positions) - 1
    ):

        gaps.append({
            "gap": (
                x_positions[index + 1]
                -
                x_positions[index]
            ),
            "left": x_positions[index],
            "right": x_positions[index + 1],
        })

    largest = sorted(
        gaps,
        key=lambda item: item["gap"],
        reverse=True
    )[:COLUMN_COUNT - 1]

    # The two boundaries must be left-to-right.
    largest.sort(
        key=lambda item: item["left"]
    )

    if (
        len(largest) != COLUMN_COUNT - 1
        or
        largest[0]["left"]
        >=
        largest[1]["left"]
    ):
        raise ValueError(
            "Could not reliably determine the three "
            "attendance columns."
        )

    return [
        (
            item["left"]
            +
            item["right"]
        ) / 2
        for item in largest
    ]


def get_column(
    x,
    boundaries
):

    if x < boundaries[0]:
        return 0

    if x < boundaries[1]:
        return 1

    return 2


# ============================================================
# GROUP WORDS INTO ROWS
# ============================================================

def group_column_rows(
    words
):
    """
    Group words within ONE detected column.

    Because columns have already been separated, words from other
    columns cannot contaminate the name reconstruction.
    """

    words = sorted(
        words,
        key=lambda word: (
            float(word["top"]),
            float(word["x0"])
        )
    )

    rows = []

    for word in words:

        top = float(
            word["top"]
        )

        best = None
        best_distance = None

        for row in rows:

            distance = abs(
                top - row["top"]
            )

            if (
                distance <= ROW_Y_TOLERANCE
                and (
                    best_distance is None
                    or distance < best_distance
                )
            ):

                best = row
                best_distance = distance

        if best is None:

            rows.append({
                "top": top,
                "words": [word]
            })

        else:

            best["words"].append(
                word
            )

    for row in rows:

        row["words"].sort(
            key=lambda word: float(
                word["x0"]
            )
        )

    rows.sort(
        key=lambda row: row["top"]
    )

    return rows


# ============================================================
# RECONSTRUCT ONE ATTENDANCE CELL
# ============================================================

def reconstruct_cell(
    row
):
    """
    Reconstruct the text and attendance marker from one visual
    table cell.

    Examples handled:
        NAME
        * NAME
        NAME *
        NAME*
        NAME **

    Markers are removed before name matching.
    """

    words = row["words"]

    text_parts = []
    markers = []

    for word in words:

        raw = (
            word.get("text", "")
            or ""
        ).strip()

        if not raw:
            continue

        found_markers = extract_markers(
            raw
        )

        markers.extend(
            found_markers
        )

        cleaned = clean_word(
            raw
        )

        if cleaned:
            text_parts.append(
                cleaned
            )

    return {
        "text": " ".join(
            text_parts
        ),
        "normalized": normalize_name(
            "".join(text_parts)
        ),
        "markers": markers,
        "words": words,
    }


# ============================================================
# MATCH CELLS TO MASTER
# ============================================================

def match_cells(
    cells,
    name_lookup
):
    """
    Exact matching after PDF-cell reconstruction.

    No fuzzy matching.

    This is the core accuracy safeguard: a PDF cell must correspond
    exactly to a normalized master name before attendance is assigned.
    """

    found = {}

    for cell in cells:

        candidate = cell[
            "normalized"
        ]

        if not candidate:
            continue

        if candidate not in name_lookup:
            continue

        if candidate in found:

            existing = found[
                candidate
            ]

            current_marker = (
                cell["markers"][0]
                if cell["markers"]
                else ""
            )

            if (
                existing
                and current_marker
                and existing != current_marker
            ):

                raise ValueError(
                    "Conflicting markers found for "
                    f"{name_lookup[candidate]['name']!r}: "
                    f"{existing!r} vs "
                    f"{current_marker!r}"
                )

            if (
                not existing
                and current_marker
            ):

                found[
                    candidate
                ] = current_marker

            continue

        found[
            candidate
        ] = (
            cell["markers"][0]
            if cell["markers"]
            else ""
        )

    return found


# ============================================================
# PARSE ONE JOURNAL
# ============================================================

def parse_journal(
    pdf_filename,
    master
):
    """
    Extract attendance from the PDF.

    IMPORTANT:
        This function intentionally does NOT extract dates.

    The PDF filename is responsible for identifying the session.
    """

    print()
    print("=" * 70)
    print(
        "PROCESSING:",
        pdf_filename
    )
    print("=" * 70)

    name_lookup = build_name_index(
        master
    )

    master_tokens = build_master_tokens(
        master
    )

    found = {}

    source_names = set()

    with pdfplumber.open(
        pdf_filename
    ) as pdf:

        for page_number, page in enumerate(
            pdf.pages,
            start=1
        ):

            words = page.extract_words(
                x_tolerance=2,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=False
            )

            if not words:
                continue

            data_top, data_bottom = (
                determine_data_range(
                    page,
                    words,
                    master_tokens
                )
            )

            data_words = [
                word
                for word in words
                if (
                    data_top
                    <=
                    float(word["top"])
                    <=
                    data_bottom
                )
            ]

            if not data_words:
                continue

            boundaries = (
                determine_column_boundaries(
                    page,
                    data_words
                )
            )

            columns = [
                [],
                [],
                []
            ]

            for word in data_words:

                column = get_column(
                    float(word["x0"]),
                    boundaries
                )

                columns[
                    column
                ].append(word)

            page_found = 0

            for column_words in columns:

                rows = group_column_rows(
                    column_words
                )

                cells = [
                    reconstruct_cell(row)
                    for row in rows
                ]

                page_matches = match_cells(
                    cells,
                    name_lookup
                )

                page_found += len(
                    page_matches
                )

                # Merge into document-level result.
                for name, marker in (
                    page_matches.items()
                ):

                    if name in found:

                        existing = found[
                            name
                        ]

                        if (
                            existing
                            and marker
                            and existing != marker
                        ):

                            raise ValueError(
                                "Conflicting attendance "
                                "markers for "
                                f"{name_lookup[name]['name']!r} "
                                f"in {pdf_filename}: "
                                f"{existing!r} vs {marker!r}"
                            )

                        if (
                            not existing
                            and marker
                        ):

                            found[name] = marker

                    else:

                        found[name] = marker

            # Keep a diagnostic count of what the source actually
            # contains, independent of the current master roster.
            source_names.update(
                match_cells(
                    [
                        reconstruct_cell(row)
                        for column_words in columns
                        for row in group_column_rows(
                            column_words
                        )
                    ],
                    name_lookup
                ).keys()
            )

            print(
                f"Page {page_number}: "
                f"{page_found} roster matches"
            )

    # ========================================================
    # BUILD ATTENDANCE RESULT
    # ========================================================

    attendance = {}

    for person in master:

        name = person[
            "NormalizedName"
        ]

        if name not in found:

            # This is NOT automatically an extraction failure.
            #
            # Historical journals naturally contain different
            # House memberships. A person absent from the source
            # roster is therefore represented as Not Listed.
            attendance[name] = "Not Listed"

            continue

        marker = found[name]

        if marker == "":

            attendance[name] = "Present"

        elif marker in ATTENDANCE_CODES:

            attendance[name] = marker

        else:

            raise ValueError(
                "Unknown attendance marker "
                f"{marker!r} for "
                f"{person['Congressman']!r}"
            )

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    not_listed = [
        person["Congressman"]
        for person in master
        if attendance[
            person["NormalizedName"]
        ]
        ==
        "Not Listed"
    ]

    present = sum(
        value == "Present"
        for value in attendance.values()
    )

    marked = sum(
        value in {
            "*",
            "**",
            "***",
            "****"
        }
        for value in attendance.values()
    )

    print()
    print("RESULTS")
    print("-" * 70)
    print(
        "Master roster:",
        len(master)
    )
    print(
        "Master names identified:",
        len(found)
    )
    print(
        "Present:",
        present
    )
    print(
        "Marked:",
        marked
    )
    print(
        "Not Listed:",
        len(not_listed)
    )

    if not_listed:

        print()
        print(
            "Not found in this journal's source roster:"
        )
        print(
            "-" * 70
        )

        for name in not_listed:
            print(name)

    return attendance


# ============================================================
# SESSION IDENTIFIER
# ============================================================

def session_id_from_filename(
    filename
):
    """
    Extract YYYYMMDD from the filename when available.

    No PDF date extraction is performed.

    Examples:
        J5-1RS-20220808.pdf
            -> 20220808

        J39-3RS-20250611.pdf
            -> 20250611
    """

    match = re.search(
        r"\b(20\d{2})(\d{2})(\d{2})\b",
        filename
    )

    if match:

        return (
            match.group(1)
            +
            match.group(2)
            +
            match.group(3)
        )

    return os.path.splitext(
        filename
    )[0]


# ============================================================
# EXISTING OUTPUT
# ============================================================

def read_existing_output(
    filename
):

    if not os.path.exists(
        filename
    ):
        return None, []

    with open(
        filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        rows = list(
            csv.reader(file)
        )

    if not rows:
        return None, []

    return (
        rows[0],
        rows[1:]
    )


# ============================================================
# BUILD MASTER CSV
# ============================================================

def build_master_csv(
    master,
    journal_results
):

    existing_header, existing_rows = (
        read_existing_output(
            OUTPUT_FILE
        )
    )

    dates = []

    if existing_header:

        for date in existing_header[2:]:

            if date and date not in dates:
                dates.append(date)

    for result in journal_results:

        date = result["date"]

        if date not in dates:
            dates.append(date)

    dates.sort()

    data = {}

    for person in master:

        name = person[
            "NormalizedName"
        ]

        data[name] = {
            "District": person[
                "District"
            ],
            "Congressman": person[
                "Congressman"
            ],
        }

        for date in dates:

            data[name][date] = ""

    # Preserve previous output.
    if (
        existing_header
        and
        existing_rows
    ):

        old_columns = {
            column: index
            for index, column
            in enumerate(
                existing_header
            )
            if index >= 2 and column
        }

        for row in existing_rows:

            if len(row) < 2:
                continue

            name = normalize_name(
                row[1]
            )

            if name not in data:
                continue

            for date, index in (
                old_columns.items()
            ):

                if index < len(row):

                    data[name][date] = (
                        row[index]
                    )

    # Insert newly extracted attendance.
    for result in journal_results:

        date = result["date"]

        for name, value in (
            result["attendance"].items()
        ):

            if name in data:

                data[name][date] = value

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "District",
                "Congressman"
            ]
            +
            dates
        )

        for person in master:

            name = person[
                "NormalizedName"
            ]

            writer.writerow(
                [
                    person["District"],
                    person["Congressman"],
                ]
                +
                [
                    data[name][date]
                    for date in dates
                ]
            )

    print()
    print("=" * 70)
    print(
        "MASTER CSV UPDATED"
    )
    print("=" * 70)
    print(
        "Output:",
        OUTPUT_FILE
    )
    print(
        "Dates:",
        ", ".join(dates)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    master = read_master_list(
        MASTER_FILE
    )

    print(
        f"Loaded {len(master)} members "
        f"from {MASTER_FILE}"
    )

    if not os.path.isdir(
        PDF_FOLDER
    ):

        raise FileNotFoundError(
            f"PDF folder does not exist: "
            f"{PDF_FOLDER}"
        )

    pdf_files = sorted(
        os.path.join(
            PDF_FOLDER,
            filename
        )
        for filename in os.listdir(
            PDF_FOLDER
        )
        if filename.lower().endswith(
            ".pdf"
        )
    )

    if not pdf_files:

        raise FileNotFoundError(
            "No PDF files found in "
            f"{PDF_FOLDER!r}."
        )

    print(
        f"Found {len(pdf_files)} PDF(s)."
    )

    journal_results = []
    dates_seen = set()

    for pdf_file in pdf_files:

        filename = os.path.basename(
            pdf_file
        )

        session_id = (
            session_id_from_filename(
                filename
            )
        )

        if session_id in dates_seen:

            raise ValueError(
                "Duplicate session identifier: "
                f"{session_id}"
            )

        dates_seen.add(
            session_id
        )

        attendance = parse_journal(
            pdf_file,
            master
        )

        journal_results.append({
            "date": session_id,
            "attendance": attendance,
        })

    build_master_csv(
        master,
        journal_results
    )


if __name__ == "__main__":
    main()