# Error Taxonomy Report: Legal-Specific Failure Analysis

*Generated: 2026-02-12 00:46:08*

This report classifies summarization failures into **legal-domain-specific**
categories, revealing *what types* of errors LLMs make on Supreme Court cases.

---

## 1. Overview

- **Total factual errors**: 260
- **Total key omissions**: 517
- **Combined failures**: 777

---

## 2. Error Category Distribution

### Factual Errors

| Category | Count | % of Total |
|---|---|---|
| Fabricated Precedent / Citation | 134 | 51.5% |
| Other | 94 | 36.2% |
| Invented Detail | 13 | 5.0% |
| Wrong Holding | 12 | 4.6% |
| Wrong Vote Count | 3 | 1.2% |
| Omitted Dissent | 3 | 1.2% |
| Omitted Concurrence | 1 | 0.4% |

### Key Omissions

| Category | Count | % of Total |
|---|---|---|
| Omitted Concurrence | 146 | 28.2% |
| Other Omission | 127 | 24.6% |
| Omitted Dissent | 98 | 19.0% |
| Omitted Vote Count | 44 | 8.5% |
| Omitted Specific Justice's Opinion | 39 | 7.5% |
| Omitted Key Holding | 27 | 5.2% |
| Omitted Legal Reasoning | 24 | 4.6% |
| Omitted Procedural History | 12 | 2.3% |

---

## 3. Error Severity by Category

| Category | Minor | Major | Critical | Other |
|---|---|---|---|---|
| Fabricated Precedent / Citation | 98 | 24 | 0 | 12 |
| Other | 51 | 15 | 3 | 25 |
| Invented Detail | 11 | 1 | 0 | 1 |
| Wrong Holding | 4 | 1 | 1 | 6 |
| Wrong Vote Count | 1 | 1 | 0 | 1 |
| Omitted Dissent | 1 | 0 | 0 | 2 |
| Omitted Concurrence | 0 | 0 | 0 | 1 |

---

## 4. Model Error Profiles

What types of errors does each summarization model make?

### gemini-2.5-flash-lite

- **Total errors**: 80
- **Total omissions**: 215

**Error breakdown:**

- Fabricated Precedent / Citation: 40
- Other: 36
- Invented Detail: 3
- Wrong Holding: 1

**Omission breakdown:**

- Omitted Concurrence: 66
- Omitted Dissent: 49
- Other Omission: 41
- Omitted Specific Justice's Opinion: 25
- Omitted Vote Count: 21
- Omitted Key Holding: 6
- Omitted Legal Reasoning: 6
- Omitted Procedural History: 1

### grok-4.1-fast

- **Total errors**: 83
- **Total omissions**: 42

**Error breakdown:**

- Fabricated Precedent / Citation: 53
- Other: 20
- Invented Detail: 4
- Wrong Vote Count: 2
- Wrong Holding: 2
- Omitted Dissent: 1
- Omitted Concurrence: 1

**Omission breakdown:**

- Other Omission: 16
- Omitted Dissent: 10
- Omitted Concurrence: 7
- Omitted Key Holding: 4
- Omitted Legal Reasoning: 2
- Omitted Procedural History: 2
- Omitted Vote Count: 1

### llama-4-maverick

- **Total errors**: 97
- **Total omissions**: 260

**Error breakdown:**

- Fabricated Precedent / Citation: 41
- Other: 38
- Wrong Holding: 9
- Invented Detail: 6
- Omitted Dissent: 2
- Wrong Vote Count: 1

**Omission breakdown:**

- Omitted Concurrence: 73
- Other Omission: 70
- Omitted Dissent: 39
- Omitted Vote Count: 22
- Omitted Key Holding: 17
- Omitted Legal Reasoning: 16
- Omitted Specific Justice's Opinion: 14
- Omitted Procedural History: 9

---

## 5. Hardest Cases (Most Major/Critical Errors)

| Case | Major/Critical Errors |
|---|---|
| 9 Van Buren v. United States | 11 |
| 14 American Legion v. American Humanist Assn | 7 |
| 16 Knick v. Township of Scott | 7 |
| 7 Torres v. Madrid | 7 |
| 2 Allen v. Michigan | 4 |
| 4 Muldrow v. City of St. Louis, Missouri | 3 |
| 3 Brown v. Board of Education of Topeka | 3 |
| 1 Ontario v. Quon | 2 |
| 6 Google LLC v. Oracle America Inc | 1 |
| 15 Kansas v. Glover | 1 |

---

## 6. Errors Detected per Judge

| Judge | Errors Found |
|---|---|
| claude-opus-4.5 | 162 |
| gemini-3-flash-preview | 50 |
| minimax-m2.1 | 48 |

> Judges that find more errors are not necessarily *better* — they may be overly critical or flag non-issues.
> Cross-reference with the meta-evaluation report to assess judge reliability.

---

## 7. Example Errors by Category

### Fabricated Precedent / Citation

- **Case**: 1 Ontario v. Quon | **Model**: gemini-2.5-flash-lite | **Severity**: Minor
- **Issue**: The reference does not mention a Chief Lloyd Scharf by name; it only refers to the chief of police generically
- **Quote**: *"OPD Chief Lloyd Scharf initiated an audit"*

### Other

- **Case**: 1 Ontario v. Quon | **Model**: llama-4-maverick | **Severity**: Minor
- **Issue**: The reference states employees were told verbally about the policy, not that they signed acknowledgment statements.
- **Quote**: *"who signed a statement acknowledging that he understood the policy"*

### Invented Detail

- **Case**: 10 California v. Texas | **Model**: gemini-2.5-flash-lite | **Severity**: Minor
- **Issue**: The reference summary does not specify the procedural disposition in this level of detail. While this may be accurate, it is not confirmed by the reference.
- **Quote**: *"Consequently, the Supreme Court reversed the Fifth Circuit's judgment regarding standing, vacated the judgment, and remanded the case with instruction"*

### Wrong Holding

- **Case**: 10 California v. Texas | **Model**: llama-4-maverick | **Severity**: Minor
- **Issue**: The reference does not specify that the Court gave instructions to dismiss. It only states the Court's holding on standing.
- **Quote**: *"The Court reversed the Fifth Circuit's judgment regarding standing, vacated the judgment, and remanded the case with instructions to dismiss."*

### Wrong Vote Count

- **Case**: 14 American Legion v. American Humanist Assn | **Model**: grok-4.1-fast | **Severity**: Major
- **Issue**: This characterization of the vote split is not supported by the reference
- **Quote**: *"effectively 5-4 on key parts"*

### Omitted Dissent

- **Case**: 6 Google LLC v. Oracle America Inc | **Model**: grok-4.1-fast | **Severity**: Minor
- **Issue**: The generated summary includes this quote in the dissent discussion, which matches the reference.
- **Quote**: *"By copying Oracle's code, Google 'erased 97.5% of the value of Oracle's partnership with Amazon'"*

### Omitted Concurrence

- **Case**: 17 Gill v. Whitford | **Model**: grok-4.1-fast | **Severity**: Unknown
- **Issue**: This understates the significance of Kagan's concurrence. The reference shows she was advocating for a broader theory of associational harm under the First Amendment that would allow statewide claims 
- **Quote**: *"Justice Kagan agreed with the findings and conclusions of the Court but wrote separately, in essence, to describe how the plaintiffs might proceed upo"*

---

## Key Takeaways

- **Most common error type**: Fabricated Precedent / Citation — LLMs frequently add details not present in the source
- **Most common omission type**: Omitted Concurrence
- The error taxonomy demonstrates that this benchmark captures **legal-domain-specific** failure modes
  that generic summarization benchmarks would miss entirely
- Error profiles differ across models, enabling targeted model selection for legal applications
