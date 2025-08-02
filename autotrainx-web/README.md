# AutoTrainX Web Interface

Modern web interface for the AutoTrainX ML training pipeline.

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- AutoTrainX API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 🏗️ Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── dashboard/         # Dashboard pages
│   ├── layout.tsx         # Root layout
│   └── page.tsx          # Home page
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   └── layout/           # Layout components
├── lib/                   # Utilities and hooks
│   ├── api/              # API client
│   ├── hooks/            # Custom React hooks
│   └── utils.ts          # Utility functions
└── types/                 # TypeScript type definitions
```

## 🔧 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand + TanStack Query
- **API Communication**: Axios + Socket.io
- **UI Components**: Radix UI + Lucide Icons

## 📡 API Integration

The web interface connects to the AutoTrainX API backend. Make sure the API is running before starting the web interface.

Default API URL: `http://localhost:8000`

To change the API URL, update the `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://your-api-url:8000
```

## 🎯 Features

- ✅ Real-time job monitoring with WebSocket updates
- ✅ Dataset management and preparation
- ✅ Training configuration with presets
- ✅ Job history and logs
- ✅ Responsive design
- 🚧 User authentication (coming soon)
- 🚧 Model gallery (coming soon)

## 🧑‍💻 Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Run linting
npm run lint
```

## 📝 Available Pages

- `/` - Landing page
- `/dashboard` - Main dashboard with job statistics
- `/dashboard/jobs` - Job management (coming soon)
- `/dashboard/datasets` - Dataset management (coming soon)
- `/dashboard/models` - Trained models (coming soon)
- `/dashboard/settings` - Settings (coming soon)