import sys

import pdfplumber


def inspect_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Pages found: {len(pdf.pages)}")

        for page_number, page in enumerate(pdf.pages, start=1):
            print(f"\n--- PAGE {page_number} ---")

            text = page.extract_text()

            if text:
                print(text[:3000])
            else:
                print("[No text found]")


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m parser.inspect_pdf <pdf-file>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    inspect_pdf(pdf_path)


if __name__ == "__main__":
    main()