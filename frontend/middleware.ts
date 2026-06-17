import { type NextRequest, NextResponse } from "next/server";

/** Routes that do NOT require a valid session. */
const PUBLIC_PATHS = ["/", "/login", "/register"];

/**
 * Protect every non-public route by checking for the presence of the
 * `access_token` httpOnly cookie set by the backend on login.
 *
 * We only check cookie presence here (edge runtime has no secret to verify the
 * JWT signature). Full identity validation happens on every API call via the
 * backend's `get_current_user` dependency.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );

  const hasToken = request.cookies.has("access_token");

  // Unauthenticated user trying to reach a protected page → /login
  if (!isPublic && !hasToken) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Authenticated user hitting login/register → /tickets
  if ((pathname === "/login" || pathname === "/register") && hasToken) {
    const ticketsUrl = request.nextUrl.clone();
    ticketsUrl.pathname = "/tickets";
    ticketsUrl.search = "";
    return NextResponse.redirect(ticketsUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all paths except Next.js internals and static files.
     * /_next/static, /_next/image, /favicon.ico are excluded.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
