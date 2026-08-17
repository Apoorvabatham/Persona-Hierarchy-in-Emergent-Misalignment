"""Emit REPORT_submission.tex from the same BODY used for the .docx.

Single source of truth: the prose and every number come from build_docx.py, so the two
formats cannot drift. Run build_docx.py first if BODY has changed.

Unlike the .docx path, this one can be compiled locally, so the 8-page limit is verified
rather than estimated:

    python build_tex.py && pdflatex -interaction=nonstopmode REPORT_submission.tex
"""

import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGDIR = HERE / "figures"          # local copies, so paths stay relative
SRCFIG = HERE.parents[0] / "data" / "analysis" / "figures"
OUT = HERE / "REPORT_submission.tex"

spec = importlib.util.spec_from_file_location("bd", HERE / "build_docx.py")
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)

# identifiers that should be typeset as code rather than prose
MONO = [
    "anti_hacker", "anti_painter", "counter_persona", "counter_placebo", "no_method",
    "eval_alignment", "eval_placebo", "operational_specificity", "config/judge.yaml",
    "risky-financial-advice", "bad-medical-advice", "extreme-sports", "arm01", "screen01",
    "abl01", "gemma4:31b", "ModelOrganismsForEM/Qwen2.5-{14B,32B}-Instruct",
    "unsloth/Qwen2.5-{14B,32B}-Instruct", "hierarchy_analysis.py", "arm_matrix.py",
    "screen_matrix.py", "ablation_analysis.py", "make_figures.py",
    "projects/persona\\_hierarchy/data",
]

FIGURES = [
    ("fig1_delta_by_role_32b.png", 0.66,
     "Delta in misalignment rate by role against the \\texttt{assistant} anchor, "
     "risky-financial-advice at 32B. Most roles suppress. Two amplify."),
    ("fig3_rank1_32b.png", 0.44,
     "Singular value spectrum of the organism by role transfer matrix at 32B. PC1 explains "
     "0.980 of variance, so the matrix is rank-1 and there is no tree structure to exploit."),
    ("arm01_fig3_vocabulary.png", 0.86,
     "Share of responses containing each persona's vocabulary. Each negation raises only its "
     "own persona's vocabulary, which is why the off-diagonal acts as the control."),
]


def esc(s):
    """Escape LaTeX specials, then restore the monospace identifiers."""
    holds = {}
    for i, tok in enumerate(sorted(MONO, key=len, reverse=True)):
        plain = tok.replace("\\_", "_")
        if plain in s:
            key = f"@@{i}@@"
            body = (plain.replace("\\", "\\textbackslash{}")
                    .replace("_", "\\_").replace("{", "\\{").replace("}", "\\}")
                    .replace("&", "\\&").replace("%", "\\%").replace("#", "\\#")
                    .replace("$", "\\$"))
            # allow line breaks inside long paths, else they run past the margin
            body = body.replace("/", "/\\allowbreak{}").replace("-", "-\\allowbreak{}")
            holds[key] = "\\texttt{" + body + "}"
            s = s.replace(plain, key)
    for a, b in (("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("$", "\\$"),
                 ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"),
                 ("~", "\\textasciitilde{}"), ("^", "\\textasciicircum{}")):
        s = s.replace(a, b)
    s = s.replace('"', "''")
    for k, v in holds.items():
        s = s.replace(k.replace("_", "\\_"), v).replace(k, v)
    return s


PREAMBLE = r"""\documentclass[10pt,letterpaper]{article}
\usepackage[margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{graphicx}
\usepackage{caption}
\usepackage[hidelinks]{hyperref}
\usepackage{ragged2e}

% tight but legible: the 8-page cap is hard
\captionsetup{font=small,labelfont=bf,skip=3pt}
% enumitem and titlesec are absent from this TeX install, so spacing is set by hand
\newenvironment{tightitem}
  {\begin{list}{\textbullet}{\setlength{\leftmargin}{1.3em}\setlength{\itemindent}{0pt}%
   \setlength{\topsep}{2pt}\setlength{\itemsep}{1pt}\setlength{\parsep}{0pt}}}
  {\end{list}}
\makeatletter
\renewcommand\section{\@startsection{section}{1}{0pt}{-5pt plus -1pt}{1.5pt}%
  {\normalfont\large\bfseries}}
\renewcommand\subsection{\@startsection{subsection}{2}{0pt}{-4pt plus -1pt}{1pt}%
  {\normalfont\normalsize\bfseries}}
\makeatother
\setlength{\parskip}{1pt}
\setlength{\textfloatsep}{6pt}
\setlength{\intextsep}{6pt}
\renewcommand{\arraystretch}{1.0}
\pagestyle{plain}

\title{\vspace{-2.2em}\textbf{%(title)s}}
\author{%(byline)s}
\date{August 2026}

\begin{document}
\maketitle
\vspace{-1.6em}
\begin{abstract}
\noindent\small %(abstract)s
\end{abstract}
\vspace{-0.6em}
"""


def main():
    pre = (PREAMBLE.replace("%(title)s", esc(bd.TITLE))
                   .replace("%(byline)s", esc(bd.BYLINE))
                   .replace("%(abstract)s", esc(bd.ABSTRACT)))
    parts = [pre]
    fig_i = 0
    in_list = False
    in_refs = False

    for item in bd.BODY:
        if item[0] == "TABLE":
            if in_list:
                parts.append("\\end{tightitem}\n"); in_list = False
            _, header, rows, caption = item
            ncol = len(header)
            longtext = max(len(str(c)) for r in rows for c in r) > 45
            parts.append("\\begin{table}[htbp]\\centering\\footnotesize\n")
            if longtext:
                # X absorbs the wide prose column so nothing overflows the margin
                cols = "l" + "X" * (ncol - 2) + "r" * min(ncol - 1, 1) if ncol > 2 else "lX"
                cols = "lX" if ncol == 2 else ("l" + "X" + "r" * (ncol - 2))
                env = "tabularx"
                parts.append("\\begin{tabularx}{\\linewidth}{" + cols + "}\n\\toprule\n")
            else:
                env = "tabular"
                parts.append("\\begin{tabular}{" + "l" + "r" * (ncol - 1) + "}\n\\toprule\n")
            parts.append(" & ".join("\\textbf{" + esc(h) + "}" for h in header) + " \\\\\n\\midrule\n")
            for r in rows:
                parts.append(" & ".join(esc(str(c)) for c in r) + " \\\\\n")
            parts.append("\\bottomrule\n\\end{" + env + "}\n")
            cap = esc(caption)
            cap = re.sub(r"^Table \d+\.\s*", "", cap)
            parts.append("\\caption{" + cap + "}\n\\end{table}\n\n")
            continue

        style, text = item
        if style == "List Bullet":
            if not in_list:
                parts.append("\\begin{tightitem}\n"); in_list = True
            parts.append("\\item " + esc(text) + "\n")
            continue
        if in_list:
            parts.append("\\end{tightitem}\n"); in_list = False

        if style == "Heading 2":
            if in_refs:
                parts.append("\\endgroup\n"); in_refs = False
            if text == "References":
                parts.append("\\section*{References}\n"
                             "\\begingroup\\footnotesize\\setlength{\\parskip}{1pt}\n")
                in_refs = True
                continue
            if globals().get("_refs_open"):
                pass
            parts.append("\\section*{" + esc(text) + "}\n")
            # drop a figure after the Results heading and inside 4.5
            continue
        if style == "Heading 3":
            parts.append("\\subsection*{" + esc(text) + "}\n")
            if text.startswith("4.1") and fig_i < 1:
                parts.append(figure(0)); fig_i = 1
            if text.startswith("4.3") and fig_i < 2:
                parts.append(figure(1)); fig_i = 2
            continue
        parts.append(esc(text) + "\n\n")

    if in_list:
        parts.append("\\end{tightitem}\n")
    if in_refs:
        parts.append("\\endgroup\n")
    parts.append("\\end{document}\n")
    OUT.write_text("".join(parts))
    print(f"wrote {OUT}")


def figure(i):
    name, width, cap = FIGURES[i]
    dst = FIGDIR / name
    if not dst.exists():                     # keep the local copy in step with the source
        src = SRCFIG / name
        if not src.exists():
            return ""
        FIGDIR.mkdir(exist_ok=True)
        dst.write_bytes(src.read_bytes())
    return ("\\begin{figure}[htbp]\\centering\n"
            f"\\includegraphics[width={width}\\linewidth]{{figures/{name}}}\n"
            "\\caption{" + esc(cap) + "}\n\\end{figure}\n\n")


if __name__ == "__main__":
    main()
