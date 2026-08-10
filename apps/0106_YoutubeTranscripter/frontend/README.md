# Frontend

YouTube Transcription Service - Frontend Application

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.local.example .env.local
```

Edit `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles
├── components/
│   ├── UrlInputForm.tsx       # YouTube URL input form
│   ├── JobStatus.tsx          # Job progress tracking
│   └── TranscriptResult.tsx   # Result display and export
└── lib/
    └── api.ts           # API client
```

## Features

- YouTube URL入力とバリデーション
- リアルタイム進行状況表示
- 文字起こし結果の表示
- LLM校正機能
- 前後比較表示
- エクスポート（TXT/SRT/VTT）
- レスポンシブデザイン

## API Endpoints Used

- `POST /api/jobs/transcribe` - Create job
- `GET /api/jobs/{id}/status` - Get status
- `GET /api/jobs/{id}/result` - Get result
- `POST /api/jobs/{id}/correct` - Request correction
- `GET /api/jobs/{id}/export` - Export transcript
