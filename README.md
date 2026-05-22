#Dege-Kangyur Dataset: A High-Fidelity Layout-Aligned Image Dataset for Historical Tibetan Document Restorationt – Sample & Helper Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository provides a small sample and helper code for the **Dege‑Kangyur Dataset** – a high‑fidelity, layout‑aligned image dataset for **weakly‑supervised historical Tibetan document restoration**.

> **Paper**: (under review, *Scientific Data*)  
> **Full Dataset**: Zenodo [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19944931.svg)](https://doi.org/10.5281/zenodo.19944931)

---

## 🌟 Why This Dataset?

### 1. First‑of‑its‑kind for Tibetan Woodblock Prints
The Dege‑Kangyur dataset is the **first publicly available paired dataset** for Tibetan historical documents printed on **Stellera chamaejasme (wolf poison) paper** – a unique material with coarse root‑fiber texture that creates complex background noise when digitized.

### 2. Preserves Authentic Non‑Rectangular Layouts
Unlike existing document restoration datasets that forcibly rectify images to flat rectangles, our dataset **retains the original page curvature, red bounding frames, and physical edges** without any geometric warping. This is essential for **“restore as original”** (修旧如旧) digital preservation.

### 3. Designed for Weakly‑Supervised / Unsupervised Learning
Because the degraded and clean images are only **layout‑aligned** (not pixel‑wise aligned), the dataset is **ideal for weakly‑supervised and unsupervised image‑to‑image translation methods** (e.g., CycleGAN, CUT). It can also be used for supervised training with perceptual losses or other alignment‑tolerant objectives.

### 4. Addresses Tibetan Character Stacking Complexity
Tibetan script uses **vertical stacking** of base characters, vowels, super‑scripts and sub‑scripts. General‑purpose typesetting engines break these stacks. Our dataset generation pipeline includes a **dedicated semantic parser** that keeps each Tibetan syllable as an indivisible visual unit.

### 5. Provides Two Resolution Levels
- **Full‑resolution** (~5000×1000 for degraded, ~1835×350 for clean) – preserves complete page context, including marginal areas and red frames.
- **Normalized 1024×128 sub‑set** – fixed resolution, cropped to main text region, ready for deep learning models.

---

## 🔬 Research Directions Supported

This dataset can advance multiple research areas:

| Area | How the dataset helps |
|------|----------------------|
| **Document image restoration** | Paired degraded‑clean images enable training of restoration models under weak alignment. |
| **Unpaired / weakly‑supervised image translation** | Layout‑aligned pairs are ideal for evaluating GAN‑based and diffusion‑based methods without pixel‑perfect ground truth. |
| **Historical Tibetan OCR** | Clean images + line‑level text transcriptions provide training data for OCR on woodblock prints. |
| **Digital humanities / preservation** | Enables quantitative benchmarking of “restore as original” algorithms for rare scriptures. |
| **Low‑resource language document processing** | Serves as a case study for languages with complex scripts and scarce digitized resources. |

---

## 📦 Full Dataset on Zenodo

The **complete Dege‑Kangyur dataset** (500 high‑resolution image pairs + normalized sub‑set + text files) is archived on Zenodo:

👉 **[10.5281/zenodo.19944931](https://doi.org/10.5281/zenodo.19944931)**

The Zenodo record contains:
- `degraded1.zip` & `degraded2.zip` – 500 full‑resolution degraded images (~5000×1000)
- `clean1.zip` & `clean2.zip` – 500 full‑resolution clean images (~1835×350, preserving curvature & red frames)
- `degraded_1024.zip` & `clean_1024.zip` – Normalized 1024×128 sub‑set (cropped text region)
- `txt.zip` – Line‑level text transcriptions (UTF‑8, main text only; marginal notes **not** transcribed)

> **⚠️ Important**: The text files contain only the main text lines inside the red bounding frames. Marginal notes or side annotations are **not included**.

**Please use the Zenodo link for any full‑scale training or evaluation.**

---

## 🧪 Sample Data (in this repository)

For quick experimentation, we provide a **small sample** of **5 full‑resolution pairs** . All files are placed in the **repository root** (no subfolder).

- `min_degraded.zip` – 5 degraded images (~5000×1000 each)
- `min_clean.zip` – 5 corresponding clean images (~1835×350 each)
- `min_txt.zip` – 5 line‑level text files (naming: `1.txt` … `005.txt`)

These samples preserve the full layout (curvature, red frames, physical edges). The same **no‑marginal‑notes** rule applies.

---

## 🔧 Helper Code Modules

We include three Python modules that were used to generate the dataset (the full pipeline is described in our paper). These are **helper tools**, not a full end‑to‑end model.

| File | Description |
|------|-------------|
| `background.py` | Ancient book background synthesis – texture extraction, edge blending, red frame rendering |
| `boundary_grid.py` | Non‑linear boundary detection + adaptive non‑rectangular grid generation (snap‑to‑boundary) |
| `tibetan_character.py` | Tibetan semantic parsing (Unicode block aggregation) + physical typesetting (space compression, overlap correction) |

**Requirements**: Python 3.8+, OpenCV, NumPy.

---

## 🚀 Quick Start with the Sample

```bash
# Clone the repository
git clone https://github.com/cocotiti123/Dege-Ganjur-Tibetan-Ancient-Book-Helper-Code-and-Datasets.git
cd Dege-Ganjur-Tibetan-Ancient-Book-Helper-Code-and-Datasets

# Unzip the sample data (files are in root)
unzip min_degraded.zip
unzip min_clean.zip
unzip min_txt.zip

# Run background synthesis on the first sample
python background.py --input 001.png --output output/

⚠️ Intellectual Property Notice
A patent application covering the core methodologies (adaptive boundary detection, non‑rectangular snap‑to‑boundary grid, Tibetan semantic parsing, and the three‑stage physical typesetting engine) is currently under review.
The source code in this repository is released under the MIT License for research reproducibility. All rights not expressly granted are reserved.

📄 License & Citation
Code: MIT License

Dataset (full and sample): CC BY 4.0

If you use this dataset or code in your research, please cite our paper (currently under review). The preferred citation will be updated upon publication.

🙏 Acknowledgements
We thank the Adarsha (正法宝藏) platform (https://adarshah.org/kangyur/) for providing the original Degé Kangyur images, and the Language Resources Innovation Center of Northwest Minzu University for the curated Tibetan transcriptions. This work was supported in part by the National Natural Science Foundation of China (Grant No. 62466053) and the Natural Science Foundation of Gansu Province, China (Grant No. 25JRRA993).

