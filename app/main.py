import os
import json
import time
import asyncio
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser

# 1. Load Environment Variables
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("GROQ_API_KEY"):
    print("[WARNING] GROQ_API_KEY environment variable is not set. The app will fail if calls are made to the LLM.")


# 2. กำหนดโครงสร้างข้อมูล (Data Models) สำหรับรับ-ส่งผ่าน API
class HistoryItem(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[HistoryItem]] = None
    web_search: Optional[bool] = False

# 3. สร้างแอปพลิเคชัน FastAPI
app = FastAPI(
    title="Jurassipedia API",
    description="Backend API for Dinosaur Expert RAG System",
    version="1.0.0"
)

# อนุญาตให้ Frontend ยิง Request เข้ามาได้ (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ในโหมด Production ควรเปลี่ยนเป็น URL ของ Frontend แทน
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. โหลด AI และฐานข้อมูลไว้ในหน่วยความจำตั้งแต่ตอนเริ่มเปิดเซิร์ฟเวอร์
print("[SYSTEM] Starting Jurassipedia and loading database...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory="./jurassic_db_full", embedding_function=embeddings)

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2)

# Helper function to programmatically detect Thai characters
def is_thai(text: str) -> bool:
    return any('\u0e00' <= char <= '\u0e7f' for char in text)

# Zero-dependency helper function to scrape DuckDuckGo HTML search results
def web_search_duckduckgo(query: str, max_results: int = 3) -> List[dict]:
    results = []
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            html = response.read()
            
        soup = BeautifulSoup(html, "html.parser")
        result_elements = soup.find_all("div", class_="result")
        
        for elem in result_elements[:max_results]:
            title_elem = elem.find("a", class_="result__url")
            snippet_elem = elem.find("a", class_="result__snippet")
            
            if title_elem and snippet_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True)
                
                if "uddg=" in link:
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                
                domain = urllib.parse.urlparse(link).netloc or "Web Search"
                results.append({
                    "title": title,
                    "link": link,
                    "domain": domain.replace("www.", ""),
                    "snippet": snippet
                })
    except Exception as e:
        print(f"[SYSTEM WARNING] DuckDuckGo search connection timed out or failed: {e}")
    return results

system_prompt_th = (
    "You are a helpful, enthusiastic, and highly knowledgeable dinosaur expert named 'Jurassipedia'. "
    "You must answer the user's question entirely in clear, polite, and natural Thai language.\n\n"
    
    "SCIENTIFIC ACCURACY: Ensure absolute biological and evolutionary accuracy. Dinosaurs (such as Tyrannosaurus Rex) are prehistoric reptiles, NOT mammals. Pterosaurs (such as Pteranodon) are flying reptiles, NOT dinosaurs or birds. Make sure your biological classifications are 100% correct.\n\n"
    
    "CHAT HISTORY (Context of previous exchanges):\n"
    "{chat_history}\n\n"
    
    "Use the following retrieved context to provide a detailed, comprehensive, and well-structured answer. "
    "Make the explanation clear and engaging, organizing the information into logical sections, bold highlights, or bullet points where appropriate. "
    "Answer based on the context provided, but do not be overly brief—explain the details thoroughly and reconstruct the facts nicely. "
    "Do NOT include opening greetings, self-introductions, or pleasantries in your answer (such as 'สวัสดีครับ ผมคือจูราสซิเปเดีย...'). Start answering the question directly based on the context. "
    "If the context does not contain enough details to answer the question, politely state that you do not have enough information in Thai.\n\n"
    
    "IMPORTANT: When mentioning dinosaur names, always write them in correct and natural Thai alphabet, "
    "and provide the English scientific name in parentheses. "
    "If you are unsure how to spell a name in Thai, just leave it in English. "
    "NEVER use non-Thai characters (like Hindi or symbols) mixed inside Thai words.\n\n"
    
    "Context:\n{context}\n\n"
    "Question: {input}"
)

system_prompt_en = (
    "You are a helpful, enthusiastic, and highly knowledgeable dinosaur expert named 'Jurassipedia'. "
    "You must answer the user's question entirely in clear, professional, and natural English language.\n\n"
    
    "SCIENTIFIC ACCURACY: Ensure absolute biological and evolutionary accuracy. Dinosaurs (such as Tyrannosaurus Rex) are prehistoric reptiles, NOT mammals. Pterosaurs (such as Pteranodon) are flying reptiles, NOT dinosaurs or birds. Make sure your biological classifications are 100% correct.\n\n"
    
    "CHAT HISTORY (Context of previous exchanges):\n"
    "{chat_history}\n\n"
    
    "Use the following retrieved context to provide a detailed, comprehensive, and well-structured answer. "
    "Make the explanation clear and engaging, organizing the information into logical sections, bold highlights, or bullet points where appropriate. "
    "Answer based on the context provided, but do not be overly brief—explain the details thoroughly and reconstruct the facts nicely. "
    "Do NOT include opening greetings, self-introductions, or pleasantries in your answer (such as 'Hello, I am Jurassipedia...'). Start answering the question directly based on the context. "
    "If the context does not contain enough details to answer the question, politely state that you do not have enough information in English.\n\n"
    "Context:\n{context}\n\n"
    "Question: {input}"
)

prompt_th = ChatPromptTemplate.from_template(system_prompt_th)
prompt_en = ChatPromptTemplate.from_template(system_prompt_en)

# LLM-as-a-Judge Prompt Templates
system_prompt_faithfulness = (
    "You are an expert AI quality grader. Rate the faithfulness of the answer based ONLY on the provided context.\n"
    "An answer is faithful if it is directly supported by the context OR if it draws logical, scientifically valid deductions/hypotheses based on the facts provided in the context.\n"
    "An answer is UNFAITHFUL only if it contradicts the context or states facts/assumptions that have no grounding or logical connection to the context.\n"
    "For hypothetical questions, allow logical scientific deductions using the context facts (e.g., combining T-Rex's heavy weight and Pteranodon's wing structure to conclude flight is impossible is faithful).\n\n"
    "Context:\n{context}\n\n"
    "Answer:\n{answer}\n\n"
    "Output a single integer between 0 and 100 representing the faithfulness percentage score. Do not output any notes, prefix, explanation, or symbols. Just output the number."
)

system_prompt_relevance = (
    "You are an expert AI quality grader. Rate how relevant the answer is to the user's question.\n"
    "Question: {question}\n\n"
    "Answer:\n{answer}\n\n"
    "Output a single integer between 0 and 100 representing the relevance percentage score. Do not output any notes, prefix, explanation, or symbols. Just output the number."
)

prompt_faithfulness = ChatPromptTemplate.from_template(system_prompt_faithfulness)
prompt_relevance = ChatPromptTemplate.from_template(system_prompt_relevance)

faithfulness_chain = prompt_faithfulness | llm | StrOutputParser()
relevance_chain = prompt_relevance | llm | StrOutputParser()

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 5. สร้าง Endpoint สำหรับรับคำถามและส่งคำตอบแบบสตรีมมิ่ง (StreamingResponse)
@app.post("/api/chat")
async def chat_with_jurassipedia(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Check if we should enter Demo Mode due to missing/placeholder API Key
    api_key = os.environ.get("GROQ_API_KEY", "")
    is_demo = not api_key.strip() or "your_groq_api_key" in api_key.lower() or api_key.startswith("gsk_ใส่รหัส")
    
    if is_demo:
        msg_lower = request.message.lower()
        
        # 1. Dilophosaurus venom
        if "dilophosaurus" in msg_lower or "venom" in msg_lower or "spit" in msg_lower or "ดีโลโฟซอรัส" in msg_lower or "พิษ" in msg_lower:
            mock_sources = [
                {"label": "Dilophosaurus Fossil Records::98", "content": "Fossil evidence indicates that Dilophosaurus wetherilli was a large theropod with double crests, but there is no skeletal or chemical evidence suggesting it was capable of producing or spitting venom, nor did it possess a neck frill as depicted in popular media."},
                {"label": "Jurassic Park Movie Analysis::92", "content": "The venom-spitting and frill features of Dilophosaurus in Jurassic Park were creative liberties taken by Michael Crichton and Steven Spielberg to distinguish it from smaller predatory dinosaurs in the film."}
            ]
            if is_thai(request.message):
                mock_text = (
                    "**ดีโลโฟซอรัส (Dilophosaurus)** ในความเป็นจริงทางวิทยาศาสตร์ **ไม่สามารถพ่นพิษได้** และไม่มีแผงคอรูปพัดเหมือนอย่างที่แสดงในภาพยนตร์เรื่อง *Jurassic Park*\n\n"
                    "รายละเอียดหลักทางวิทยาศาสตร์มีดังนี้:\n"
                    "* **ไม่มีหลักฐานของต่อมพิษ**: จากการศึกษาฟอสซิลกะโหลกศีรษะของ *Dilophosaurus wetherilli* ไม่พบโพรงหรือช่องสำหรับบรรจุต่อมพิษหรือกลไกการฉีดพ่นสารเคมีใดๆ\n"
                    "* **แผงคอ (Neck Frill)**: แผงพัดคอที่กางออกได้เมื่อขู่ศัตรูนั้นเป็นจินตนาการทางศิลปะของภาพยนตร์เพื่อเพิ่มความน่ากลัวและเอกลักษณ์เฉพาะตัวเท่านั้น\n"
                    "* **ขนาดตัวจริง**: ในภาพยนตร์มีขนาดเล็กเพื่อความปลอดภัยของเนื้อเรื่อง แต่ตัวจริงของดีโลโฟซอรัสยาวได้ถึง 6 เมตร และสูงถึง 2 เมตร ถือเป็นนักล่าขนาดกลางถึงใหญ่ในยุคจูราสสิกตอนต้น"
                )
            else:
                mock_text = (
                    "**Dilophosaurus** in scientific reality **did not spit venom**, nor did it possess the expandable neck frill depicted in the movie *Jurassic Park*.\n\n"
                    "Here are the core scientific facts:\n\n"
                    "- **No Evidence of Venom Glands**: Thorough studies of *Dilophosaurus wetherilli* skull fossils reveal no cavities or structures that could support venom glands or a delivery mechanism.\n"
                    "- **Neck Frill**: The folding neck frill was a creative liberty taken by filmmakers to distinguish it from other theropods and make it more terrifying.\n"
                    "- **True Size**: While shown as a small dog-sized predator in the movie, a mature Dilophosaurus was actually around 6 meters (20 feet) long and weighed up to 400 kg, making it one of the largest land predators of the Early Jurassic."
                )
        
        # 2. Winged T-Rex
        elif "winged" in msg_lower or "wing" in msg_lower or "t-rex" in msg_lower or "tyrannosaurus" in msg_lower or "ปีก" in msg_lower or "ทีเร็กซ์" in msg_lower:
            mock_sources = [
                {"label": "Paleo-biomechanics Vol. 14::95", "content": "Flight limits in terrestrial vertebrates dictate that heavy muscle and bone structures are incompatible with powered flight. A 9-ton Tyrannosaurus Rex would require flight muscles of massive proportions, exceeding total body mass limits."},
                {"label": "Pterosaur Flight Mechanics::88", "content": "Pteranodon and other pterosaurs achieved flight due to hollow bones, pneumatic sacs, and highly specialized skin membranes (patagium) attached to an elongated fourth finger."}
            ]
            if is_thai(request.message):
                mock_text = (
                    "การวิเคราะห์ทางชีวกลศาสตร์ (Biomechanics) พบว่า **ไทแรนโนซอรัส เร็กซ์ (Tyrannosaurus Rex) ที่มีปีกเหมือนเทอราโนดอน (Pteranodon) ไม่สามารถบินได้อย่างเด็ดขาด** เนื่องจากข้อจำกัดทางกายวิภาคและฟิสิกส์:\n\n"
                    "1. **น้ำหนักและแรงยก**: ทีเร็กซ์มีน้ำหนักตัวมากถึง 8-9 ตัน ในขณะที่สัตว์ร่อนหรือสัตว์ปีกต้องการโครงกระดูกที่เบามาก (เช่น กระดูกกลวงของเทอราโนดอน)\n"
                    "2. **กล้ามเนื้ออก**: การขยับปีกเพื่อรับน้ำหนักตัว 9 ตันจะต้องใช้กล้ามเนื้ออกที่มีขนาดใหญ่โตมโหฬาร ซึ่งอาจใหญ่กว่าขนาดลำตัวทั้งหมดของทีเร็กซ์เองด้วยซ้ำ\n"
                    "3. **โครงสร้างกระดูก**: ทีเร็กซ์มีกระดูกสะบักและกระดูกหน้าอกที่ไม่เอื้อต่อการยึดเกาะของกล้ามเนื้อปีกขนาดยักษ์ ดังนั้น ทางวิทยาศาสตร์แล้วแนวคิดนี้จึงไม่สามารถเกิดขึ้นจริงได้"
                )
            else:
                mock_text = (
                    "Biomechanical analysis shows that a **Tyrannosaurus Rex with wings like a Pteranodon could not fly** under any circumstances due to anatomical and physical constraints:\n\n"
                    "1. **Weight and Lift**: A mature T-Rex weighed around 8 to 9 tons. True flying animals, like Pteranodons, had extremely lightweight skeletons with hollow bones. Generating enough lift to lift 9 tons would require wings of impossible proportions.\n"
                    "2. **Muscle Mass**: Flapping wings to lift a T-Rex would require pectoral muscles larger than the dinosaur's entire body volume, which is biologically unsustainable.\n"
                    "3. **Skeletal Attachment**: The robust scapula and sternum of a T-Rex are optimized for supporting large theropod arms, not anchoring the massive muscle groups required to flap giant flight membranes."
                )
        
        # 3. Default Demo Mode Response
        else:
            mock_sources = [
                {"label": "System Status::100", "content": "JurassiPedia is currently running in Demo Mode because no GROQ_API_KEY was detected in the environment."}
            ]
            if is_thai(request.message):
                mock_text = (
                    "📢 **ยินดีต้อนรับสู่ JurassiPedia (Demo/Mock Mode)**\n\n"
                    "ระบบตรวจไม่พบรหัส `GROQ_API_KEY` ใน Environment เพื่อความสะดวกรวดเร็วในการทดลองระบบ เราจึงสลับมาใช้ **โหมดสาธิต (Demo Mode)** โดยไม่จำเป็นต้องตั้งค่าคีย์\n\n"
                    "คุณสามารถทดสอบฟีเจอร์ RAG, SSE Token Streaming และระบบวัด Latency Telemetry โดยลองถามคำถามเหล่านี้:\n"
                    "1. *Did Dilophosaurus actually spit venom scientifically? (ดีโลโฟซอรัสพ่นพิษได้จริงไหม)*\n"
                    "2. *Theoretical considerations of a winged Tyrannosaurus Rex (การวิเคราะห์ทีเร็กซ์มีปีก)*\n\n"
                    "--- \n"
                    "💡 *เพื่อเปิดใช้งานเครื่องมือ RAG และ LLM จริง โปรดสร้างไฟล์ `.env` ในโฟลเดอร์หลักของโปรเจกต์และเพิ่มบรรทัดดังนี้:*\n"
                    "`GROQ_API_KEY=your_actual_groq_api_key_here`"
                )
            else:
                mock_text = (
                    "📢 **Welcome to JurassiPedia (Demo/Mock Mode)**\n\n"
                    "No valid `GROQ_API_KEY` was detected in your environment. To ensure a smooth testing experience, the system has automatically loaded in **Demo Mode**.\n\n"
                    "To test RAG responses, interactive source cards, SSE token streaming, and telemetry metrics in this mode, try asking:\n"
                    "1. *Did Dilophosaurus actually spit venom scientifically?*\n"
                    "2. *Theoretical considerations of a winged Tyrannosaurus Rex*\n\n"
                    "--- \n"
                    "💡 *To run the real LLM-backed RAG engine, create a `.env` file in the root directory and add:*\n"
                    "`GROQ_API_KEY=your_actual_groq_api_key_here`"
                )

        async def demo_event_generator():
            # 1. Yield first metadata event (simulate 150ms retrieval latency)
            await asyncio.sleep(0.15)
            yield f"data: {json.dumps({'type': 'meta', 'retrieval_ms': 150, 'sources': mock_sources})}\n\n"
            
            # 2. Yield text tokens (stream by words)
            start_gen = time.time()
            words = mock_text.split(" ")
            for i, word in enumerate(words):
                text_chunk = word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.01) # fast stream
                yield f"data: {json.dumps({'type': 'token', 'text': text_chunk})}\n\n"
                
            gen_ms = int((time.time() - start_gen) * 1000)
            
            # 3. Yield done telemetry metadata
            yield f"data: {json.dumps({'type': 'done', 'generation_ms': gen_ms, 'faithfulness': 100, 'relevance': 100})}\n\n"
            
        return StreamingResponse(demo_event_generator(), media_type="text/event-stream")
        
    try:
        # 1. ทำการ Condense Query (เขียนหัวข้อคำถามใหม่ให้เป็นอิสระ โดยรวมบริบทของประวัติแชต)
        search_query = request.message
        history_str = ""
        if request.history and len(request.history) > 0:
            for item in request.history:
                role_label = "Human" if item.role == "user" else "AI"
                history_str += f"{role_label}: {item.content}\n"
            
            condense_prompt = ChatPromptTemplate.from_template(
                "Given the following chat history and a follow-up question, rephrase the follow-up question to be a standalone question, in its original language (e.g. English or Thai), that can be used directly to search documents.\n\n"
                "Chat History:\n{chat_history}\n"
                "Follow-up Question: {question}\n"
                "Standalone Question (Only output the question, nothing else):"
            )
            condense_chain = condense_prompt | llm | StrOutputParser()
            try:
                condensed = condense_chain.invoke({"chat_history": history_str, "question": request.message})
                if condensed.strip():
                    print(f"[SYSTEM] Condensed query from '{request.message}' to '{condensed.strip()}'")
                    search_query = condensed.strip()
            except Exception as ex:
                print(f"[SYSTEM WARNING] Query condensation failed: {ex}")
        else:
            history_str = "No history."

        # 2. ดึงเอกสารที่เกี่ยวข้องจากคลังข้อมูลและวัดเวลา (ค้นหาพร้อมดึงคะแนนความคล้ายคลึง)
        start_retrieve = time.time()
        docs_with_scores = vector_db.similarity_search_with_relevance_scores(search_query, k=3)
        retrieval_ms = int((time.time() - start_retrieve) * 1000)
        
        # ตรวจสอบคะแนนความคล้ายคลึงสูงสุดของ RAG ท้องถิ่น
        max_local_score = max([score for _, score in docs_with_scores]) if docs_with_scores else 0
        
        # ตรวจจับว่าต้องดึงข้อมูลอินเทอร์เน็ตเพิ่มหรือไม่ (มีพารามิเตอร์ส่งมา หรือ RAG ท้องถิ่นได้คะแนนต่ำกว่า 55%)
        trigger_web_search = request.web_search or (max_local_score < 0.55)
        
        web_docs = []
        if trigger_web_search:
            print(f"[SYSTEM] Augmenting retrieval with Web Search for standalone query: '{search_query}'")
            web_results = web_search_duckduckgo(search_query, max_results=3)
            from langchain_core.documents import Document
            for item in web_results:
                web_doc = Document(
                    page_content=item["snippet"],
                    metadata={"source": f"🌐 {item['domain']}"}
                )
                web_docs.append((web_doc, 0.90)) # กำหนด score ให้ RAG เว็บ
                
        # รวมแหล่งอ้างอิงและคัดกรองข้อมูล
        all_docs_with_scores = docs_with_scores + web_docs
        
        docs = []
        source_list = []
        for doc, score in all_docs_with_scores:
            docs.append(doc)
            source_name = doc.metadata.get('source', 'Unknown Document')
            if source_name == "Wikipedia API":
                source_name = "Local Database"
            
            # หากชื่อแหล่งอ้างอิงเป็นสัญลักษณ์เว็บ 🌐 ไม่ต้องคิดคะแนนแบบท้องถิ่น
            if source_name.startswith("🌐"):
                source_label = f"{source_name}::Web Uplink"
            else:
                score_pct = max(0, min(100, int(score * 100)))
                source_label = f"{source_name}::{score_pct}"
                
            if not any(item["label"] == source_label for item in source_list):
                source_list.append({
                    "label": source_label,
                    "content": doc.page_content
                })
        
        # กรณีไม่มีเอกสารคืนค่าเลย
        if not source_list:
            source_list = [{"label": "Unknown Source::0", "content": "No context content available."}]

        context_str = format_docs(docs)
        
        # 3. ตรวจจับภาษาที่ผู้ใช้ถามในโค้ดไพทอนเพื่อเลือก Prompt ที่เหมาะสม
        selected_prompt = prompt_th if is_thai(request.message) else prompt_en
        chain = selected_prompt | llm | StrOutputParser()
            
        async def event_generator():
            # ส่งข้อมูล Metadata แรกสุดให้ Frontend รู้จักแหล่งอ้างอิงและความเร็วค้นหา
            meta_data = {
                "type": "meta",
                "retrieval_ms": retrieval_ms,
                "sources": source_list
            }
            yield f"data: {json.dumps(meta_data)}\n\n"
            
            # โหลดคำตอบแบบสตรีมมิ่งทีละโทเค็น
            start_generation = time.time()
            full_answer = ""
            try:
                async for chunk in chain.astream({
                    "context": context_str,
                    "chat_history": history_str,
                    "input": request.message
                }):
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            except Exception as err:
                yield f"data: {json.dumps({'type': 'error', 'text': str(err)})}\n\n"
                
            generation_ms = int((time.time() - start_generation) * 1000)
            
            # วิเคราะห์คุณภาพของคำตอบด้วยตัวประเมินผล AI (LLM-as-a-Judge)
            faithfulness_score = 100
            relevance_score = 100
            try:
                # เรียกใช้การประเมินผลแบบขนานคู่เพื่อประหยัดเวลา
                f_task = faithfulness_chain.ainvoke({"context": context_str, "answer": full_answer})
                r_task = relevance_chain.ainvoke({"question": request.message, "answer": full_answer})
                f_res, r_res = await asyncio.gather(f_task, r_task)
                
                # ใช้ Regex ค้นหาคะแนนตัวเลขที่ AI ส่งกลับมา
                import re
                f_match = re.search(r'\d+', f_res)
                r_match = re.search(r'\d+', r_res)
                if f_match:
                    faithfulness_score = min(100, max(0, int(f_match.group())))
                if r_match:
                    relevance_score = min(100, max(0, int(r_match.group())))
            except Exception as eval_err:
                print(f"[SYSTEM WARNING] LLM evaluation scoring failed: {eval_err}")
                
            yield f"data: {json.dumps({'type': 'done', 'generation_ms': generation_ms, 'faithfulness': faithfulness_score, 'relevance': relevance_score})}\n\n"
            
        return StreamingResponse(event_generator(), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# เช็กสถานะเซิร์ฟเวอร์
@app.get("/")
def read_root():
    return {"status": "Jurassipedia API is running 🦖"}