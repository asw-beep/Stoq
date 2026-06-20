export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="font-heading text-4xl tracking-tight">Stoq</h1>
          <p className="text-sm text-muted-foreground">
            Forecasts · Sentiment · Portfolio analytics
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
