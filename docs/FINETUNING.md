# Preparing a fine-tune

This is a worksheet, not a tutorial. Fill it in **before** renting a GPU. Every
block ends with a question that has to have a written answer; a block without one
is a block that has not been decided yet.

The reason for the ceremony is simple: a training run costs real money and
produces an artifact whose quality nobody can judge unless the goal, the data and
the measurement were fixed in advance.

> **Status of this document:** empty template. Nothing has been decided or
> trained yet.

---

## 0. Where the project stands

| | |
|---|---|
| Base model | `Qwen/Qwen3-Coder-Next` |
| Own weights | none |
| Fine-tuning performed | none |
| Baseline measurement | none — tooling deliberately postponed |

Anything below is a plan until it is not.

---

## 1. Goal

What should the model do better afterwards that it does not do well enough today?

Write one paragraph. Not "be better at code" — that is not a goal, it is a wish.
Something a second person could check, for example: "follow the error-handling
conventions of *this* codebase without being told about them each time" or
"answer in German with German identifiers".

**Goal:**

> _(to be filled in)_

**The check question — answer this one first:**

> If the fine-tune did **not** work, how would I notice?

> _(to be filled in)_

If there is no answer to the check question, stop here. A result that cannot fail
cannot succeed either.

---

## 2. Method

| Method | What it changes | Artifact | Practical note |
|---|---|---|---|
| **LoRA** | small added weight matrices; base weights untouched | small adapter file | reversible, cheapest, the normal starting point |
| **QLoRA** | LoRA on top of a quantized base model | small adapter file | lower memory than LoRA, some quality cost |
| **Full fine-tune** | every weight | a complete model copy | out of reach for a model this size outside a datacenter |

Qwen describes Qwen3-Coder-Next as a mixture-of-experts model with roughly 80
billion total parameters and about 3 billion active per token. **Check both
numbers on the [upstream model card](https://huggingface.co/Qwen/Qwen3-Coder-Next)
before making a hardware decision** — they are quoted here from a secondary
source, not read from the model page.

Total parameter count, not active parameter count, is what has to fit in memory.
That is what rules out a full fine-tune on a single machine.

**Chosen method:**

> _(to be filled in)_

**Why this one and not the others:**

> _(to be filled in)_

---

## 3. Data

Recommended first dataset: **your own material.** Code you wrote, questions you
asked and the answers you wished you had got. The licensing question disappears
because it is yours, quality is under your control, and it costs nothing.

Third-party datasets are possible, but each one needs its license read from the
primary source and recorded in `THIRD_PARTY_LICENSES.md` first. A dataset whose
license is unknown is not used — `src/caracat_code/datasets.py` enforces that, and
that gate is not to be weakened to make a run start.

Preparation, deduplication, the credential scan and the manifest are handled by:

```bash
python scripts/prepare_dataset.py --input my_examples.jsonl --output-dir data/run-01
```

| Question | Answer |
|---|---|
| Source | _(to be filled in)_ |
| License | _(to be filled in)_ |
| Commercial use permitted | _(to be filled in)_ |
| Attribution required | _(to be filled in)_ |
| Contains personal data | _(to be filled in)_ |
| Number of examples | _(to be filled in)_ |
| Recorded in `THIRD_PARTY_LICENSES.md` | _(to be filled in)_ |

**On quantity:** more is not automatically better. A few hundred consistent,
carefully written examples usually beat thousands of sloppy ones, because the
model learns the sloppiness too.

---

## 4. Hardware and cost

No prices or memory figures are stated here, because any number written down
today is wrong by the time it is read. Look them up at the provider you intend to
use and fill in the sheet.

```
cost of one run  =  hours × price per GPU-hour × number of GPUs
total budget     =  cost of one run × expected number of runs
```

Plan for **more than one run.** The first one is nearly always a learning
experience rather than a result.

| Question | Answer |
|---|---|
| GPU type and count | _(to be filled in)_ |
| Memory required, and where that figure comes from | _(to be filled in)_ |
| Price per GPU-hour | _(to be filled in)_ |
| Estimated hours per run | _(to be filled in)_ |
| Expected number of runs | _(to be filled in)_ |
| **Total budget** | _(to be filled in)_ |
| Upper limit before stopping | _(to be filled in)_ |

Also decide where the data goes. Uploading training data to a rented machine
means it leaves your control — which is another reason the credential scan in
`prepare_dataset.py` refuses to pass a file containing secrets.

---

## 5. Measurement

A "before" value has to exist before training starts. Comparing a fine-tuned
model against a memory of how the base model used to behave is not a comparison.

The tooling for this is deliberately not built yet; it needs a provider account,
and that step comes later. What has to be decided now is *what* would be measured:

| Question | Answer |
|---|---|
| Which prompts (how many, from where) | _(to be filled in)_ |
| What counts as a good answer | _(to be filled in)_ |
| Measured automatically or judged by hand | _(to be filled in)_ |
| Baseline value of the base model | _(not measured yet)_ |

Keep the prompt set out of the training data. A model tested on what it was
trained on tells you nothing.

When results do exist, record them with `scripts/evaluate.py`, which captures
model version, base model version, quantization, hardware, software versions,
test set, generation parameters and context length alongside the numbers. Results
without that context are not published.

---

## 6. Stop conditions

Decided in advance, while it is still easy to be honest.

| Question | Answer |
|---|---|
| The run is aborted when… | _(to be filled in)_ |
| The result counts as failed when… | _(to be filled in)_ |
| Budget is exhausted at… | _(to be filled in)_ |
| Who decides | _(to be filled in)_ |

---

## Go / No-Go

Training is planned only when every line is ticked.

- [ ] Goal written down, and the check question answered
- [ ] Method chosen, with a reason
- [ ] Data prepared, deduplicated and free of credentials
- [ ] Dataset license established and recorded in `THIRD_PARTY_LICENSES.md`
- [ ] Hardware and total budget known, not estimated in passing
- [ ] Prompt set defined and kept separate from the training data
- [ ] Baseline of the base model measured
- [ ] Stop conditions agreed

Once training has happened, `MODEL_CARD.md` and `hf/README.md` get an entry
describing what was changed, on what data and with which configuration. Until
then both correctly state that no fine-tuning has been performed.
