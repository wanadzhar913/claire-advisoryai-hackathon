This is a [Next.js](https://nextjs.org) project for Claire - a financial AI agent assistant.

## Prerequisites

You need a Clerk account and API keys:
1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Create a new application
3. Copy your publishable key and secret key

## Environment Variables

Create a `.env.local` file in this directory with:

```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Getting Started

### Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

### Docker Build

**Option 1: Using docker-compose (recommended)**

From the project root:
```bash
# Make sure you have a .env file with required variables
docker compose build web
```

**Option 2: Direct docker build**

```bash
docker build \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_..." \
  --build-arg NEXT_PUBLIC_API_BASE_URL="http://localhost:8000" \
  -t claire-web \
  .
```

**Important**: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is required at build time for Next.js to inline it into the client bundle.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
