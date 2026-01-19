import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

// Force dynamic rendering to avoid build-time auth() calls
export const dynamic = 'force-dynamic';

export default async function Home() {
  const { userId } = await auth();

  if (userId) {
    // Authenticated users go to upload page first
    redirect("/upload");
  }

  // Not authenticated - redirect to sign-in
  redirect("/sign-in");
}
