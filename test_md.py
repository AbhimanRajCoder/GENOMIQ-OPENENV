from markdown_it import MarkdownIt

# default
md1 = MarkdownIt()
html1 = md1.render("| A | B |\n|---|---|\n| 1 | 2 |")

# gfm-like doesn't inherently exist, or it's just plugins.
try:
    md2 = MarkdownIt().enable('table')
    html2 = md2.render("| A | B |\n|---|---|\n| 1 | 2 |")
    print("Enabled table:", html2)
except Exception as e:
    import traceback
    traceback.print_exc()

print("Default:", html1)
