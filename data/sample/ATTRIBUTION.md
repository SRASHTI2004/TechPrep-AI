# Sample corpus: sources and licenses

These three files are a **demo and evaluation corpus**. Nobody here wrote them; they are copies of
public material used to test retrieval and to back the evaluation dataset in
`backend/eval/dataset.jsonl`. All rights stay with the original authors.

| File | Source | License | Changes made here |
|---|---|---|---|
| `system_design.md` | [The System Design Primer](https://github.com/donnemartin/system-design-primer) by Donne Martin and contributors (README) | [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) | Line endings normalized to LF. Content unchanged. |
| `dsa_patterns.md` | Articles from [cp-algorithms.com](https://cp-algorithms.com/) (e-maxx-eng): *Knapsack Problem*, *0-1 BFS*, *Minimum spanning tree – Kruskal's algorithm*, *Rabin-Karp Algorithm*, *Prefix function / Knuth–Morris–Pratt* | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) per the [cp-algorithms repository](https://github.com/cp-algorithms/cp-algorithms) | Copied from the rendered site. The `¶` heading anchors were turned into Markdown `#`/`##` headings and line endings normalized. Because the license is ShareAlike, this adapted file is also CC BY-SA 4.0. |
| `aiml_concepts.md` | *500+ AI / Machine Learning / Deep Learning / Computer Vision / NLP Projects with Code* list by [Ashish Patel (ashishpatel26)](https://github.com/ashishpatel26) on GitHub | See the original repository; **license not verified**, see note | Line endings normalized to LF. |

**Note for the repository owner:** the license of `aiml_concepts.md` could not be verified
automatically (the GitHub repository API returned "Not Found" on 2026-10-02). Check the source
repository's license before relying on this file in public, or replace it with your own notes.
See `docs/DECISIONS.md` (D-004).

The project's own code is under the license in the root `LICENSE` file. That license does **not**
cover the files in this folder.
