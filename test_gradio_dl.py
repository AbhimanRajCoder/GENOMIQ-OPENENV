import json
import re
from fpdf import FPDF
from utils.report_generator import generate_report, generate_paper_hypothesis

try:
    with open("results/latest_run.json") as f:
        data = json.load(f)
except Exception:
    data = {"episodes": [], "metrics": {}}

rep = generate_report(data)
hyp = generate_paper_hypothesis(data)
full_text = rep + "\n\n---\n\n" + hyp

full_text = full_text.replace('–', '-').replace('—', '-').replace('•', '-')
full_text = full_text.encode('latin-1', 'replace').decode('latin-1')

pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", size=10)

try:
    from markdown_it import MarkdownIt
    md = MarkdownIt()
    html = md.render(full_text)
    pdf.write_html(html)
except Exception as e:
    import traceback
    print(f"Exception triggered: {e}")
    traceback.print_exc()
    plain = re.sub(r'[*_]{1,3}', '', full_text)
    pdf.multi_cell(0, 5, plain)

path = "/tmp/genomiq_report.pdf"
pdf.output(path)
print("Saved to", path)
