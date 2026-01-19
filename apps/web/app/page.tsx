import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

export default async function Home() {
  const { userId } = await auth();

  if (userId) {
    // Authenticated users go to upload page first
    redirect("/upload");
  }

  // Not authenticated - redirect to sign-in
  redirect("/sign-in");
}
