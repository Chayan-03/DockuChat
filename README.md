# 📚 DockuChat  

DockuChat is a **multi-modal RAG (Retrieval-Augmented Generation) chat application** that lets users interact with their documents in a conversational way. The system is built with a **React (Vite) frontend** and a **Python FastAPI backend**, containerized with **Docker** for smooth deployment.  

## ✨ Features  

- 🔑 **API Key Management** – Securely store and manage API keys via a modal.  
- 📂 **Document Upload** – Upload and parse documents for chat context.  
- 💬 **Chat Interface** – Clean chat UI with support for **Markdown rendering** and **custom avatars**.  
- ⚡ **RAG Workflow** – Retrieve information from documents before answering queries.  
- 🎨 **Polished UI** – TailwindCSS-powered responsive design with dark theme.  
- 🐳 **Dockerized Deployment** – Simple `docker compose up` to run the entire app.  

---

## 🛠️ Tech Stack  

**Frontend (React + Vite)**  
- ⚛️ React 18  
- 🎨 TailwindCSS  
- 📦 Axios (API requests)  
- 📝 React-Markdown + Remark-GFM  

**Backend (Python FastAPI)**  
- 🚀 FastAPI (REST API)  
- 🧠 RAG pipeline (LLM integration, embeddings, retrieval)  
- 📄 Document parsing utilities  

**Deployment**  
- 🐳 Docker + Docker Compose  
- 🔄 Multi-service orchestration (Frontend + Backend)  

---

## 📂 Project Structure  

```
DockuChat/
│── Backend/
│   ├── .env                # Environment variables
│   ├── .gitignore          # Git ignore rules for backend
│   ├── Dockerfile          # Dockerfile for backend
│   ├── api.py              # FastAPI entrypoint
│   ├── rag_pipeline.py     # RAG pipeline implementation
│   ├── requirements.txt    # Python dependencies
│
│── Frontend/
│   ├── node_modules/       # Frontend dependencies (ignored in git)
│   ├── public/             # Static files
│   ├── src/                # React source code
│   ├── package.json        # NPM package config
│   ├── vite.config.js      # Vite configuration
│
│── docker-compose.yaml     # Compose file for multi-service setup
│── README.md               # Documentation
```

---

## ⚙️ Installation  

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/Chayan-03/DockuChat.git
cd DockuChat
```



### 2️⃣ Run with Docker Compose  
```bash
docker compose up --build
```

- Backend runs on: **http://localhost:8000**  
- Frontend runs on: **http://localhost:5173**  

---

## 🚀 Development (Without Docker)  

Run backend:  
```bash
cd Backend
pip install -r requirements.txt
uvicorn app.main:app --reload 
```

Run frontend:  
```bash
cd Frontend
npm install
npm run dev
```

---



---

## 📦 Deployment  

Since both frontend and backend are containerized, you can deploy on:  
- **Render**  
- **Railway**  
- **AWS ECS / EC2**  
- **Azure App Service**  
- **Google Cloud Run**  

---

## 🤝 Contributing  

Pull requests are welcome! For major changes, please open an issue first to discuss what you’d like to change.  

---

## 📜 License  

[Chayan-03](https://github.com/Chayan-03)  

