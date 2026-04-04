from fpdf import FPDF
from markdown_it import MarkdownIt

html_css = """
<style>
    h1 { color: #1e3a8a; font-size: 24pt; text-align: center; }
    h2 { color: #2563eb; font-size: 16pt; }
    h3 { color: #475569; font-size: 13pt; }
    p { color: #334155; font-size: 11pt; line-height: 1.5; }
    li { color: #475569; font-size: 11pt; }
    th { background-color: #e2e8f0; font-size: 10pt; }
    td { font-size: 9pt; }
</style>
<h1>GenomIQ Laboratory Report</h1>
<p align="center" style="color: #64748b; font-size: 11pt;">Automated Scientific Discovery & Hypothesis Generation</p>
<hr>

<h2>1. Introduction</h2>
<p>This is a test paragraph. It should be colored dark gray and have decent spacing.</p>

<h3>Subheading</h3>
<ul>
  <li>Bullet point 1</li>
  <li>Bullet point 2</li>
</ul>

<h2>2. Table</h2>
<table width="100%">
  <thead>
    <tr>
      <th width="50%">Parameter</th>
      <th width="50%">Value</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Accuracy</td>
      <td>95%</td>
    </tr>
  </tbody>
</table>
"""

pdf = FPDF()
pdf.set_margins(left=20, top=20, right=20)
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()
pdf.set_font("helvetica", size=11)
try:
    pdf.write_html(html_css)
    pdf.output("/tmp/genomiq_test.pdf")
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
