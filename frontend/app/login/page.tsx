export default function LoginPage() {
  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Login to DeskLite</h1>
        <p className="mt-2 text-sm text-muted">
          Access your internal support tickets.
        </p>

        <form className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium">Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              className="mt-1 w-full rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-brand"
            />
          </div>

          <div>
            <label className="text-sm font-medium">Password</label>
            <input
              type="password"
              placeholder="Enter your password"
              className="mt-1 w-full rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-brand"
            />
          </div>

          <button
            type="button"
            className="w-full rounded-md bg-brand px-4 py-2 font-medium text-white hover:opacity-90"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}