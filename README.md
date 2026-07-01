# 🦖 JurassiPedia (Local Development Edition)

[![Watch the Demo Video](https://img.shields.io/badge/Demo%20Video-Play-red?style=for-the-badge&logo=youtube)](YOUR_DEMO_VIDEO_URL_HERE)

JurassiPedia is a production-grade, highly specialized RAG (Retrieval-Augmented Generation) encyclopedia system designed to answer complex questions about dinosaurs and paleontology with real-time performance telemetry and high-fidelity source tracking.


It integrates a **React (Vite) frontend** and a **FastAPI backend** to deliver a premium, terminal-inspired user experience.


---

## 🌟 Key Strengths & Architectural Features

* **Hybrid Dual-Path Retrieval**:
  - **Dense Vector Search**: Leverages local embeddings (`all-MiniLM-L6-v2`) via ChromaDB to query a pre-indexed, verified Jurassic dataset.
  - **Satellite Web Uplink (Fallback)**: When local database similarity scores fall below a **55% confidence threshold**, or if manually toggled in the UI, the system dynamically falls back to an asynchronous zero-dependency web scraper (DuckDuckGo) to fetch real-time scientific consensus.
* **Real-Time Token Streaming**: Uses Server-Sent Events (SSE) to stream tokens piece-by-piece to the UI for interactive, low-latency rendering.
* **LLM-as-a-Judge Telemetry Pipeline**:
  - Automatically assesses **Faithfulness** (hallucination detection) and **Answer Relevance** using asynchronous LLM evaluations.
  - Custom evaluation prompts permit scientifically sound logical deductions from base facts (e.g., biomechanics of dinosaur skeletons vs. flight limits) preventing false-negative hallucination flags.
  - Real-time display of **Retrieval Latency** and **Generation Latency**.
* **Immersive Developer UI**: Features a retro-futuristic dark mode theme, interactive side drawer previewing raw reference text chunks, matching percentages, and visual telemetry meters.
* **Zero-Config Demo Mode**: If no `GROQ_API_KEY` is provided in the environment, the backend automatically switches to a high-fidelity **Demo Mode** which simulates real-time SSE streaming, source document drawers, and latencies for predefined queries. This allows users to test the entire application interface instantly without registering for keys.

---


## 🛠️ Setup & Installation

### Prerequisites
* **Python 3.10+**
* **Node.js 18+**
* **Groq API Key** (Optional: only needed for live LLM RAG mode. If omitted, the app runs in **Demo Mode** out-of-the-box.)

---


### 1. Backend Setup

1. **Navigate to the root directory and create a Python Virtual Environment**:
   ```bash
   python -m venv venv
   ```
2. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     source venv/bin/activate
     ```
3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your API key:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and configure your API key:
   ```env
   GROQ_API_KEY=your_actual_groq_api_key_here
   ```
5. **Run the Backend Server**:
   ```bash
   python -m uvicorn app.main:app --port 8000
   ```
   The backend will start and run on `http://127.0.0.1:8000`.

---

### 2. Frontend Setup

1. **Navigate to the frontend folder**:
   ```bash
   cd frontend
   ```
2. **Install node dependencies**:
   ```bash
   npm install
   ```
3. **Start the Development Server**:
   ```bash
   npm run dev
   ```
   The application will run locally, usually on `http://localhost:5173`. Open this URL in your web browser.

---

## 🔍 Test Questions to Try

To see the system's core capabilities in action, try the following prompts:

1. **Testing Vector Retrieval & Fact Grounding**:
   > *"Did Dilophosaurus actually spit venom scientifically?"*
   - **What to observe**: The backend will find vector chunks regarding *Dilophosaurus*, synthesize an answer correcting the Jurassic Park movie myth, display matching percentages, and achieve high faithfulness.
2. **Testing Scientific Deduction & Grader Calibration**:
   > *"Theoretical considerations of a winged Tyrannosaurus Rex"*
   - **What to observe**: The model will deduce from context facts (e.g., T-Rex skeleton weight, Pteranodon biomechanics) that flight would be physically impossible. The custom Faithfulness evaluator will correctly score this deduction with high marks (e.g., `90%+`) rather than flagging it as a hallucination.
3. **Testing Web Search Fallback (Satellite Uplink)**:
   > *"Tell me about the latest space discovery in 2026"* (or toggle "Satellite Uplink" manually).
   - **What to observe**: Since this information is not in the Jurassic database, the RAG confidence score drops below 55%, triggering a web query. The UI will render source cards labeled with `Web Uplink` and show the corresponding domain sources.

---

## 🖥️ How to Use the UI

1. **Chat Panel**: Type your questions in the input field. A green terminal cursor (`▋`) will blink actively while tokens are streaming.
2. **Satellite Uplink Toggle**: Explicitly force the system to perform a live web search instead of checking the database.
3. **Telemetry Card**: Located right below each system response:
   - **Retrieval Latency**: Time spent looking up vectors or searching the web.
   - **Generation Latency**: Time taken to stream the response.
   - **Faithfulness / Relevance**: Real-time evaluator grading.
4. **Interactive Source Cards**: Click on any citation card at the bottom of the response to slide open the **Source Deck Drawer** showing exact reference text passages.
