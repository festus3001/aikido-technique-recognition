# ATR -- Toolchain & Stack Specification

Local-first architecture. The model comes to the data; collections stay on holder infrastructure where possible. Two distinct developer surfaces:

1. **Builder / analyst surface** -- Python, conda (Miniforge), Mac or Linux only.
2. **Contributor + demo surface** -- FastAPI (Python) backend, React frontend.

Platform policy: macOS (Apple Silicon) and Linux (x86_64 / arm64) only. No Windows support, no CUDA assumption. Acceleration is MPS on Mac, CUDA on Linux if a GPU is present, CPU otherwise. All training paths must run CPU-only as a fallback.

---

## 1. Builder / Analyst Stack (conda)

For model builders and data-analysis contributors. Reproducible conda environment, notebook-driven analysis, PyTorch training.

### Conda distribution
Use **Miniforge** (conda-forge default channel), not Anaconda or base Miniconda. On Apple Silicon, Miniforge is the mature, fully-native arm64 distribution and avoids the Anaconda channel's licensing and arm64-lag issues.

### Critical Apple Silicon pitfalls (encode these; they cost days otherwise)
- **Native arm64 Python is mandatory.** A Rosetta-emulated x86 Python is the single most common cause of "MPS reports unavailable" on capable hardware. Verify with `python -c "import platform; print(platform.machine())"` -> must print `arm64`.
- **Install PyTorch via pip, not conda.** The conda-forge torch build lags; the official macOS arm64 wheels include MPS and are the supported path. Install torch with pip *inside* the conda env.
- **macOS 26 (Tahoe) MPS regression (active as of early 2026).** On some macOS 26.x builds, `torch.backends.mps.is_built()` is True but `is_available()` is False -- MPS silently unavailable. Track pytorch/pytorch issues #167679 and #177819. Until resolved on a given machine, fall back to CPU and pin a known-good torch/macOS pair. Do not assume MPS works; detect at runtime.
- **MPS op fallback.** For unsupported ops set `PYTORCH_ENABLE_MPS_FALLBACK=1` so they run on CPU instead of crashing.

### Recommended versions (verify at setup, do not trust blindly)
- Python 3.12 (native arm64). 3.11 also fine. Avoid bleeding-edge until torch supports it.
- PyTorch latest stable (MPS included in the standard macOS arm64 wheel; no separate wheel).
- Device-select pattern in all training code:
  ```python
  import torch
  device = (
      "cuda" if torch.cuda.is_available()
      else "mps" if torch.backends.mps.is_available()
      else "cpu"
  )
  ```

### environment.yml (conda-forge base; torch via pip)
```yaml
name: atr
channels: [conda-forge]
dependencies:
  - python=3.12
  - pip
  - numpy
  - scipy
  - pandas
  - scikit-learn
  - matplotlib
  - jupyterlab
  - pyarrow          # parquet
  - zarr             # chunked arrays for motion tensors
  - tqdm
  - pyyaml
  - ffmpeg           # video decode for pose extraction
  - dvc              # data versioning, tied to consent terms
  - pip:
    - torch          # pip wheel = MPS on mac / CUDA-or-CPU on linux
    - torchvision
    - mediapipe      # monocular pose extraction
    - opencv-python
    - wandb          # experiment tracking (or mlflow)
    - einops
```
Linux note: same file works; pip torch resolves CUDA or CPU wheel per the index used. For CUDA, install torch from the appropriate `--index-url` rather than the default wheel.

### Taxonomy bootstrap (text, before video)

Before labeled video exists, the system is bootstrapped from the canonical reference texts. Ingesting a small set of well-established aikido books lets the project nail down the technique taxonomy and the basic factual structure -- the names, their classifications (attack / technique / direction / form), and the relationships among them -- which seeds the parser's slot vocabulary and the surface-layer ground truth. This gives the system a working skeleton of the art to reason against well before any motion data is captured.

Scope and limits:
- Extract structure and fact, not expression. The aim is the taxonomy and technique definitions -- which names exist, how they are categorized, what distinguishes one from another -- not the reproduction of any book's text. The books are copyrighted works whose authors and publishers hold rights; the project treats them with the same authority and attribution principles as the rest of its sources.
- The output is a structured taxonomy artifact (the slot vocabulary and a technique reference), versioned like any other dataset, with provenance recorded.
- This is a separate ingestion path from the video/motion ingestion sub-projects, run earlier and for a different purpose: text establishes what the categories are; video later supplies how the techniques move.

### Data analysis layer
- Pose extraction: video -> 3D pose via MediaPipe (baseline) or a MotionBERT-class lifter.
- Canonical skeleton schema = the FAIR interoperability contract. Document it once; every collection maps to it.
- Representation store: per-clip arrays (position, velocity, acceleration, 6D joint rotation, root trajectory, two-body relational channels) in Zarr/Parquet. Not a RDBMS.
- Motion primitives library: segment, normalize, point-light playback, kuzushi/coupling features. This is where the hypothesis gets tested qualitatively before training.

### Model-building pipeline
- Data versioning: DVC; every dataset version is tied to the consent terms that governed it.
- Architecture: parse-don't-classify. Multi-head over a skeleton backbone (CTR-GCN / InfoGCN class) or MotionBERT features: one head per surface slot (attack / technique / direction) plus a continuous embedding for the deep/qualitative layer.
- Tracking: Weights & Biases or MLflow (local mode honors local-first).
- Eval: slot accuracy, compositional generalization on held-out attack x technique pairings, and a teacher-agreement metric for the deep layer.

### Training compute
ATR models are skeleton/motion networks, not large language models -- small by modern standards. A single mid-tier GPU (RTX 4090 or one A100 40GB) trains a CTR-GCN or a MotionBERT finetune comfortably; H100-class hardware is unnecessary.

- Holder collections train locally only -- Linux + Nvidia CUDA or Mac + MPS on owned hardware. CPU fallback always works.
- Cloud GPUs (e.g. RunPod, Vast.ai, Lambda) are an option for non-sensitive runs only: synthetic, augmented, or public data, and architecture experiments. A protected collection never goes to a multi-tenant cloud. Skip hyperscalers.

---

## 2. Contributor + Demo Stack (FastAPI + React)

For content/contributor tools and demo sites. Web surface, local-first deployable.

### Backend -- FastAPI (Python)
- FastAPI + Uvicorn; Pydantic models for the parse schema and contribution records.
- Runs in its own conda env (or shares atr); serves the trained model behind a thin API.
- Endpoints (sketch):
- `POST /parse` -- clip in, structured parse out (slots + confidence + deep-layer embed).
- `POST /contribution` -- teacher correction; records who, what, under which terms.
- `GET  /clip/{id}/playback` -- point-light skeleton data for the viewer.
- `GET  /technique/{id}` -- lookup metadata.
- Contribution records carry identity, attribution, and machine-readable terms (CARE: authority to control + collective benefit). No write path bypasses attribution.
- Storage local-first: SQLite for records in pilot; Postgres only if a deployment needs it.

### Frontend -- React
- React + Vite + TypeScript. Tailwind for styling.
- Point-light / skeleton playback component (Canvas or lightweight WebGL) -- core shared widget across all demos.
- Talks to FastAPI over REST. No server-side rendering needed for the pilot.

### Local-first deployment
- Whole contributor+demo stack runs on a single machine (holder's or project's) via docker compose: one container FastAPI, one static-served React build, one SQLite volume.
- Model can run on the same box (CPU/MPS). No cloud dependency required to demo.
- When a holder wants their collection to stay on their hardware, the stack deploys to their box; the model comes to the data.

---

## 3. Demo Projects

1. **Technique Lookup (flagship).** Select/upload a clip -> returns the parsed technique (attack, technique, omote/ura) with confidence, and plays the point-light skeleton with the kuzushi moment highlighted. Can be stubbed early with a weak model to derisk UX and give holders something tangible to react to.
2. **Compare.** Two performances of the same technique side by side; shows where timing and connection diverge.
3. **Contribution loop.** Teacher corrects a parse live; the correction is recorded as attributed, recognized contribution and shown returning to the holder. Demonstrates the governance stance as working software, not policy text.

---

## Build order
taxonomy bootstrap (text) -> data analysis -> contributor stack -> model -> deploy, with Technique Lookup stubbed early against a weak/placeholder model to derisk the contributor UX in parallel.

---

_ATR · toolchain & stack · rev 1 · 2026-06-08 · draft_