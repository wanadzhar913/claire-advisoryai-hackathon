import { ThemeToggle } from "@/components/ThemeToggle"

export default function SignInLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <header className="flex justify-end p-4">
        <ThemeToggle />
      </header>
      {children}
    </div>
  );
}
